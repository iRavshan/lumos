import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import ChatbotConfig, ChatSession, ChatMessage
from django.db.models import Q, Count
from .forms import ChatbotConfigForm
from .services import generate_rag_response, extract_contact_info


def cors_json_response(data, status=200):
    response = JsonResponse(data, status=status)
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With'
    return response


@csrf_exempt
def api_chatbot_config(request, api_key):
    if request.method == 'OPTIONS':
        return cors_json_response({})

    chatbot = get_object_or_404(ChatbotConfig, api_key=api_key)
    return cors_json_response({
        'status': 'success',
        'is_active': chatbot.is_active,
        'bot_name': chatbot.bot_name,
        'business_name': chatbot.business.name,
        'welcome_message': chatbot.welcome_message,
        'theme_color': chatbot.theme_color,
        'suggested_questions': chatbot.get_suggested_questions_list(),
    })


@csrf_exempt
def api_chat_message(request, api_key):
    if request.method == 'OPTIONS':
        return cors_json_response({})

    if request.method != 'POST':
        return cors_json_response({'error': 'Faqat POST so\'rov qabul qilinadi.'}, status=405)

    try:
        chatbot = ChatbotConfig.objects.select_related('business').get(api_key=api_key)
    except ChatbotConfig.DoesNotExist:
        return cors_json_response({'error': 'Bunday chatbot topilmadi.'}, status=404)

    if not chatbot.is_active:
        return cors_json_response({'error': 'Chatbot hozirda nofaol holatda.'}, status=403)

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        body = request.POST

    user_message = body.get('message', '').strip()
    session_id = body.get('session_id', '').strip()

    if not user_message:
        return cors_json_response({'error': 'Xabar matni bo\'sh bo\'lishi mumkin emas.'}, status=400)

    # Get client IP
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')

    # Get or create chat session
    session = None
    if session_id:
        session, created = ChatSession.objects.get_or_create(
            chatbot=chatbot,
            session_id=session_id,
            defaults={'visitor_ip': ip}
        )
        if not session.visitor_ip and ip:
            session.visitor_ip = ip

        # Automatically extract and update contact details if provided by visitor
        contacts = extract_contact_info(user_message)
        changed = False
        if contacts.get('phone') and not session.visitor_phone:
            session.visitor_phone = contacts['phone']
            changed = True
        if contacts.get('email') and not session.visitor_email:
            session.visitor_email = contacts['email']
            changed = True
        if contacts.get('name') and not session.visitor_name:
            session.visitor_name = contacts['name']
            changed = True

        if changed or not created:
            session.save()

    # Save user message
    ChatMessage.objects.create(
        chatbot=chatbot,
        session=session,
        role='user',
        content=user_message
    )

    # Generate RAG reply
    reply = generate_rag_response(chatbot, user_message)

    # Check if this chat requires human operator escalation
    from apps.team.services import check_if_needs_escalation, assign_session_to_operator
    needs_esc, reason = check_if_needs_escalation(user_message, reply)

    staff_assigned = None
    if session and (needs_esc or session.is_escalated):
        if not session.is_escalated:
            staff_assigned = assign_session_to_operator(session, reason)
            reply += f"\n\n👨‍💼 Savolingiz navbatchi mutaxassisimiz ({staff_assigned.name if staff_assigned else 'Operator'}) ga yo'naltirildi. Tez orada javob beriladi."

    # Save assistant message
    ChatMessage.objects.create(
        chatbot=chatbot,
        session=session,
        role='assistant',
        content=reply
    )

    return cors_json_response({
        'status': 'success',
        'reply': reply,
        'bot_name': chatbot.bot_name,
        'business_name': chatbot.business.name,
        'is_escalated': bool(session and session.is_escalated),
    })


@csrf_exempt
def api_poll_widget(request, api_key):
    """
    Allows widget to poll for any new messages (e.g. sent by Operator/Supervisor from Telegram Mini App).
    """
    if request.method == 'OPTIONS':
        return cors_json_response({})

    session_id = request.GET.get('session_id', '').strip()
    after_id = request.GET.get('after_id', '0')

    try:
        after_id = int(after_id)
    except ValueError:
        after_id = 0

    if not session_id:
        return cors_json_response({'messages': []})

    messages_qs = ChatMessage.objects.filter(
        chatbot__api_key=api_key,
        session__session_id=session_id,
        id__gt=after_id
    ).order_by('created_at')

    data = []
    for m in messages_qs:
        sender_name = m.sender_staff.name if m.sender_staff else (m.chatbot.bot_name if m.role == 'assistant' else 'Siz')
        data.append({
            'id': m.id,
            'role': m.role,
            'content': m.content,
            'sender': sender_name,
            'created_at': m.created_at.strftime("%H:%M")
        })

    return cors_json_response({
        'status': 'success',
        'messages': data
    })


