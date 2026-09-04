import re
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError


def normalize_phone(phone_str):
    """
    Normalizes any Uzbek/international phone format to canonical +998XXXXXXXXX.
    """
    if not phone_str:
        return ""
    digits = re.sub(r'\D', '', str(phone_str))
    if len(digits) == 9:
        return f"+998{digits}"
    elif len(digits) == 12 and digits.startswith('998'):
        return f"+{digits}"
    elif digits:
        return f"+{digits}"
    return phone_str.strip()


class UserRegisterForm(forms.Form):
    first_name = forms.CharField(
        max_length=50,
        required=True,
        label="Ismingiz",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
            'placeholder': 'Ismingizni kiriting'
        })
    )
    phone = forms.CharField(
        max_length=30,
        required=True,
        label="Telefon raqamingiz",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
            'placeholder': '+998 90 123 45 67',
            'type': 'tel'
        })
    )
    password1 = forms.CharField(
        required=True,
        label="Parol",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
            'placeholder': 'Parol kiriting'
        })
    )
    password2 = forms.CharField(
        required=True,
        label="Parolni tasdiqlang",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
            'placeholder': 'Parolni qayta kiriting'
        })
    )

    def clean_phone(self):
        raw_phone = self.cleaned_data.get('phone', '').strip()
        norm_phone = normalize_phone(raw_phone)
        digits = re.sub(r'\D', '', norm_phone)
        if len(digits) < 9:
            raise ValidationError("Telefon raqami noto'g'ri kiritildi.")
        
        # Check if user with this phone/username already exists
        if User.objects.filter(username=norm_phone).exists():
            raise ValidationError("Ushbu telefon raqami allaqachon ro'yxatdan o'tgan. Iltimos, tizimga kiring.")
        return norm_phone

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Kiritilgan parollar bir-biriga mos kelmadi.")
        return cleaned_data

    def save(self):
        norm_phone = self.cleaned_data['phone']
        first_name = self.cleaned_data['first_name']
        password = self.cleaned_data['password1']

        user = User.objects.create_user(
            username=norm_phone,
            first_name=first_name,
            password=password
        )
        return user


class UserLoginForm(forms.Form):
    phone = forms.CharField(
        max_length=30,
        required=True,
        label="Telefon raqami",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
            'placeholder': '+998 90 123 45 67',
            'type': 'tel'
        })
    )
    password = forms.CharField(
        required=True,
        label="Parol",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
            'placeholder': 'Parolingiz'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        raw_phone = cleaned_data.get('phone', '').strip()
        password = cleaned_data.get('password', '')

        if raw_phone and password:
            norm_phone = normalize_phone(raw_phone)
            # Authenticate via username (normalized phone) or raw input
            user = authenticate(username=norm_phone, password=password)
            if not user:
                user = authenticate(username=raw_phone, password=password)
            
            if not user:
                raise ValidationError("Telefon raqam yoki parol noto'g'ri.")
            cleaned_data['user'] = user

        return cleaned_data

    def get_user(self):
        return self.cleaned_data.get('user')
