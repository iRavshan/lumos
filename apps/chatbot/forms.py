from django import forms
from .models import ChatbotConfig


class ChatbotConfigForm(forms.ModelForm):
    class Meta:
        model = ChatbotConfig
        fields = ['theme_color', 'is_active']
        widgets = {
            'theme_color': forms.TextInput(attrs={
                'id': 'themeColorHex',
                'class': 'w-36 px-3.5 py-2.5 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none font-mono text-sm font-semibold uppercase',
                'placeholder': '#4F46E5',
                'maxlength': '7'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500',
            }),
        }

    def clean_theme_color(self):
        color = self.cleaned_data.get('theme_color', '').strip()
        if not color:
            return '#4f46e5'
        if not color.startswith('#'):
            color = '#' + color
        import re
        if not re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', color):
            raise forms.ValidationError("To'g'ri HEX rang kodini kiriting (masalan: #4F46E5).")
        return color.lower()


class TelegramBotConfigForm(forms.ModelForm):
    class Meta:
        model = ChatbotConfig
        fields = ['telegram_bot_token', 'telegram_bot_active']
        widgets = {
            'telegram_bot_token': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200 font-mono text-sm',
                'placeholder': '123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ...'
            }),
            'telegram_bot_active': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500',
            }),
        }

