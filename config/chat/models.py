import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify


class Product(models.Model):
    class Category(models.TextChoices):
        SHOES = "shoes", "Shoes"
        WATCHES = "watches", "Watches"

    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField()
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    stock = models.PositiveIntegerField(default=0)
    image_url = models.URLField(blank=True)
    featured = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-featured", "name")

    def __str__(self):
        return self.name

    @property
    def placeholder_image(self):
        product_photos = {
            "citystride-classic": "shop/images/shoes-classic.jpg",
            "cloudstep-runner": "shop/images/shoes-studio.jpg",
            "courtline-low": "shop/images/shoes-court.jpg",
            "trailform-outdoor": "shop/images/shoes-trail.jpg",
            "fieldmark-sport": "shop/images/watch-wrist.jpg",
            "heritage-automatic": "shop/images/watch-detail.jpg",
            "moment-classic": "shop/images/watch-classic.jpg",
            "northstar-minimal": "shop/images/watch-minimal.jpg",
        }
        if self.slug in product_photos:
            return product_photos[self.slug]
        if self.category == self.Category.SHOES:
            return "shop/images/shoes-lifestyle.jpg"
        return "shop/images/watch-classic.jpg"


class Order(models.Model):
    class Status(models.TextChoices):
        PLACED = "placed", "Order placed"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentMethod(models.TextChoices):
        CASH_ON_DELIVERY = "cod", "Cash on delivery"

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="shop_orders",
        null=True,
        blank=True,
    )
    full_name = models.CharField(max_length=160)
    email = models.EmailField()
    address = models.CharField(max_length=240)
    city = models.CharField(max_length=120)
    postal_code = models.CharField(max_length=24)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLACED,
    )
    payment_method = models.CharField(
        max_length=8,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH_ON_DELIVERY,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Order {self.reference}"

    @property
    def total(self):
        return sum(
            (item.unit_price * item.quantity for item in self.items.all()),
            start=0,
        )


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        related_name="order_items",
        null=True,
        blank=True,
    )
    product_name = models.CharField(max_length=160)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    def __str__(self):
        return f"{self.quantity} × {self.product_name}"
