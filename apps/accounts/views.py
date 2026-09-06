from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from .forms import UserRegisterForm, UserLoginForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect('businesses:dashboard')
        
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Xush kelibsiz, {user.first_name}! Endi biznesingizni ro'yxatdan o'tkazing.")
            return redirect('businesses:onboarding')
        else:
            messages.error(request, "Iltimos, kiritilgan ma'lumotlarni tekshiring.")
    else:
        form = UserRegisterForm()
        
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('businesses:dashboard')

    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            if user:
                login(request, user)
                messages.success(request, f"Xush kelibsiz, {user.first_name or user.username}!")
                return redirect('businesses:dashboard')
        else:
            messages.error(request, "Elektron pochta yoki parol noto'g'ri.")
    else:
        form = UserLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "Tizimdan muvaffaqiyatli chiqdingiz.")
    return redirect('home')
