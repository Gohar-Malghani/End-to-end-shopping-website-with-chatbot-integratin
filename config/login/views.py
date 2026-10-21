
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST


def login_page(request):
    next_url = request.POST.get("next", "") if request.method == "POST" else request.GET.get("next", "")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        if not username or not password:
            messages.error(request, "Enter both your username and password.")
        else:
            user = authenticate(
                request,
                username=username,
                password=password,
            )

            if user is not None:
                login(request, user)

                if not url_has_allowed_host_and_scheme(
                    next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    next_url = reverse("shop_home")

                return redirect(next_url)

            messages.error(request, "Invalid username or password.")

    return render(request, "login.html", {"next": next_url})


def register_page(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not all([username, email, password, confirm_password]):
            messages.error(request, "Please fill in all fields.")

        elif password != confirm_password:
            messages.error(request, "Passwords do not match.")

        elif User.objects.filter(username__iexact=username).exists():
            messages.error(request, "That username is already in use.")

        elif User.objects.filter(email__iexact=email).exists():
            messages.error(request, "That email is already registered.")

        else:
            new_user = User(username=username, email=email)

            try:
                validate_password(password, user=new_user)

                User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                )

            except ValidationError as error:
                for message in error.messages:
                    messages.error(request, message)

            except IntegrityError:
                messages.error(
                    request,
                    "That username or email is already in use.",
                )

            else:
                messages.success(
                    request,
                    "Account created successfully. Please sign in.",
                )
                if request.user.is_authenticated:
                    return render(request, "register.html")
                return redirect("login_page")

    return render(request, "register.html")


@require_POST
def logout_user(request):
    logout(request)
    return redirect("login_page")
