from django.urls import path

from chat import views

urlpatterns = [
    path("", views.shop_home, name="shop_home"),
    path("products/<slug:slug>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart_view, name="cart_view"),
    path("cart/add/<slug:slug>/", views.cart_add, name="cart_add"),
    path("cart/update/", views.cart_update, name="cart_update"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.order_history, name="order_history"),
    path("orders/<uuid:reference>/", views.order_detail, name="order_detail"),
    path("chat/", views.page_chat, name="page_chat"),
    path("chat/api/", views.chat_api, name="chat_api"),
]