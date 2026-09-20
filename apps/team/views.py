import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q, Avg
from .models import StaffMember, EscalationLog
from .forms import StaffMemberForm
from .services import check_and_escalate_overdue_chats
from apps.chatbot.models import ChatSession, ChatMessage


# ==========================================
# WEB DASHBOARD VIEWS (FOR BUSINESS OWNER)
# ==========================================

@login_required
def team_list_view(request):
    if not hasattr(request.user, 'business'):
        return redirect('businesses:onboarding')

    business = request.user.business
    # Run SLA overdue check
    check_and_escalate_overdue_chats(business)

    staff_members = business.staff_members.all()
    operators = staff_members.filter(role='operator')
    supervisors = staff_members.filter(role='supervisor')

    return render(request, 'team/team_list.html', {
        'business': business,
        'operators': operators,
        'supervisors': supervisors,
        'total_staff': staff_members.count(),
        'form': StaffMemberForm(),
    })


@login_required
def team_create_view(request):
    if not hasattr(request.user, 'business'):
        return redirect('businesses:onboarding')

    business = request.user.business

    if request.method == 'POST':
        form = StaffMemberForm(request.POST)
        if form.is_valid():
            staff = form.save(commit=False)
            staff.business = business
            staff.save()
            messages.success(request, f"«{staff.name}» muvaffaqiyatli qo'shildi. TMA havolasi shakllantirildi.")
        else:
            err_msgs = []
            for field, errs in form.errors.items():
                err_msgs.append(f"{', '.join(errs)}")
            messages.error(request, "Xodim qo'shishda xatolik: " + "; ".join(err_msgs))
        return redirect('team:team_list')

    # GET requests redirect to team_list since modal is used instead of a separate page
    return redirect('team:team_list')


@login_required
def team_edit_view(request, staff_id):
    if not hasattr(request.user, 'business'):
        return redirect('businesses:onboarding')

    business = request.user.business
    staff = get_object_or_404(StaffMember, id=staff_id, business=business)

    if request.method == 'POST':
        form = StaffMemberForm(request.POST, instance=staff)
        if form.is_valid():
            form.save()
            messages.success(request, f"«{staff.name}» ma'lumotlari muvaffaqiyatli yangilandi.")
        else:
            err_msgs = []
            for field, errs in form.errors.items():
                err_msgs.append(f"{', '.join(errs)}")
            messages.error(request, "Tahrirlashda xatolik: " + "; ".join(err_msgs))
        return redirect('team:team_list')

    # GET requests redirect to team_list since edit is handled via modal
    return redirect('team:team_list')


@login_required
def team_delete_view(request, staff_id):
    if not hasattr(request.user, 'business'):
        return redirect('businesses:onboarding')

    business = request.user.business
    staff = get_object_or_404(StaffMember, id=staff_id, business=business)
    staff_name = staff.name
    staff.delete()
    messages.info(request, f"«{staff_name}» tizimdan o'chirildi.")
    return redirect('team:team_list')



@login_required
def team_analytics_view(request):
    if not hasattr(request.user, 'business'):
        return redirect('businesses:onboarding')

    business = request.user.business
    check_and_escalate_overdue_chats(business)

    operators = business.staff_members.filter(role='operator')
    escalations = EscalationLog.objects.filter(session__chatbot__business=business)
    
    total_escalated = escalations.count()
    total_breached = escalations.filter(is_sla_breached=True).count()
    resolved_by_supervisor = escalations.filter(resolved_by='supervisor').count()

    return render(request, 'team/analytics.html', {
        'business': business,
        'operators': operators,
        'escalations': escalations[:30],
        'total_escalated': total_escalated,
        'total_breached': total_breached,
        'resolved_by_supervisor': resolved_by_supervisor,
    })


# ==========================================
# TELEGRAM MINI APP (TMA) VIEWS & APIs
# ==========================================

def tma_operator_view(request, token):
    staff = get_object_or_404(StaffMember, auth_token=token, role='operator')
    check_and_escalate_overdue_chats(staff.business)

    active_sessions = staff.assigned_sessions.filter(
        escalation_status__in=['waiting_operator', 'operator_active']
    ).prefetch_related('messages')

    resolved_sessions = staff.assigned_sessions.filter(
        escalation_status='resolved'
    ).order_by('-updated_at')[:10]

    return render(request, 'team/tma_operator.html', {
        'staff': staff,
        'active_sessions': active_sessions,
        'resolved_sessions': resolved_sessions,
    })


