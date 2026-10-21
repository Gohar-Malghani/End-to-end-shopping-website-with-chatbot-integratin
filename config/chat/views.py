import json
import re
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_POST

from chat.chatbot import get_customer_response
from chat.forms import CheckoutForm
from chat.models import Order, OrderItem, Product


CART_SESSION_KEY = "shopping_cart"
GUEST_ORDER_SESSION_KEY = "guest_order_references"


class InsufficientStock(Exception):
    pass


def _cart_count(request):
    cart = request.session.get(CART_SESSION_KEY, {})
    return sum(
        quantity
        for quantity in cart.values()
        if isinstance(quantity, int) and quantity > 0
    )


def _cart_rows(request):
    cart = request.session.get(CART_SESSION_KEY, {})
    product_ids = []
    for product_id in cart:
        try:
            product_ids.append(int(product_id))
        except (TypeError, ValueError):
            continue

    products = Product.objects.filter(
        pk__in=product_ids,
        active=True,
    ).order_by("name")
    rows = []
    for product in products:
        try:
            quantity = int(cart.get(str(product.pk), 0))
        except (TypeError, ValueError):
            quantity = 0
        if quantity < 1:
            continue
        rows.append(
            {
                "product": product,
                "quantity": quantity,
                "line_total": product.price * quantity,
            }
        )
    return rows


def shop_home(request):
    products = Product.objects.filter(active=True)
    category = request.GET.get("category", "")
    query = request.GET.get("q", "").strip()

    if category in Product.Category.values:
        products = products.filter(category=category)
    else:
        category = ""
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    return render(
        request,
        "shop/home.html",
        {
            "products": products,
            "categories": Product.Category.choices,
            "selected_category": category,
            "query": query,
            "cart_count": _cart_count(request),
        },
    )


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, active=True)
    return render(
        request,
        "shop/product_detail.html",
        {"product": product, "cart_count": _cart_count(request)},
    )


def cart_view(request):
    rows = _cart_rows(request)
    return render(
        request,
        "shop/cart.html",
        {
            "rows": rows,
            "subtotal": sum(
                (row["line_total"] for row in rows),
                start=Decimal("0.00"),
            ),
            "cart_count": _cart_count(request),
        },
    )


@require_POST
def cart_add(request, slug):
    product = get_object_or_404(Product, slug=slug, active=True)
    cart = request.session.get(CART_SESSION_KEY, {})
    try:
        current_quantity = int(cart.get(str(product.pk), 0))
    except (TypeError, ValueError):
        current_quantity = 0

    if product.stock < 1:
        messages.error(request, "This item is currently out of stock.")
    elif current_quantity >= product.stock:
        messages.error(request, "You have added all available stock to your cart.")
    else:
        cart[str(product.pk)] = current_quantity + 1
        request.session[CART_SESSION_KEY] = cart
        messages.success(request, f"{product.name} added to your cart.")

    return redirect("product_detail", slug=product.slug)


@require_POST
def cart_update(request):
    cart = request.session.get(CART_SESSION_KEY, {})
    product_id = request.POST.get("product_id", "")
    try:
        numeric_product_id = int(product_id)
    except (TypeError, ValueError):
        messages.error(request, "The selected cart item could not be found.")
        return redirect("cart_view")

    try:
        quantity = int(request.POST.get("quantity", "0"))
    except (TypeError, ValueError):
        messages.error(request, "Enter a valid quantity.")
        return redirect("cart_view")

    product = Product.objects.filter(pk=numeric_product_id, active=True).first()
    if product is None or quantity <= 0:
        cart.pop(product_id, None)
    elif quantity > product.stock:
        messages.error(request, f"Only {product.stock} of that item are available.")
    else:
        cart[str(product.pk)] = quantity

    request.session[CART_SESSION_KEY] = cart
    return redirect("cart_view")


