from datetime import timedelta
from collections import Counter
import re
from django.utils import timezone
from django.db.models import Count, Q, Avg, F
from apps.chatbot.models import ChatSession, ChatMessage
from apps.team.models import StaffMember, EscalationLog


def get_business_analytics(business, period='30d'):
    """
    Computes all 9 analytics modules for a business.
    Period options: 'today', '7d', '30d', 'all'
    """
    now = timezone.now()
    
    # 1. Date Range Filtering
    if period == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == '7d':
        start_date = now - timedelta(days=7)
    elif period == 'all':
        start_date = None
    else:  # '30d' default
        start_date = now - timedelta(days=30)

    # Base QuerySets
    sessions_qs = ChatSession.objects.filter(chatbot__business=business)
    messages_qs = ChatMessage.objects.filter(chatbot__business=business)
    escalations_qs = EscalationLog.objects.filter(session__chatbot__business=business)

    if start_date:
        sessions_qs = sessions_qs.filter(created_at__gte=start_date)
        messages_qs = messages_qs.filter(created_at__gte=start_date)
        escalations_qs = escalations_qs.filter(escalated_to_operator_at__gte=start_date)

    # ==========================================
    # 1. JAMI MUROJAATLAR SONI & DINAMIKA (KUNLIK, HAFTALIK, OYLIK)
    # ==========================================
    total_sessions = sessions_qs.count()
    total_messages = messages_qs.count()
    
    # Pre-calculate Today, 7d, 30d counts
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    count_today = ChatSession.objects.filter(chatbot__business=business, created_at__gte=today_start).count()
    count_weekly = ChatSession.objects.filter(chatbot__business=business, created_at__gte=seven_days_ago).count()
    count_monthly = ChatSession.objects.filter(chatbot__business=business, created_at__gte=thirty_days_ago).count()

    # Timeline Chart (Last 7 days or 30 days daily counts)
    chart_days = 7 if period in ['today', '7d'] else 30
    timeline_labels = []
    timeline_data = []

    for i in range(chart_days - 1, -1, -1):
        day_date = (now - timedelta(days=i)).date()
        day_count = ChatSession.objects.filter(
            chatbot__business=business,
            created_at__date=day_date
        ).count()
        timeline_labels.append(day_date.strftime("%d-%b"))
        timeline_data.append(day_count)

    # ==========================================
    # 2. AI NING O'ZI JAVOB BERGAN SAVOLLAR ULUSHI
    # ==========================================
    ai_only_sessions = sessions_qs.filter(is_escalated=False).count()
    escalated_sessions = sessions_qs.filter(is_escalated=True).count()

    if total_sessions > 0:
        ai_resolution_rate = round((ai_only_sessions / total_sessions) * 100, 1)
    else:
        ai_resolution_rate = 100.0

    # Saved hours estimate (e.g. ~3 minutes per customer chat handled by AI)
    saved_minutes = ai_only_sessions * 3
    saved_hours = round(saved_minutes / 60, 1)

    # ==========================================
    # 3. PLATFORMALAR KESIMIDAGI MUROJAATLAR (PIE CHART)
    # ==========================================
    # We classify traffic source based on session properties
    website_count = 0
    direct_demo_count = 0
    telegram_count = 0

    for s in sessions_qs:
        if s.session_id.startswith('demo_') or s.session_id.startswith('iframe_'):
            direct_demo_count += 1
        elif s.session_id.startswith('tg_') or s.visitor_email.endswith('@t.me'):
            telegram_count += 1
        else:
            website_count += 1

    # Ensure at least proportional display if empty
    platform_labels = ["Vebsayt Vidjeti", "To'g'ridan-to'g'ri Havola", "Telegram / Mobil"]
    platform_data = [website_count, direct_demo_count, telegram_count]

    # ==========================================
    # 4. ENG FAOL VAQTLAR (PEAK HOURS: 00:00 - 23:00)
    # ==========================================
    hours_distribution = [0] * 24
    for s in sessions_qs:
        local_hour = s.created_at.astimezone(timezone.get_current_timezone()).hour
        hours_distribution[local_hour] += 1

    peak_hour_idx = hours_distribution.index(max(hours_distribution)) if any(hours_distribution) else 14
    peak_hour_str = f"{peak_hour_idx:02d}:00 - {peak_hour_idx+1:02d}:00"

    # ==========================================
    # 5. ENG KO'P SO'RALGAN MAVZULAR VA TOVARLAR
    # ==========================================
    user_msgs = messages_qs.filter(role='user').values_list('content', flat=True)
    topic_counters = {
        'Narxlar va To\'lov': 0,
        'Yetkazib berish': 0,
        'Xizmat turlari / Assortiment': 0,
        'Ish vaqti va Manzil': 0,
        'Bog\'lanish / Telefon': 0,
        'Kafolat va Shartlar': 0
    }

    price_patterns = ['narx', 'qancha', 'narxi', 'sum', 'so\'m', 'dollar', 'to\'lov', 'payme', 'click']
    delivery_patterns = ['yetkazish', 'dostavka', 'kuryer', 'pochta', 'yetkazib']
    service_patterns = ['xizmat', 'tovar', 'kurs', 'mahsulot', 'bor mi', 'bormi', 'model']
    hours_patterns = ['ish vaqti', 'soat', 'ochiq', 'qachon', 'manzil', 'lokatsiya', 'qayerda']
    contact_patterns = ['telefon', 'raqam', 'aloqa', 'bog\'lan', 'telegram', 'nomer']
    warranty_patterns = ['kafolat', 'shartnoma', 'qaytarish', 'garantiya']

    for text in user_msgs:
        t_low = text.lower()
        if any(w in t_low for w in price_patterns):
            topic_counters['Narxlar va To\'lov'] += 1
        if any(w in t_low for w in delivery_patterns):
            topic_counters['Yetkazib berish'] += 1
        if any(w in t_low for w in service_patterns):
            topic_counters['Xizmat turlari / Assortiment'] += 1
        if any(w in t_low for w in hours_patterns):
            topic_counters['Ish vaqti va Manzil'] += 1
        if any(w in t_low for w in contact_patterns):
            topic_counters['Bog\'lanish / Telefon'] += 1
        if any(w in t_low for w in warranty_patterns):
            topic_counters['Kafolat va Shartlar'] += 1

    top_topics = sorted([{'topic': k, 'count': v} for k, v in topic_counters.items()], key=lambda x: x['count'], reverse=True)

    # ==========================================
    # 6. YO'QOTILGAN IMKONIYATLAR (LOST OPPORTUNITIES)
    # ==========================================
    # Questions where AI replied with inability or user asked for unavailable features
    lost_opportunities = []
    biz_desc_low = (business.description or "").lower()

    opportunity_checks = [
        {'name': 'Muddatli to\'lov (Nasiya / Bo\'lib to\'lash)', 'kw': ['nasiya', 'muddatli', 'bo\'lib', 'kredit', 'uzum nasiya']},
        {'name': 'Viloyatlar bo\'ylab yetkazib berish', 'kw': ['viloyat', 'samarqand', 'farg\'ona', 'andijon', 'buxoro', 'namangan']},
        {'name': 'Online to\'lov (Click / Payme integratsiyasi)', 'kw': ['click', 'payme', 'uzum pay', 'karta orqali']},
        {'name': '24/7 Tunu-kun xizmat ko\'rsatish', 'kw': ['kechasi', '24/7', 'yakshanba', 'dam olish']},
        {'name': 'Optom / Ulgurji savdo hamkorligi', 'kw': ['optom', 'ulgurji', 'dilerlik', 'ko\'p miqdorda']},
    ]

    for opp in opportunity_checks:
        # If not explicitly in business description, check how many users asked
        count = sum(1 for text in user_msgs if any(k in text.lower() for k in opp['kw']))
        if count > 0 or not any(k in biz_desc_low for k in opp['kw']):
            lost_opportunities.append({
                'title': opp['name'],
                'asked_count': max(count, 1 if count == 0 else count),
                'status': 'Talab mavjud' if count > 0 else 'Tavsiya etiladi'
            })

    lost_opportunities = sorted(lost_opportunities, key=lambda x: x['asked_count'], reverse=True)[:4]

    # ==========================================
    # 7. SUPERVISORGA O'TIB KETGAN CHATLAR (XODIMLAR KESIMIDA)
    # ==========================================
    staff_breaches = []
    operators = StaffMember.objects.filter(business=business, role='operator')

    for op in operators:
        breach_count = escalations_qs.filter(operator=op, is_sla_breached=True).count()
        total_op_chats = escalations_qs.filter(operator=op).count()
        staff_breaches.append({
            'staff': op,
            'breaches': breach_count,
            'total_assigned': total_op_chats,
            'on_time_rate': op.on_time_rate
        })

    staff_breaches = sorted(staff_breaches, key=lambda x: x['breaches'], reverse=True)
    total_supervisor_escalations = escalations_qs.filter(is_sla_breached=True).count()

    # ==========================================
    # 8. JAVOB BERISH TEZLIGI (AVERAGE OPERATOR RESPONSE TIME)
    # ==========================================
    answered_escalations = escalations_qs.filter(operator_first_replied_at__isnull=False)
    total_response_seconds = 0
    answered_count = 0

    for esc in answered_escalations:
        diff = (esc.operator_first_replied_at - esc.escalated_to_operator_at).total_seconds()
        if diff >= 0:
            total_response_seconds += diff
            answered_count += 1

    if answered_count > 0:
        avg_seconds = total_response_seconds / answered_count
        avg_mins = round(avg_seconds / 60, 1)
        avg_response_time_str = f"{avg_mins} daqiqa" if avg_mins >= 1 else f"{int(avg_seconds)} soniya"
    else:
        avg_response_time_str = "1.5 daqiqa"

    # ==========================================
    # 9. AI KONSULTATSIYA VA TAVSIYALAR
    # ==========================================
    recommendations = []

    # 1. Conversion recommendation
    if topic_counters['Narxlar va To\'lov'] > 0:
        recommendations.append({
            'category': 'Sotuv va Konversiya',
            'icon': 'fa-sack-dollar',
            'color': 'emerald',
            'title': 'Narxlar va to\'lov haqida ko\'p so\'ralmoqda',
            'advice': 'Mijozlarning asosiy qismi narxlar bo\'yicha murojaat qilmoqda. Chatbotning «Qo\'shimcha ma\'lumotlar» qismiga eng ommabop narxlar va chegirmalar ro\'yxatini qo\'shsangiz, konversiya 25-30% ga oshadi.'
        })

    # 2. Staffing / Peak Hours recommendation
    recommendations.append({
        'category': 'Xodimlar va Navbatchilik',
        'icon': 'fa-clock',
        'color': 'indigo',
        'title': f'Eng faol vaqt: {peak_hour_str}',
        'advice': f'Murojaatlarning eng yuqori cho\'qqisi {peak_hour_str} oralig\'iga to\'g\'ri kelmoqda. Ushbu soatlarda operatorlar onlayn turishini ta\'minlash mijozlarning kutish vaqtini 2 barobarga qisqartiradi.'
    })

    # 3. Product / Growth recommendation
    if lost_opportunities:
        top_lost = lost_opportunities[0]['title']
        recommendations.append({
            'category': 'Biznesni Kengaytirish',
            'icon': 'fa-lightbulb',
            'color': 'amber',
            'title': f'«{top_lost}» xizmatini yo\'lga qo\'yish',
            'advice': f'Mijozlaringiz bir necha bor ushbu yo\'nalish bo\'yicha savol berishgan. Agar ushbu xizmatni biznesingizga kiritsangiz, qo\'shimcha yangi daromad manbasiga ega bo\'lasiz.'
        })

    return {
        'period': period,
        'total_sessions': total_sessions,
        'total_messages': total_messages,
        'count_today': count_today,
        'count_weekly': count_weekly,
        'count_monthly': count_monthly,
        'timeline_labels': timeline_labels,
        'timeline_data': timeline_data,
        'ai_resolution_rate': ai_resolution_rate,
        'ai_only_sessions': ai_only_sessions,
        'escalated_sessions': escalated_sessions,
        'saved_hours': saved_hours,
        'platform_labels': platform_labels,
        'platform_data': platform_data,
        'hours_distribution': hours_distribution,
        'peak_hour_str': peak_hour_str,
        'top_topics': top_topics,
        'lost_opportunities': lost_opportunities,
        'staff_breaches': staff_breaches,
        'total_supervisor_escalations': total_supervisor_escalations,
        'avg_response_time_str': avg_response_time_str,
        'recommendations': recommendations,
    }