from django.views.decorators.clickjacking import xframe_options_exempt


@xframe_options_exempt
def widget_iframe_view(request, api_key):
    chatbot = get_object_or_404(ChatbotConfig, api_key=api_key)
    return render(request, 'chatbot/widget_iframe.html', {
        'chatbot': chatbot,
        'suggested_questions': chatbot.get_suggested_questions_list()
    })


def demo_page_view(request, api_key):
    chatbot = get_object_or_404(ChatbotConfig, api_key=api_key)
    return render(request, 'chatbot/demo_page.html', {
        'chatbot': chatbot
    })


@login_required
def chatbot_settings_view(request):
    if not hasattr(request.user, 'business'):
        messages.warning(request, "Avval biznesingizni ro'yxatdan o'tkazing.")
        return redirect('businesses:onboarding')

    business = request.user.business
    chatbot, created = ChatbotConfig.objects.get_or_create(
        business=business,
        defaults={
            'bot_name': f"{business.name} AI",
            'welcome_message': f"Assalomu alaykum! «{business.name}» virtual yordamchisiman. Sizga qanday yordam bera olaman?"
        }
    )

    if request.method == 'POST':
        form = ChatbotConfigForm(request.POST, instance=chatbot)
        if form.is_valid():
            form.save()
            messages.success(request, "Chatbot sozlamalari muvaffaqiyatli saqlandi!")
            return redirect('businesses:dashboard')
    else:
        form = ChatbotConfigForm(instance=chatbot)

    return render(request, 'chatbot/settings.html', {
        'form': form,
        'chatbot': chatbot,
        'business': business
    })


@login_required
def inbox_view(request, session_id=None):
    if not hasattr(request.user, 'business'):
        return redirect('businesses:onboarding')

    business = request.user.business
    chatbot = getattr(business, 'chatbot_config', None)

    if not chatbot:
        chatbot, _ = ChatbotConfig.objects.get_or_create(
            business=business,
            defaults={'bot_name': f"{business.name} AI"}
        )

    # Base sessions queryset
    sessions_qs = chatbot.sessions.prefetch_related('messages').all()

    # Search filter
    q = request.GET.get('q', '').strip()
    if q:
        sessions_qs = sessions_qs.filter(
            Q(visitor_name__icontains=q) |
            Q(visitor_phone__icontains=q) |
            Q(visitor_email__icontains=q) |
            Q(session_id__icontains=q) |
            Q(messages__content__icontains=q)
        ).distinct()

    # Status filter
    status_filter = request.GET.get('status', 'all')
    if status_filter in ['new', 'in_progress', 'completed', 'archived']:
        sessions_qs = sessions_qs.filter(status=status_filter)

    # Counts
    all_sessions = chatbot.sessions.all()
    counts = {
        'all': all_sessions.count(),
        'new': all_sessions.filter(status='new').count(),
        'in_progress': all_sessions.filter(status='in_progress').count(),
        'completed': all_sessions.filter(status='completed').count(),
    }

    sessions_list = list(sessions_qs)

    # Active session selection
    active_session = None
    if session_id:
        active_session = chatbot.sessions.filter(session_id=session_id).prefetch_related('messages').first()
    elif sessions_list:
        active_session = sessions_list[0]

    return render(request, 'chatbot/inbox.html', {
        'business': business,
        'chatbot': chatbot,
        'sessions': sessions_list,
        'active_session': active_session,
        'counts': counts,
        'current_status': status_filter,
        'search_query': q,
    })


@login_required
def update_lead_view(request, session_id):
    if not hasattr(request.user, 'business'):
        return redirect('businesses:onboarding')

    business = request.user.business
    chatbot = getattr(business, 'chatbot_config', None)
    session = get_object_or_404(ChatSession, chatbot=chatbot, session_id=session_id)

    if request.method == 'POST':
        session.visitor_name = request.POST.get('visitor_name', '').strip()
        session.visitor_phone = request.POST.get('visitor_phone', '').strip()
        session.visitor_email = request.POST.get('visitor_email', '').strip()
        session.status = request.POST.get('status', session.status)
        session.notes = request.POST.get('notes', '').strip()
        session.save()
        messages.success(request, f"«{session.display_name}» ma'lumotlari muvaffaqiyatli yangilandi.")

    return redirect('chatbot:inbox_detail', session_id=session_id)


@login_required
def chatbot_history_view(request):
    # Redirect legacy history link directly to the new powerful inbox view
    return redirect('chatbot:inbox')

