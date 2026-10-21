from decimal import Decimal

from django.db import migrations


PRODUCTS = (
    (
        "cloudstep-runner",
        "Cloudstep Runner",
        "shoes",
        "Lightweight everyday trainers with a cushioned sole and breathable knit upper.",
        "12999.00",
        18,
        True,
    ),
    (
        "citystride-classic",
        "Citystride Classic",
        "shoes",
        "A clean, versatile sneaker made for comfortable days around town.",
        "10999.00",
        14,
        True,
    ),
    (
        "trailform-outdoor",
        "Trailform Outdoor",
        "shoes",
        "Grippy, supportive outdoor shoes ready for weekend trails and changing weather.",
        "15999.00",
        9,
        False,
    ),
    (
        "courtline-low",
        "Courtline Low",
        "shoes",
        "A classic low-top silhouette with a durable finish and easy everyday styling.",
        "8999.00",
        21,
        False,
    ),
    (
        "moment-classic",
        "Moment Classic",
        "watches",
        "A refined everyday watch with a clear dial and a comfortable adjustable strap.",
        "18999.00",
        11,
        True,
    ),
    (
        "northstar-minimal",
        "Northstar Minimal",
        "watches",
        "A slim, minimalist timepiece that pairs easily with work and weekend outfits.",
        "16999.00",
        8,
        True,
    ),
    (
        "fieldmark-sport",
        "Fieldmark Sport",
        "watches",
        "A durable sporty watch with an easy-to-read face for active days.",
        "13999.00",
        12,
        False,
    ),
    (
        "heritage-automatic",
        "Heritage Automatic",
        "watches",
        "A timeless statement watch with a detailed dial and polished finish.",
        "24999.00",
        5,
        False,
    ),
)


def add_sample_products(apps, schema_editor):
    Product = apps.get_model("chat", "Product")
    for slug, name, category, description, price, stock, featured in PRODUCTS:
        Product.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "category": category,
                "description": description,
                "price": Decimal(price),
                "stock": stock,
                "featured": featured,
                "active": True,
            },
        )


def remove_sample_products(apps, schema_editor):
    Product = apps.get_model("chat", "Product")
    Product.objects.filter(slug__in=[product[0] for product in PRODUCTS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_sample_products, remove_sample_products),
    ]