def tma_supervisor_view(request, token):
    supervisor = get_object_or_404(StaffMember, auth_token=token, role='supervisor')
    check_and_escalate_overdue_chats(supervisor.business)

    business = supervisor.business
    
    # Overdue/Escalated chats
    escalated_sessions = ChatSession.objects.filter(
        chatbot__business=business,
        escalation_status='escalated_supervisor'
    ).prefetch_related('messages')

    # All ongoing chats
    all_ongoing = ChatSession.objects.filter(
        chatbot__business=business,
        escalation_status__in=['waiting_operator', 'operator_active', 'escalated_supervisor']
    ).prefetch_related('messages')

    operators = business.staff_members.filter(role='operator')

    return render(request, 'team/tma_supervisor.html', {
        'supervisor': supervisor,
        'business': business,
        'escalated_sessions': escalated_sessions,
        'all_ongoing': all_ongoing,
        'operators': operators,
    })


@csrf_exempt
def tma_toggle_status_api(request, token):
    staff = get_object_or_404(StaffMember, auth_token=token)
    staff.is_online = not staff.is_online
    staff.save()
    return JsonResponse({'status': 'success', 'is_online': staff.is_online})


@csrf_exempt
def tma_send_reply_api(request, token, session_id):
    staff = get_object_or_404(StaffMember, auth_token=token)
    session = get_object_or_404(ChatSession, session_id=session_id, chatbot__business=staff.business)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    text = data.get('message', '').strip()
    if not text:
        return JsonResponse({'error': 'Xabar bo\'sh bo\'lishi mumkin emas'}, status=400)

    # Create message from staff
    msg = ChatMessage.objects.create(
        chatbot=session.chatbot,
        session=session,
        sender_staff=staff,
        role='staff',
        content=text
    )

    try:
        from apps.chatbot.realtime import notify_chat_update
        notify_chat_update(session.chatbot.business_id, session.session_id, msg.id)
    except Exception:
        pass

    now = timezone.now()
    if session.escalation_status == 'waiting_operator':
        session.escalation_status = 'operator_active'
        # Log first reply
        log = session.escalation_logs.filter(operator=staff, operator_first_replied_at__isnull=True).first()
        if log:
            log.operator_first_replied_at = now
            log.save()

    session.save()

    # If this session came from Telegram, forward operator reply to Telegram chat
    if session.session_id.startswith('tg_') and session.chatbot.telegram_bot_token:
        try:
            tg_chat_id = session.session_id.replace('tg_', '')
            from apps.chatbot.telegram_service import send_telegram_bot_message, sanitize_for_telegram
            clean_text = sanitize_for_telegram(text)
            send_telegram_bot_message(
                session.chatbot.telegram_bot_token,
                tg_chat_id,
                clean_text,
                parse_mode='HTML'
            )
        except Exception:
            pass

    return JsonResponse({
        'status': 'success',
        'message_id': msg.id,
        'content': msg.content,
        'created_at': msg.created_at.strftime("%H:%M")
    })


@csrf_exempt
def tma_resolve_chat_api(request, token, session_id):
    staff = get_object_or_404(StaffMember, auth_token=token)
    session = get_object_or_404(ChatSession, session_id=session_id, chatbot__business=staff.business)

    session.escalation_status = 'resolved'
    session.status = 'completed'
    session.save()

    # Update log
    log = session.escalation_logs.order_by('-escalated_to_operator_at').first()
    if log:
        log.resolved_at = timezone.now()
        log.resolved_by = staff.role
        log.save()

    return JsonResponse({'status': 'success'})


def tma_poll_messages_api(request, token, session_id):
    staff = get_object_or_404(StaffMember, auth_token=token)
    session = get_object_or_404(ChatSession, session_id=session_id, chatbot__business=staff.business)

    messages_data = []
    for m in session.messages.all():
        messages_data.append({
            'id': m.id,
            'role': m.role,
            'content': m.content,
            'sender': staff.name if m.role == 'staff' else ('Mijoz' if m.role == 'user' else 'AI'),
            'created_at': m.created_at.strftime("%H:%M")
        })

    return JsonResponse({
        'status': 'success',
        'escalation_status': session.escalation_status,
        'messages': messages_data
    })
