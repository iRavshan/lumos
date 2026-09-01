from django import forms
from .models import StaffMember


class StaffMemberForm(forms.ModelForm):
    class Meta:
        model = StaffMember
        fields = ['name', 'role', 'telegram_username', 'sla_minutes', 'is_active', 'is_online']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
                'placeholder': 'Masalan: Sardor Rahimov'
            }),
            'role': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200 bg-white font-medium',
            }),
            'telegram_username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
                'placeholder': '@username'
            }),
            'sla_minutes': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
                'min': '1',
                'max': '120',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500',
            }),
            'is_online': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500',
            }),
        }

    def clean_telegram_username(self):
        tg = self.cleaned_data.get('telegram_username', '').strip()
        if tg and not tg.startswith('@'):
            tg = '@' + tg
        return tg
