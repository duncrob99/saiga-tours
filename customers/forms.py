from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

from zxcvbn import zxcvbn
from email_validator import validate_email, EmailNotValidError
from hcaptcha_field import hCaptchaField

class NewPasswordForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password', 'password2']

    password = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    def clean_password(self):
        password_score = zxcvbn(self.cleaned_data['password'], [self.instance.username, self.cleaned_data['first_name'], self.cleaned_data['last_name']])['guesses_log10'] * 10

        if password_score < 75:
            raise forms.ValidationError('Password is too weak')
        return self.cleaned_data['password']

    def clean_password2(self):
        if self.cleaned_data['password'] != self.cleaned_data['password2']:
            raise forms.ValidationError('Passwords do not match')
        return self.cleaned_data['password2']

    def clean_email(self):
        return self.instance.email

    def save(self, commit=True):
        self.instance.set_password(self.cleaned_data['password'])
        if commit:
            self.instance.save()
        return self.instance


class NewUserForm(UserCreationForm):
    captcha = hCaptchaField()

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password1', 'password2']

    def clean_password1(self):
        password_score = zxcvbn(self.cleaned_data['password1'], [self.instance.username, self.cleaned_data['first_name'], self.cleaned_data['last_name']])['guesses_log10'] * 10

        if password_score < 75:
            raise forms.ValidationError('Password is too weak')
        return self.cleaned_data['password1']

    def clean_password2(self):
        if self.cleaned_data['password1'] != self.cleaned_data['password2']:
            raise forms.ValidationError('Passwords do not match')
        return self.cleaned_data['password2']

    def clean_email(self):
        validated_email = None

        try:
            validated_email = validate_email(self.cleaned_data['email']).email
        except EmailNotValidError as e:
            raise forms.ValidationError(str(e))
        return validated_email

    def save(self, commit=True):
        self.instance.set_password(self.cleaned_data['password1'])
        if commit:
            self.instance.save()
        return self.instance
