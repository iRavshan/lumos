from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
import logging
from .models import Business
from .forms import BusinessForm

logger = logging.getLogger(__name__)


def _fetch_url(url, timeout=4):
    """Helper: fetch a URL and return (content_bytes, content_type) or (None, None)."""
    import urllib.request
    import ssl
    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        if resp.status == 200:
            data = resp.read()
            ct = resp.headers.get('Content-Type', 'image/png')
            # Bo'sh yoki juda kichik rasm ekanligini tekshiramiz
            if len(data) > 100:
                return data, ct
    except Exception:
        pass
    return None, None


@cache_page(60 * 60 * 24)  # 24 soat keshlanadi
def favicon_proxy_view(request, business_id):
    """
    Server-side favicon proxy: biznesning vebsayt faviconini yoki
    Telegram kanal logosini olib qaytaradi.
    Ketma-ketlik: Google S2 → DuckDuckGo → to'g'ridan-to'g'ri saytdan → Telegram avatar
    """
    business = get_object_or_404(Business, pk=business_id)
    domain = business.domain

    # 1-bosqich: Vebsayt faviconi (agar domain bor bo'lsa)
    if domain:
        sources = [
            f"https://www.google.com/s2/favicons?domain={domain}&sz=128",
            f"https://icons.duckduckgo.com/ip3/{domain}.ico",
            f"https://{domain}/favicon.ico",
            f"http://{domain}/favicon.ico",
        ]
        for src in sources:
            data, ct = _fetch_url(src)
            if data:
                return HttpResponse(data, content_type=ct)

    # 2-bosqich: Telegram kanal/guruh logosi (agar telegram bor bo'lsa)
    tg_avatar = business.telegram_avatar_url
    if tg_avatar:
        data, ct = _fetch_url(tg_avatar)
        if data:
            return HttpResponse(data, content_type=ct)

    # 3-bosqich: hech narsa topilmasa — 1x1 shaffof piksel qaytaramiz
    # Brauzer onerror chaqirmaydi, lekin rasm shaffof bo'ladi
    import base64
    transparent_1px = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQI12NgAAIABQAB"
        "Nl7BcQAAAABJRU5ErkJggg=="
    )
    return HttpResponse(transparent_1px, content_type='image/png', status=204)


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
            # Update user profile information (ism, email, parol)
            owner_first_name = request.POST.get('owner_first_name', '').strip()
            owner_email = request.POST.get('owner_email', '').strip()
            password = request.POST.get('password', '').strip()
            password_confirm = request.POST.get('password_confirm', '').strip()

            user_updated = False
            if owner_first_name:
                request.user.first_name = owner_first_name
                user_updated = True
            if owner_email:
                request.user.email = owner_email
                user_updated = True
            if password and password == password_confirm:
                request.user.set_password(password)
                user_updated = True

            if user_updated:
                request.user.save()
                if password and password == password_confirm:
                    from django.contrib.auth import update_session_auth_hash
                    update_session_auth_hash(request, request.user)

            if not business.phone and request.user.username.startswith('+'):
                business.phone = request.user.username
            business.save()

            # Saytni scrape qilib bilimlar bazasiga saqlash
            if business.website:
                try:
                    from apps.knowledge.tasks import scrape_and_embed
                    scrape_and_embed(business)
                except Exception as e:
                    logger.warning("Onboarding scraping xatolik: %s", e)

            # Save chatbot agent configuration from onboarding slides
            from apps.chatbot.models import ChatbotConfig
            bot_name = request.POST.get('bot_name', '').strip() or f"{business.name} AI"
            response_delay_enabled = request.POST.get('response_delay_enabled') in ['true', 'True', '1', 'on']
            
            try:
                first_message_delay_seconds = int(request.POST.get('first_message_delay_seconds', 5))
                if first_message_delay_seconds < 1 or first_message_delay_seconds > 60:
                    first_message_delay_seconds = 5
            except (ValueError, TypeError):
                first_message_delay_seconds = 5

            try:
                subsequent_message_delay_seconds = int(request.POST.get('subsequent_message_delay_seconds', 10))
                if subsequent_message_delay_seconds < 1 or subsequent_message_delay_seconds > 60:
                    subsequent_message_delay_seconds = 10
            except (ValueError, TypeError):
                subsequent_message_delay_seconds = 10

            split_messages = request.POST.get('split_messages') in ['true', 'True', '1', 'on']

            ChatbotConfig.objects.create(
                business=business,
                bot_name=bot_name,
                response_delay_enabled=response_delay_enabled,
                first_message_delay_seconds=first_message_delay_seconds,
                subsequent_message_delay_seconds=subsequent_message_delay_seconds,
                response_delay_seconds=first_message_delay_seconds,
                split_messages=split_messages,
                welcome_message=(
                    f"Assalomu alaykum! {business.name} qo‘llab-quvvatlash xizmatiga xush kelibsiz.\n\n"
                    "Sizni qiziqtirgan barcha savollarni bemalol shu yerga yozib qoldirishingiz mumkin. "
                    "Mutaxassislarimiz savollaringizga shu yerning o‘zida javob berishadi.\n\n"
                    "Sizga qanday yordam bera olamiz?"
                )
            )

            messages.success(request, f"«{business.name}» va savdo agentingiz muvaffaqiyatli yaratildi!")
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
            'welcome_message': (
                f"Assalomu alaykum! {business.name} qo‘llab-quvvatlash xizmatiga xush kelibsiz.\n\n"
                "Sizni qiziqtirgan barcha savollarni bemalol shu yerga yozib qoldirishingiz mumkin. "
                "Mutaxassislarimiz savollaringizga shu yerning o‘zida javob berishadi.\n\n"
                "Sizga qanday yordam bera olamiz?"
            )
        }
    )
    
    chat_count = chatbot.messages.filter(role='user').count()
    leads_count = chatbot.sessions.count()
    new_leads_count = chatbot.sessions.filter(status='new').count()
    recent_sessions = chatbot.sessions.prefetch_related('messages')[:5]

    staff_members = business.staff_members.all()
    total_staff = staff_members.filter(is_active=True).count()
    operators_count = staff_members.filter(role='operator', is_active=True).count()
    supervisors_count = staff_members.filter(role='supervisor', is_active=True).count()
    
    context = {
        'business': business,
        'completion': business.completion_percentage,
        'chatbot': chatbot,
        'chat_count': chat_count,
        'leads_count': leads_count,
        'new_leads_count': new_leads_count,
        'recent_sessions': recent_sessions,
        'total_staff': total_staff,
        'operators_count': operators_count,
        'supervisors_count': supervisors_count,
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

