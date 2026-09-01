from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm


class UserRegisterForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=50, 
        required=True, 
        label="Ismingiz",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
            'placeholder': 'Ismingizni kiriting'
        })
    )
    last_name = forms.CharField(
        max_length=50, 
        required=False, 
        label="Familiyangiz",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
            'placeholder': 'Familiyangizni kiriting'
        })
    )
    email = forms.EmailField(
        required=True, 
        label="Email manzil",
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
            'placeholder': 'nomingiz@misol.uz'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
            'placeholder': 'Foydalanuvchi nomi (masalan: ali_dev)'
        })
        self.fields['username'].label = "Foydalanuvchi nomi (username)"
        
        if 'password1' in self.fields:
            self.fields['password1'].widget.attrs.update({
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
                'placeholder': 'Kuchli parol kiriting'
            })
            self.fields['password1'].label = "Parol"
        if 'password2' in self.fields:
            self.fields['password2'].widget.attrs.update({
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
                'placeholder': 'Parolni qayta kiriting'
            })
            self.fields['password2'].label = "Parolni tasdiqlang"


class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
            'placeholder': 'Foydalanuvchi nomi'
        })
        self.fields['username'].label = "Foydalanuvchi nomi"
        self.fields['password'].widget.attrs.update({
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
            'placeholder': 'Parolingiz'
        })
        self.fields['password'].label = "Parol"
