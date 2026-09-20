from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q
from .models import StaffMember, EscalationLog


def check_if_needs_escalation(user_message, ai_reply=""):
    """
    Determines if a customer conversation needs human operator intervention.
    """
    msg = user_message.lower().strip()
    
    # Direct operator request triggers
    operator_triggers = [
        'operator', 'operatir', 'odam', 'inson', 'menejer', 'manager', 
        'xodim', 'tirik odam', 'mutaxassis', 'raxbar', 'rahbar',
        'operatorga ula', 'operator bilan', 'bog\'lang', 'boglang', 'admin'
    ]
    if any(t in msg for t in operator_triggers):
        return True, "Mijoz inson operatori bilan bog'lanishni so'radi."

    # If AI reply contains inability to resolve
    if ai_reply and any(phrase in ai_reply for phrase in ['aniq ma\'lumot topilmadi', 'ma\'muriyat bilan bog\'lanishingiz', 'afsuski, topilmadi']):
        return True, "AI ma'lumotlar bazasidan aniq yechim topa olmadi."

    return False, ""


def assign_session_to_operator(session, reason="AI yechim topa olmadi"):
    """
    Assigns a chat session to the most available online operator.
    """
    business = session.chatbot.business

    # 1. Find active operators for this business (least busy first)
    operators = StaffMember.objects.filter(
        business=business,
        role='operator',
        is_active=True
    ).annotate(
        active_chats=Count('assigned_sessions', filter=Q(assigned_sessions__escalation_status__in=['waiting_operator', 'operator_active']))
    ).order_by('active_chats', 'created_at')

    assigned_operator = operators.first()

    # 3. If still no operator, assign directly to supervisor
    assigned_supervisor = None
    if not assigned_operator:
        assigned_supervisor = StaffMember.objects.filter(
            business=business,
            role='supervisor',
            is_active=True
        ).first()

    now = timezone.now()
    sla_mins = assigned_operator.sla_minutes if assigned_operator else 5
    deadline = now + timedelta(minutes=sla_mins)

    session.is_escalated = True
    session.escalated_at = now
    session.sla_deadline = deadline

    if assigned_operator:
        session.assigned_staff = assigned_operator
        session.escalation_status = 'waiting_operator'
    elif assigned_supervisor:
        session.assigned_staff = assigned_supervisor
        session.escalation_status = 'escalated_supervisor'
    else:
        session.escalation_status = 'waiting_operator'

    session.save()

    # Log escalation
    EscalationLog.objects.create(
        session=session,
        operator=assigned_operator,
        supervisor=assigned_supervisor,
        escalation_reason=reason,
        escalated_to_operator_at=now
    )

    return session.assigned_staff


def check_and_escalate_overdue_chats(business=None):
    """
    Scans for overdue chats where operator exceeded SLA deadline and escalates them to supervisor.
    """
    now = timezone.now()
    overdue_query = Q(
        escalation_status='waiting_operator',
        sla_deadline__lt=now,
        is_escalated=True
    )
    if business:
        overdue_query &= Q(chatbot__business=business)

    from apps.chatbot.models import ChatSession
    overdue_sessions = ChatSession.objects.filter(overdue_query)

    escalated_count = 0
    for session in overdue_sessions:
        biz = session.chatbot.business
        # Find active supervisor for this business
        supervisor = StaffMember.objects.filter(
            business=biz,
            role='supervisor',
            is_active=True
        ).first()

        # Update session
        session.escalation_status = 'escalated_supervisor'
        if supervisor:
            session.assigned_staff = supervisor
        session.save()

        # Update escalation log
        log = session.escalation_logs.order_by('-escalated_to_operator_at').first()
        if log:
            log.is_sla_breached = True
            log.escalated_to_supervisor_at = now
            if supervisor:
                log.supervisor = supervisor
            log.save()

        escalated_count += 1

    return escalated_count
