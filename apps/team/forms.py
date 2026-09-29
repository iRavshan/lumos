from django import forms
from .models import StaffMember


class StaffMemberForm(forms.ModelForm):
    class Meta:
        model = StaffMember
        fields = ['name', 'role']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3.5 py-2.5 rounded-xl border border-[#E7E5E1] dark:border-[#262626] bg-slate-50 dark:bg-[#1E1E1E] text-slate-900 dark:text-[#F5F1E8] placeholder-slate-400 dark:placeholder-slate-500 text-xs focus:ring-2 focus:ring-slate-300 dark:focus:ring-zinc-700 focus:bg-white dark:focus:bg-[#141414] outline-none font-medium transition',
                'placeholder': 'Masalan: Sardor Rahimov',
                'required': 'required',
            }),
            'role': forms.Select(attrs={
                'class': 'w-full px-3.5 py-2.5 rounded-xl border border-[#E7E5E1] dark:border-[#262626] bg-slate-50 dark:bg-[#1E1E1E] text-slate-900 dark:text-[#F5F1E8] text-xs focus:ring-2 focus:ring-slate-300 dark:focus:ring-zinc-700 outline-none font-medium transition cursor-pointer',
            }),
        }

