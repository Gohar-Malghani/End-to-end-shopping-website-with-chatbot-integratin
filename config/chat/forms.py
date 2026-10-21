from django import forms


class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=160, label="Full name")
    email = forms.EmailField(max_length=254)
    address = forms.CharField(max_length=240, label="Street address")
    city = forms.CharField(max_length=120)
    postal_code = forms.CharField(max_length=24, label="Postal code")

