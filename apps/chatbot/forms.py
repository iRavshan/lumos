from django import forms
from .models import ChatbotConfig


class ChatbotConfigForm(forms.ModelForm):
    class Meta:
        model = ChatbotConfig
        fields = ['theme_color']
        widgets = {
            'theme_color': forms.TextInput(attrs={
                'id': 'themeColorHex',
                'class': 'w-36 px-3.5 py-2.5 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none font-mono text-sm font-semibold uppercase',
                'placeholder': '#4F46E5',
                'maxlength': '7'
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


class AgentConfigForm(forms.ModelForm):
    class Meta:
        model = ChatbotConfig
        fields = [
            'bot_name', 
            'welcome_message',
            'response_delay_enabled', 
            'first_message_delay_seconds', 
            'subsequent_message_delay_seconds', 
            'split_messages',
            'extra_knowledge',
        ]
        widgets = {
            'bot_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-[#262626] bg-slate-50 dark:bg-[#1E1E1E] text-slate-900 dark:text-[#F5F1E8] focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200 text-sm font-semibold',
                'placeholder': 'Masalan: Anvar'
            }),
            'welcome_message': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-[#262626] bg-slate-50 dark:bg-[#1E1E1E] text-slate-900 dark:text-[#F5F1E8] focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200 text-sm leading-relaxed',
                'rows': 4,
                'placeholder': "Assalomu alaykum! Sizga qanday yordam bera olaman?"
            }),
            'response_delay_enabled': forms.CheckboxInput(attrs={
                'class': 'sr-only peer',
                'id': 'responseDelayToggle',
            }),
            'first_message_delay_seconds': forms.NumberInput(attrs={
                'class': 'w-20 px-3 py-2 text-center font-mono font-bold text-sm rounded-xl border border-[#E7E5E1] dark:border-[#262626] bg-slate-50 dark:bg-[#1E1E1E] text-indigo-600 dark:text-indigo-400 outline-none focus:ring-2 focus:ring-indigo-500',
                'min': '1',
                'max': '60',
                'id': 'firstDelayInput',
            }),
            'subsequent_message_delay_seconds': forms.NumberInput(attrs={
                'class': 'w-20 px-3 py-2 text-center font-mono font-bold text-sm rounded-xl border border-[#E7E5E1] dark:border-[#262626] bg-slate-50 dark:bg-[#1E1E1E] text-violet-600 dark:text-violet-400 outline-none focus:ring-2 focus:ring-violet-500',
                'min': '1',
                'max': '60',
                'id': 'subsequentDelayInput',
            }),
            'split_messages': forms.CheckboxInput(attrs={
                'class': 'sr-only peer',
                'id': 'splitMessagesToggle',
            }),
            'extra_knowledge': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-[#262626] bg-slate-50 dark:bg-[#1E1E1E] text-slate-900 dark:text-[#F5F1E8] focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200 text-xs sm:text-sm',
                'rows': 5,
                'placeholder': "Masalan:\n- Ish vaqti: Har kuni 09:00 dan 20:00 gacha\n- Toshkent bo'ylab yetkazib berish: 20 000 so'm yoki 300 000 dan ortiq xaridda bepul\n- Kafolat: 1 yil"
            }),
        }

