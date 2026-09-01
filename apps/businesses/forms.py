from django import forms
from .models import Business


class BusinessForm(forms.ModelForm):
    class Meta:
        model = Business
        fields = ['name', 'category', 'website', 'telegram', 'instagram', 'phone', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
                'placeholder': 'Masalan: Super IT Academy, Fresh Bakery, AutoFix...'
            }),
            'category': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
                'placeholder': 'Masalan: IT & Texnologiya, Umumiy ovqatlanish, Savdo...'
            }),
            'website': forms.URLInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
                'placeholder': 'https://misol.uz'
            }),
            'telegram': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
                'placeholder': '@biznesingiz yoki https://t.me/biznesingiz'
            }),
            'instagram': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
                'placeholder': '@biznesingiz yoki https://instagram.com/biznesingiz'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
                'placeholder': '+998 90 123 45 67'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
                'rows': 5,
                'placeholder': 'Biznesingizning maqsadi, taklif qiladigan xizmatlari va afzalliklari haqida yozing...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].required = True
        self.fields['description'].required = True
