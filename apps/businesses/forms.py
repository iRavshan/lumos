from django import forms
from .models import Business

CATEGORY_CHOICES = (
    ('', '— Faoliyat turini tanlang —'),
    ('IT & Dasturlash', 'IT & Dasturlash / Texnologiya'),
    ('Savdo & Do\'kon', 'Savdo & Do\'kon / E-commerce'),
    ('Ta\'lim & O\'quv markazi', 'Ta\'lim & O\'quv markazi / Kurslar'),
    ('Yetkazib berish & Logistika', 'Yetkazib berish & Logistika / Kuryerlik'),
    ('Xizmat ko\'rsatish', 'Maishiy & Professional xizmat ko\'rsatish'),
    ('Restoran & Kafe', 'Restoran, Kafe & Umumiy ovqatlanish'),
    ('Tibbiyot & Salomatlik', 'Tibbiyot, Klinika & Salomatlik'),
    ('Go\'zallik & Spa', 'Go\'zallik saloni, Sartaroshxona & Spa'),
    ('Ishlab chiqarish', 'Ishlab chiqarish & Sanoat'),
    ('Moliya & Konsalting', 'Moliya, Huquq & Konsalting'),
    ('Boshqa', 'Boshqa soha'),
)


class BusinessForm(forms.ModelForm):
    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        required=False,
        label="Soha / Faoliyat turi",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200 bg-white font-medium text-slate-800'
        })
    )
    description_file = forms.FileField(
        required=False,
        label=".txt fayl orqali yuklash",
        widget=forms.FileInput(attrs={
            'id': 'descriptionFileInput',
            'accept': '.txt,text/plain',
            'class': 'hidden'
        })
    )

    class Meta:
        model = Business
        fields = ['name', 'category', 'website', 'telegram', 'instagram', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200',
                'placeholder': 'Masalan: Super IT Academy, Fresh Bakery, AutoFix...'
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
            'description': forms.Textarea(attrs={
                'id': 'descriptionTextarea',
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition duration-200 text-sm leading-relaxed',
                'rows': 6,
                'placeholder': 'Biznesingizning maqsadi, taklif qiladigan xizmatlari, afzalliklari, narxlari va qulayliklari haqida yozing yoki pastdagi tugma orqali .txt fayl yuklang...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].required = True
        self.fields['website'].required = False
        self.fields['telegram'].required = False
        self.fields['instagram'].required = False
        self.fields['description'].required = False

    def clean(self):
        cleaned_data = super().clean()
        desc = cleaned_data.get('description', '').strip()
        uploaded_file = cleaned_data.get('description_file')

        if uploaded_file:
            try:
                content = uploaded_file.read().decode('utf-8')
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                content = uploaded_file.read().decode('latin-1', errors='ignore')
            if content.strip():
                desc = (desc + "\n\n" + content.strip()).strip() if desc else content.strip()
                cleaned_data['description'] = desc

        if not desc:
            self.add_error('description', "Iltimos, biznesingiz haqida ma'lumot kiriting yoki .txt fayl yuklang.")

        return cleaned_data