def checkout(request):
    rows = _cart_rows(request)
    if not rows:
        messages.info(request, "Add an item to your cart before checking out.")
        return redirect("shop_home")

    customer_user = (
        request.user
        if request.user.is_authenticated and not request.user.is_staff
        else None
    )
    form = CheckoutForm(
        request.POST or None,
        initial={
            "full_name": customer_user.get_full_name() or customer_user.username,
            "email": customer_user.email,
        } if customer_user else {},
    )

    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                order = Order.objects.create(
                    user=customer_user,
                    full_name=form.cleaned_data["full_name"],
                    email=form.cleaned_data["email"],
                    address=form.cleaned_data["address"],
                    city=form.cleaned_data["city"],
                    postal_code=form.cleaned_data["postal_code"],
                )
                for row in rows:
                    product = row["product"]
                    quantity = row["quantity"]
                    updated = Product.objects.filter(
                        pk=product.pk,
                        active=True,
                        stock__gte=quantity,
                    ).update(stock=F("stock") - quantity)
                    if updated != 1:
                        raise InsufficientStock(product.name)
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=product.name,
                        unit_price=product.price,
                        quantity=quantity,
                    )
        except InsufficientStock as error:
            messages.error(
                request,
                f"{error} no longer has enough stock. Please review your cart.",
            )
            return redirect("cart_view")

        request.session[CART_SESSION_KEY] = {}
        messages.success(request, "Your order has been placed.")
        if customer_user is None:
            guest_order_references = request.session.get(
                GUEST_ORDER_SESSION_KEY, []
            )
            guest_order_references.append(str(order.reference))
            request.session[GUEST_ORDER_SESSION_KEY] = guest_order_references[-20:]
        return redirect("order_detail", reference=order.reference)

    return render(
        request,
        "shop/checkout.html",
        {
            "form": form,
            "rows": rows,
            "subtotal": sum(
                (row["line_total"] for row in rows),
                start=Decimal("0.00"),
            ),
            "cart_count": _cart_count(request),
        },
    )


@login_required
def order_history(request):
    orders = request.user.shop_orders.prefetch_related("items")
    return render(
        request,
        "shop/order_history.html",
        {"orders": orders, "cart_count": _cart_count(request)},
    )


def order_detail(request, reference):
    order = get_object_or_404(Order.objects.prefetch_related("items"), reference=reference)
    is_order_owner = request.user.is_authenticated and order.user_id == request.user.pk
    has_guest_access = str(order.reference) in request.session.get(
        GUEST_ORDER_SESSION_KEY, []
    )
    if not is_order_owner and not (order.user_id is None and has_guest_access):
        raise Http404

    return render(
        request,
        "shop/order_detail.html",
        {
            "order": order,
            "cart_count": _cart_count(request),
            "show_login_prompt": order.user_id is None,
        },
    )


@ensure_csrf_cookie
@login_required(login_url="login_page")
def page_chat(request):
    return render(
        request,
        "chat.html",
        {"cart_count": _cart_count(request)},
    )


def _build_store_context(user):
    products = Product.objects.filter(active=True).order_by("name")[:30]
    product_lines = [
        (
            f"- {product.name} | {product.get_category_display()} | "
            f"PKR {product.price} | "
            f"{'in stock' if product.stock else 'out of stock'}"
        )
        for product in products
    ]

    orders = user.shop_orders.prefetch_related("items")[:10]
    order_lines = []
    for order in orders:
        order_lines.append(
            f"- {str(order.reference)[:8].upper()} | {order.get_status_display()} | "
            f"PKR {order.total} | "
            f"{', '.join(item.product_name for item in order.items.all())}"
        )

    return (
        f"SIGNED-IN CUSTOMER: {user.username}\n"
        "CURRENT PRODUCT CATALOG:\n"
        + ("\n".join(product_lines) or "No products are currently listed.")
        + "\n\nORDERS FOR THE SIGNED-IN CUSTOMER ONLY:\n"
        + ("\n".join(order_lines) or "This customer has no orders yet.")
    )


