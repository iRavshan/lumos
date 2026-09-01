from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView
from .forms import UserRegisterForm, UserLoginForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect('businesses:dashboard')
        
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Xush kelibsiz, {user.username}! Endi biznesingizni ro'yxatdan o'tkazing.")
            return redirect('businesses:onboarding')
        else:
            messages.error(request, "Iltimos, kiritilgan ma'lumotlarni tekshiring.")
    else:
        form = UserRegisterForm()
        
    return render(request, 'accounts/register.html', {'form': form})


class CustomLoginView(LoginView):
    authentication_form = UserLoginForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def form_invalid(self, form):
        messages.error(self.request, "Foydalanuvchi nomi yoki parol noto'g'ri.")
        return super().form_invalid(form)


def logout_view(request):
    logout(request)
    messages.info(request, "Tizimdan muvaffaqiyatli chiqdingiz.")
    return redirect('home')
