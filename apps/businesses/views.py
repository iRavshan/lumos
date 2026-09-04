from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Business
from .forms import BusinessForm


def landing_view(request):
    if request.user.is_authenticated:
        return redirect('businesses:dashboard')
    
    total_businesses = Business.objects.count()
    recent_businesses = Business.objects.all()[:6]
    return render(request, 'landing.html', {
        'total_businesses': total_businesses,
        'recent_businesses': recent_businesses
    })


@login_required
def onboarding_view(request):
    # If user already registered business, take them directly to dashboard
    if hasattr(request.user, 'business'):
        return redirect('businesses:dashboard')

    if request.method == 'POST':
        form = BusinessForm(request.POST, request.FILES)
        if form.is_valid():
            business = form.save(commit=False)
            business.user = request.user
            if not business.phone and request.user.username.startswith('+'):
                business.phone = request.user.username
            business.save()
            messages.success(request, f"«{business.name}» biznesingiz muvaffaqiyatli ro'yxatdan o'tkazildi!")
            return redirect('businesses:dashboard')
        else:
            messages.error(request, "Iltimos, formadagi xatoliklarni to'g'rilang.")
    else:
        form = BusinessForm()

    return render(request, 'businesses/onboarding.html', {'form': form})


@login_required
def dashboard_view(request):
    # If user hasn't registered a business yet, prompt onboarding
    if not hasattr(request.user, 'business'):
        messages.warning(request, "Dashboarddan foydalanish uchun avval biznesingizni ro'yxatdan o'tkazing.")
        return redirect('businesses:onboarding')

    business = request.user.business
    
    # Ensure chatbot config exists
    from apps.chatbot.models import ChatbotConfig
    chatbot, _ = ChatbotConfig.objects.get_or_create(
        business=business,
        defaults={
            'bot_name': f"{business.name} AI",
            'welcome_message': f"Assalomu alaykum! «{business.name}» virtual yordamchisiman. Sizga qanday yordam bera olaman?"
        }
    )
    
    chat_count = chatbot.messages.filter(role='user').count()
    leads_count = chatbot.sessions.count()
    new_leads_count = chatbot.sessions.filter(status='new').count()
    recent_sessions = chatbot.sessions.prefetch_related('messages')[:5]
    
    context = {
        'business': business,
        'completion': business.completion_percentage,
        'chatbot': chatbot,
        'chat_count': chat_count,
        'leads_count': leads_count,
        'new_leads_count': new_leads_count,
        'recent_sessions': recent_sessions,
    }
    return render(request, 'businesses/dashboard.html', context)


@login_required
def edit_business_view(request):
    if not hasattr(request.user, 'business'):
        return redirect('businesses:onboarding')

    business = request.user.business

    if request.method == 'POST':
        form = BusinessForm(request.POST, request.FILES, instance=business)
        if form.is_valid():
            form.save()
            messages.success(request, "Biznes ma'lumotlari muvaffaqiyatli yangilandi!")
            return redirect('businesses:dashboard')
        else:
            messages.error(request, "Ma'lumotlarni saqlashda xatolik yuz berdi.")
    else:
        form = BusinessForm(instance=business)

    return render(request, 'businesses/edit_business.html', {
        'form': form,
        'business': business
    })


def public_business_preview(request, slug):
    business = get_object_or_404(Business, slug=slug)
    return render(request, 'businesses/public_profile.html', {'business': business})


@login_required
def business_analytics_view(request):
    if not hasattr(request.user, 'business'):
        return redirect('businesses:onboarding')

    business = request.user.business
    period = request.GET.get('period', '30d')
    if period not in ['today', '7d', '30d', 'all']:
        period = '30d'

    from .analytics import get_business_analytics
    analytics_data = get_business_analytics(business, period=period)

    return render(request, 'businesses/analytics.html', {
        'business': business,
        'analytics': analytics_data,
        'period': period,
    })