def _answer_store_question(user, question):
    normalized = re.sub(r"[^a-z0-9]+", " ", question.casefold()).strip()
    words = set(normalized.split())
    if words.intersection(
        {"payment", "payments", "pay", "checkout", "cash", "cod"}
    ):
        return (
            "We currently offer cash on delivery. You can pay in cash when "
            "your order arrives; online card payment is not available yet."
        )

    if any(term in normalized.split() for term in ("delivery", "shipping")):
        return (
            "Delivery charges and timing are confirmed with you when your "
            "order is placed. We currently offer cash on delivery."
        )

    if any(term in normalized for term in ("refund", "return")):
        return (
            "Our return and refund policy is not listed yet. Please contact "
            "our support team so they can help with your request."
        )

    if any(term in normalized.split() for term in ("order", "orders", "tracking")):
        orders = list(user.shop_orders.prefetch_related("items")[:10])
        if not orders:
            return "There are no orders on your account yet. Once you place one, I can help you check its status."

        reference = next(
            (
                token.upper()
                for token in normalized.upper().split()
                if len(token) >= 6
                and any(str(order.reference).startswith(token.lower()) for order in orders)
            ),
            None,
        )
        if reference:
            orders = [
                order
                for order in orders
                if str(order.reference).startswith(reference.lower())
            ]

        order_summary = "\n".join(
            (
                f"Order {str(order.reference)[:8].upper()} — "
                f"{order.get_status_display()} "
                f"(placed {order.created_at:%b %d, %Y}). "
                f"Items: {', '.join(item.product_name for item in order.items.all())}. "
                f"Total: PKR {order.total:,.0f}; payment: "
                f"{order.get_payment_method_display()}."
            )
            for order in orders
        )
        return (
            f"Here are your latest orders:\n{order_summary}\n"
            "See your full order history: /orders/"
        )

    category = None
    if words.intersection({"shoe", "shoes", "sneaker", "sneakers", "footwear"}):
        category = Product.Category.SHOES
    elif words.intersection({"watch", "watches", "timepiece", "timepieces"}):
        category = Product.Category.WATCHES

    products = Product.objects.filter(active=True)
    if category:
        products = products.filter(category=category)
    else:
        normalized_products = [
            (
                product,
                re.sub(r"[^a-z0-9]+", " ", product.name.casefold()).strip(),
            )
            for product in products
        ]
        matched_product = next(
            (
                product
                for product, product_name in normalized_products
                if product_name and product_name in normalized
            ),
            None,
        )
        if matched_product:
            availability = (
                f"{matched_product.stock} in stock."
                if matched_product.stock
                else "Currently out of stock."
            )
            return (
                f"{matched_product.name} is a {matched_product.get_category_display().lower()} "
                f"priced at PKR {matched_product.price:,.0f}. "
                f"{matched_product.description} {availability} "
                f"View product and add it to your bag: /products/{matched_product.slug}/"
            )
        return None

    if "stock" in words or "available" in words:
        products = products.filter(stock__gt=0)
    products = list(products.order_by("price", "name"))
    if not products:
        return "We don't currently have any matching items in stock."

    category_name = dict(Product.Category.choices)[category]
    lines = [
        f"- {product.name}: PKR {product.price:,.0f} "
        f"({'in stock' if product.stock else 'out of stock'}). "
        f"{product.description} "
        f"View product and add it to your bag: /products/{product.slug}/"
        for product in products
    ]
    return f"Here are the {category_name.lower()} in our catalog:\n" + "\n".join(lines)


@require_POST
@csrf_protect
@login_required(login_url="login_page")
def chat_api(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON request."}, status=400)

    if not isinstance(data, dict):
        return JsonResponse(
            {"error": "The request body must be a JSON object."},
            status=400,
        )

    question = data.get("question")
    if not isinstance(question, str) or not question.strip():
        return JsonResponse({"error": "Please enter a question."}, status=400)
    if len(question) > 2000:
        return JsonResponse(
            {"error": "Please keep your message under 2,000 characters."},
            status=400,
        )

    store_answer = _answer_store_question(request.user, question.strip())
    if store_answer is not None:
        return JsonResponse({"answer": store_answer})

    answer = get_customer_response(
        question.strip(),
        store_context=_build_store_context(request.user),
    )
    return JsonResponse({"answer": answer})
