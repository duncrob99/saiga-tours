from django import forms


class SubscriptionForm(forms.Form):
    name = forms.CharField(required=False, max_length=500)
    email = forms.EmailField(required=True)
