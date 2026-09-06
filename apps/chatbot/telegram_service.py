import json
import urllib.request
import urllib.parse
from django.utils import timezone
from .models import ChatbotConfig, ChatSession, ChatMessage
from .services import generate_rag_response, extract_contact_info


def make_telegram_request(token, method, payload=None):
    """
    Utility to make HTTP requests to the official Telegram Bot API.
    """
    if not token:
        return {'ok': False, 'description': 'Token mavjud emas'}
    
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        if payload:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                url, 
                data=data, 
                headers={'Content-Type': 'application/json'}
            )
        else:
            req = urllib.request.Request(url)
            
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode('utf-8')
            return json.loads(res_body)
    except Exception as e:
        return {'ok': False, 'description': str(e)}


def verify_telegram_bot_token(token):
    """
    Verifies bot token by calling getMe API.
    Returns (is_valid, bot_info_dict, error_msg).
    """
    cleaned_token = (token or '').strip()
    if not cleaned_token:
        return False, {}, "Token kiritilmadi."
    
    res = make_telegram_request(cleaned_token, 'getMe')
    if res.get('ok') and 'result' in res:
        bot_data = res['result']
        return True, {
            'id': bot_data.get('id'),
            'first_name': bot_data.get('first_name', ''),
            'username': bot_data.get('username', ''),
            'can_join_groups': bot_data.get('can_join_groups', False),
        }, ""
    else:
        err = res.get('description', "Noto'g'ri yoki yaroqsiz Telegram Bot Token.")
        return False, {}, err


def set_telegram_webhook(token, webhook_url):
    """
    Registers the webhook URL with Telegram.
    """
    payload = {
        'url': webhook_url,
        'drop_pending_updates': True,
        'allowed_updates': ['message', 'callback_query']
    }
    return make_telegram_request(token, 'setWebhook', payload)


def delete_telegram_webhook(token):
    """
    Deletes the webhook from Telegram.
    """
    return make_telegram_request(token, 'deleteWebhook', {'drop_pending_updates': True})


