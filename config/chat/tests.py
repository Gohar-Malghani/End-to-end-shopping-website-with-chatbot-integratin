import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from chat.models import Order, OrderItem, Product


class ChatApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='chat-user',
            password='test-password',
        )
        self.client.force_login(self.user)
        self.product = Product.objects.create(
            name="Test Runner",
            slug="test-runner",
            category=Product.Category.SHOES,
            description="Comfortable running shoes.",
            price=Decimal("10000.00"),
            stock=5,
        )

    def test_chat_page_uses_named_api_route_and_static_assets(self):
        response = self.client.get(reverse('page_chat'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-chat-url="/chat/api/"')
        self.assertContains(response, 'href="/static/chat.css"')
        self.assertContains(response, 'src="/static/chat.js?v=2"')
        self.assertContains(response, "Find something")
        self.assertContains(response, "Continue shopping")
        self.assertContains(response, "Hi, chat-user")
        self.assertContains(response, "Welcome, chat-user.")

    @patch('chat.views.get_customer_response', return_value='How can I help?')
    def test_chat_api_returns_assistant_response(self, get_customer_response):
        response = self.client.post(
            reverse('chat_api'),
            data=json.dumps({'question': 'Hello, I am exploring the shop.'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'answer': 'How can I help?'})
        get_customer_response.assert_called_once()
        self.assertEqual(
            get_customer_response.call_args.args[0],
            'Hello, I am exploring the shop.',
        )
        self.assertIn(
            "Test Runner",
            get_customer_response.call_args.kwargs["store_context"],
        )
        self.assertIn(
            "ORDERS FOR THE SIGNED-IN CUSTOMER ONLY",
            get_customer_response.call_args.kwargs["store_context"],
        )
        self.assertIn("SIGNED-IN CUSTOMER: chat-user", get_customer_response.call_args.kwargs["store_context"])

    def test_chat_context_includes_only_the_signed_in_customers_orders(
        self,
    ):
        own_order = Order.objects.create(
            user=self.user,
            full_name="Chat User",
            email="chat@example.com",
            address="1 Customer Lane",
            city="Lahore",
            postal_code="54000",
        )
        OrderItem.objects.create(
            order=own_order,
            product=self.product,
            product_name="Test Runner",
            unit_price=self.product.price,
            quantity=1,
        )
        other_user = get_user_model().objects.create_user(
            username="other-chat-user",
            password="another-password",
        )
        other_order = Order.objects.create(
            user=other_user,
            full_name="Other User",
            email="other@example.com",
            address="2 Private Lane",
            city="Lahore",
            postal_code="54000",
        )
        OrderItem.objects.create(
            order=other_order,
            product=self.product,
            product_name="Private Purchase",
            unit_price=self.product.price,
            quantity=1,
        )

        response = self.client.post(
            reverse('chat_api'),
            data=json.dumps({'question': 'Where is my order?'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(str(own_order.reference)[:8].upper(), response.json()["answer"])
        self.assertIn("/orders/", response.json()["answer"])
        self.assertNotIn("Private Purchase", response.json()["answer"])

    @patch('chat.views.get_customer_response')
    def test_chat_recommendations_are_limited_to_live_catalog_category(
        self,
        get_customer_response,
    ):
        response = self.client.post(
            reverse('chat_api'),
            data=json.dumps(
                {'question': 'Recommend in-stock shoes from the shop.'}
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Cloudstep Runner", response.json()["answer"])
        self.assertIn("/products/cloudstep-runner/", response.json()["answer"])
        self.assertNotIn("Moment Classic", response.json()["answer"])
        get_customer_response.assert_not_called()

    @patch('chat.views.get_customer_response')
    def test_product_question_includes_a_link_to_add_product_to_bag(
        self,
        get_customer_response,
    ):
        response = self.client.post(
            reverse('chat_api'),
            data=json.dumps({'question': 'Can I buy Test Runner?'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("/products/test-runner/", response.json()["answer"])
        get_customer_response.assert_not_called()

    @patch('chat.views.get_customer_response')
    def test_chat_answers_payment_questions_from_store_settings(
        self,
        get_customer_response,
    ):
        response = self.client.post(
            reverse('chat_api'),
            data=json.dumps({'question': 'What payment options do you have?'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("cash on delivery", response.json()["answer"])
        self.assertIn(
            "online card payment is not available yet",
            response.json()["answer"],
        )
        get_customer_response.assert_not_called()

    def test_chat_api_rejects_empty_question(self):
        response = self.client.post(
            reverse('chat_api'),
            data=json.dumps({'question': '  '}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'error': 'Please enter a question.'})

    def test_chat_api_rejects_invalid_json(self):
        response = self.client.post(
            reverse('chat_api'),
            data='{',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'error': 'Invalid JSON request.'})


class StorefrontFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="shopper",
            email="shopper@example.com",
            password="correct-horse-battery",
        )
        self.product = Product.objects.create(
            name="Weekend Watch",
            slug="weekend-watch",
            category=Product.Category.WATCHES,
            description="A simple everyday watch.",
            price=Decimal("15000.00"),
            stock=4,
        )

    def add_product_to_cart(self, quantity=1):
        session = self.client.session
        session["shopping_cart"] = {str(self.product.pk): quantity}
        session.save()

    def test_shop_filters_and_searches_products(self):
        homepage = self.client.get(reverse("shop_home"))

        self.assertEqual(homepage.status_code, 200)
        self.assertContains(homepage, "shop/images/shoes-lifestyle.jpg")
        self.assertContains(homepage, "shop/images/watch-classic.jpg")
        self.assertContains(homepage, "shop/images/shoes-court.jpg")

        response = self.client.get(reverse("shop_home"), {"q": "watch"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Weekend Watch")
        self.assertNotContains(response, "Cloudstep Runner")

        shoes = self.client.get(
            reverse("shop_home"),
            {"category": Product.Category.SHOES},
        )
        self.assertNotContains(shoes, "Weekend Watch")

    def test_product_page_and_add_to_cart(self):
        detail = self.client.get(
            reverse("product_detail", kwargs={"slug": self.product.slug})
        )
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Cash on delivery available")
        self.assertContains(detail, "shop/images/watch-classic.jpg")

        response = self.client.post(
            reverse("cart_add", kwargs={"slug": self.product.slug})
        )
        self.assertRedirects(
            response,
            reverse("product_detail", kwargs={"slug": self.product.slug}),
        )
        self.assertEqual(
            self.client.session["shopping_cart"],
            {str(self.product.pk): 1},
        )

    def test_guest_can_open_checkout(self):
        self.add_product_to_cart()

        response = self.client.get(reverse("checkout"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Delivery details")
        self.assertContains(response, "Place my order")

    def test_guest_checkout_creates_order_and_shows_login_prompt(self):
        self.add_product_to_cart(quantity=2)

        response = self.client.post(
            reverse("checkout"),
            {
                "full_name": "Guest Shopper",
                "email": "guest@example.com",
                "address": "42 Market Road",
                "city": "Lahore",
                "postal_code": "54000",
            },
        )

        order = Order.objects.get()
        self.assertIsNone(order.user)
        self.assertRedirects(
            response,
            reverse("order_detail", kwargs={"reference": order.reference}),
        )
        self.assertEqual(order.items.get().quantity, 2)
        self.assertEqual(self.client.session["shopping_cart"], {})
        self.assertIn(str(order.reference), self.client.session["guest_order_references"])

        confirmation = self.client.get(
            reverse("order_detail", kwargs={"reference": order.reference})
        )
        self.assertEqual(confirmation.status_code, 200)
        self.assertContains(confirmation, "Please sign in")
        self.assertContains(confirmation, "Continue as guest")
        self.assertContains(confirmation, "guest-order-prompt")
        self.assertContains(confirmation, 'src="/static/shop-chat.js?v=3"')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)

    def test_staff_checkout_is_guest_checkout_without_logging_out_admin(self):
        admin = get_user_model().objects.create_superuser(
            username="store-admin",
            email="admin@example.com",
            password="Admin-password-293!",
        )
        self.client.force_login(admin)
        self.add_product_to_cart()

        response = self.client.post(
            reverse("checkout"),
            {
                "full_name": "Guest Shopper",
                "email": "guest@example.com",
                "address": "42 Market Road",
                "city": "Lahore",
                "postal_code": "54000",
            },
        )

        order = Order.objects.get()
        self.assertIsNone(order.user)
        self.assertRedirects(
            response,
            reverse("order_detail", kwargs={"reference": order.reference}),
        )
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user, admin)
        homepage = self.client.get(reverse("shop_home"))
        self.assertContains(homepage, "Admin")
        self.assertContains(homepage, "Join us")
        self.assertNotContains(homepage, "Hi, store-admin")

    def test_guest_order_is_only_visible_in_the_session_that_placed_it(self):
        self.add_product_to_cart()
        self.client.post(
            reverse("checkout"),
            {
                "full_name": "Guest Shopper",
                "email": "guest@example.com",
                "address": "42 Market Road",
                "city": "Lahore",
                "postal_code": "54000",
            },
        )
        order = Order.objects.get()
        self.client.logout()
        response = self.client.get(
            reverse("order_detail", kwargs={"reference": order.reference})
        )
        self.assertEqual(response.status_code, 404)

    def test_checkout_places_cod_order_and_decrements_inventory(self):
        self.client.force_login(self.user)
        self.add_product_to_cart(quantity=2)

        response = self.client.post(
            reverse("checkout"),
            {
                "full_name": "Shopper Name",
                "email": "shopper@example.com",
                "address": "42 Market Road",
                "city": "Lahore",
                "postal_code": "54000",
            },
        )

        order = Order.objects.get(user=self.user)
        self.assertRedirects(
            response,
            reverse("order_detail", kwargs={"reference": order.reference}),
        )
        self.assertEqual(order.payment_method, Order.PaymentMethod.CASH_ON_DELIVERY)
        self.assertEqual(order.total, Decimal("30000.00"))
        self.assertEqual(order.items.get().product_name, "Weekend Watch")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)
        self.assertEqual(self.client.session["shopping_cart"], {})
        confirmation = self.client.get(
            reverse("order_detail", kwargs={"reference": order.reference})
        )
        self.assertNotContains(confirmation, "guest-order-prompt")

    def test_checkout_rejects_insufficient_stock_without_creating_order(self):
        self.client.force_login(self.user)
        self.add_product_to_cart(quantity=5)

        response = self.client.post(
            reverse("checkout"),
            {
                "full_name": "Shopper Name",
                "email": "shopper@example.com",
                "address": "42 Market Road",
                "city": "Lahore",
                "postal_code": "54000",
            },
        )

        self.assertRedirects(response, reverse("cart_view"))
        self.assertFalse(Order.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 4)

    def test_customer_cannot_view_another_users_order(self):
        other_user = get_user_model().objects.create_user(
            username="another-shopper",
            password="another-correct-password",
        )
        order = Order.objects.create(
            user=other_user,
            full_name="Other Shopper",
            email="other@example.com",
            address="5 Safe Street",
            city="Lahore",
            postal_code="54000",
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("order_detail", kwargs={"reference": order.reference})
        )

        self.assertEqual(response.status_code, 404)
