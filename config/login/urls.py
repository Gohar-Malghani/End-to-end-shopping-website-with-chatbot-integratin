
from django.urls import path
from .views import login_page, register_page, logout_user

urlpatterns = [
    path("", login_page, name="login_page"),
    path("register/", register_page, name="register_page"),
    path("logout/", logout_user, name="logout_user"),
]