def send_telegram_bot_message(token, chat_id, text, reply_markup=None):
    """
    Sends a message to a Telegram chat using HTML or Markdown formatting.
    """
    if not token or not chat_id or not text:
        return {'ok': False}
    
    payload = {
        'chat_id': chat_id,
        'text': text,
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
        
    return make_telegram_request(token, 'sendMessage', payload)


def handle_telegram_update(api_key, update_data):
    """
    Processes an incoming update from Telegram webhook.
    """
    try:
        config = ChatbotConfig.objects.select_related('business').get(api_key=api_key, is_active=True)
    except ChatbotConfig.DoesNotExist:
        return {'ok': False, 'error': 'Chatbot topilmadi'}

    if not config.telegram_bot_active or not config.telegram_bot_token:
        return {'ok': False, 'error': 'Telegram bot faol emas'}

    # Process message update
    message = update_data.get('message') or update_data.get('edited_message')
    if not message:
        return {'ok': True, 'note': 'No message in update'}

    chat = message.get('chat', {})
    chat_id = chat.get('id')
    from_user = message.get('from', {})
    user_first_name = from_user.get('first_name', '')
    user_last_name = from_user.get('last_name', '')
    user_username = from_user.get('username', '')
    full_name = f"{user_first_name} {user_last_name}".strip() or (f"@{user_username}" if user_username else "Telegram Foydalanuvchisi")

    text = message.get('text', '').strip()
    contact = message.get('contact')

    if not chat_id:
        return {'ok': True}

    # Find or create ChatSession
    session_id = f"tg_{chat_id}"
    session, created = ChatSession.objects.get_or_create(
        chatbot=config,
        session_id=session_id,
        defaults={
            'visitor_name': full_name,
            'visitor_email': f"@{user_username}" if user_username else f"{chat_id}@t.me",
            'status': 'new',
        }
    )

    # Handle Contact sharing
    if contact:
        phone = contact.get('phone_number')
        if phone:
            session.visitor_phone = phone
            session.save(update_fields=['visitor_phone'])
            send_telegram_bot_message(
                config.telegram_bot_token,
                chat_id,
                f"Rahmat, {full_name}! Telefon raqamingiz ({phone}) qabul qilindi. Sizga qanday yordam bera olaman?"
            )
            return {'ok': True}

    if not text:
        return {'ok': True}

    # Handle /start or /help command
    if text.startswith('/start'):
        welcome_txt = config.welcome_message or f"Assalomu alaykum! «{config.business.name}» virtual yordamchisiman. Sizga qanday yordam bera olaman?"
        
        # Build quick questions keyboard if available
        questions = config.get_suggested_questions_list()
        reply_markup = None
        if questions:
            keyboard = [[{'text': q}] for q in questions[:4]]
            reply_markup = {
                'keyboard': keyboard,
                'resize_keyboard': True,
                'one_time_keyboard': False
            }

        send_telegram_bot_message(
            config.telegram_bot_token,
            chat_id,
            welcome_txt,
            reply_markup=reply_markup
        )
        return {'ok': True}

    # 1. Save user's incoming message
    user_msg = ChatMessage.objects.create(
        chatbot=config,
        session=session,
        role='user',
        content=text
    )

    # 2. Extract contact info if mentioned in text
    extracted = extract_contact_info(text)
    needs_save = False
    if extracted.get('phone') and not session.visitor_phone:
        session.visitor_phone = extracted['phone']
        needs_save = True
    if extracted.get('name') and (session.visitor_name == "Telegram Foydalanuvchisi" or not session.visitor_name):
        session.visitor_name = extracted['name']
        needs_save = True
    if needs_save:
        session.save()

    # 3. Check for escalation request (Human Operator)
    from apps.team.services import check_if_needs_escalation, assign_session_to_operator
    needs_escalation, esc_reason = check_if_needs_escalation(text)
    
    if needs_escalation and not session.is_escalated:
        assigned_staff = assign_session_to_operator(session, esc_reason)
        if assigned_staff:
            esc_reply = f"Hurmatli {full_name}, sizning murojaatingiz navbatchi mutaxassisimiz {assigned_staff.name}ga biriktirildi. Tez orada sizga shu yerda javob beradilar."
        else:
            esc_reply = "Murojaatingiz qabul qilindi. Operatorlarimiz tez orada siz bilan bog'lanishadi."

        # Save assistant message
        ChatMessage.objects.create(
            chatbot=config,
            session=session,
            role='assistant',
            content=esc_reply
        )
        send_telegram_bot_message(config.telegram_bot_token, chat_id, esc_reply)
        return {'ok': True}

    # 4. If session is already assigned to an operator and waiting for reply
    if session.is_escalated and session.escalation_status in ['waiting_operator', 'operator_active', 'escalated_supervisor']:
        # The operator will reply from their TMA, but send acknowledgement if needed
        return {'ok': True}

    # 5. Generate AI RAG Response
    ai_reply = generate_rag_response(config, text, session)

    # Check if AI couldn't answer -> escalate
    needs_esc_ai, _ = check_if_needs_escalation(text, ai_reply)
    if needs_esc_ai and not session.is_escalated:
        assigned_staff = assign_session_to_operator(session, "AI to'liq javob bera olmadi")
        if assigned_staff:
            ai_reply += f"\n\n👨‍💼 Savolingiz bo'yicha mutaxassisimiz ({assigned_staff.name}) ulanmoqda..."

    # Save and send AI response
    ChatMessage.objects.create(
        chatbot=config,
        session=session,
        role='assistant',
        content=ai_reply
    )

    # Human-like delay in Telegram
    if config.response_delay_enabled:
        import time
        user_msgs = session.messages.filter(role='user').count()
        delay = config.first_message_delay_seconds if user_msgs <= 1 else config.subsequent_message_delay_seconds
        if delay > 0:
            time.sleep(min(delay, 15))

    # Split messages if enabled
    if config.split_messages and '\n\n' in ai_reply:
        parts = [p.strip() for p in ai_reply.split('\n\n') if p.strip()]
        if len(parts) > 1:
            for p in parts:
                send_telegram_bot_message(config.telegram_bot_token, chat_id, p)
            return {'ok': True}

    send_telegram_bot_message(config.telegram_bot_token, chat_id, ai_reply)
    return {'ok': True}
