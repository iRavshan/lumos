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
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-[#262626] bg-slate-50 dark:bg-[#1E1E1E] text-slate-900 dark:text-[#F5F1E8] focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200 text-sm font-semibold',
            'placeholder': 'Ismingizni kiriting'
        })
    )
    email = forms.EmailField(
        required=True,
        label="Elektron pochta",
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-[#262626] bg-slate-50 dark:bg-[#1E1E1E] text-slate-900 dark:text-[#F5F1E8] focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200 text-sm',
            'placeholder': 'misol@domen.uz',
            'id': 'emailInput'
        })
    )
    password1 = forms.CharField(
        required=True,
        label="Parol",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-[#262626] bg-slate-50 dark:bg-[#1E1E1E] text-slate-900 dark:text-[#F5F1E8] focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200 text-sm',
            'placeholder': 'Parol kiriting'
        })
    )
    password2 = forms.CharField(
        required=True,
        label="Parolni tasdiqlang",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-[#262626] bg-slate-50 dark:bg-[#1E1E1E] text-slate-900 dark:text-[#F5F1E8] focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200 text-sm',
            'placeholder': 'Parolni qayta kiriting'
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
            raise ValidationError("Ushbu elektron pochta allaqachon ro'yxatdan o'tgan. Iltimos, tizimga kiring.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Kiritilgan parollar bir-biriga mos kelmadi.")
        return cleaned_data

    def save(self):
        email = self.cleaned_data['email']
        first_name = self.cleaned_data['first_name']
        password = self.cleaned_data['password1']

        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=first_name,
            password=password
        )
        return user


class UserLoginForm(forms.Form):
    email = forms.CharField(
        required=True,
        label="Elektron pochta",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-[#262626] bg-slate-50 dark:bg-[#1E1E1E] text-slate-900 dark:text-[#F5F1E8] focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200 text-sm',
            'placeholder': 'misol@domen.uz yoki username',
            'id': 'loginEmailInput'
        })
    )
    password = forms.CharField(
        required=True,
        label="Parol",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-[#262626] bg-slate-50 dark:bg-[#1E1E1E] text-slate-900 dark:text-[#F5F1E8] focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200 text-sm',
            'placeholder': 'Parolingiz'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        raw_email = cleaned_data.get('email', '').strip()
        password = cleaned_data.get('password', '')

        if raw_email and password:
            # 1. Try auth directly with input as username
            user = authenticate(username=raw_email, password=password)
            if not user:
                user = authenticate(username=raw_email.lower(), password=password)
            # 2. If not found, look up user by email
            if not user:
                user_obj = User.objects.filter(email__iexact=raw_email).first()
                if user_obj:
                    user = authenticate(username=user_obj.username, password=password)
            # 3. Fallback for legacy phone-based users
            if not user:
                norm_phone = normalize_phone(raw_email)
                user = authenticate(username=norm_phone, password=password)

            if not user:
                raise ValidationError("Elektron pochta yoki parol noto'g'ri.")
            cleaned_data['user'] = user

        return cleaned_data

    def get_user(self):
        return self.cleaned_data.get('user')
