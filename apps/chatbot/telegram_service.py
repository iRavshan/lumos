import json
import random
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
        'drop_pending_updates': False,
        'allowed_updates': ['message', 'callback_query']
    }
    return make_telegram_request(token, 'setWebhook', payload)


def delete_telegram_webhook(token):
    """
    Deletes the webhook from Telegram.
    """
    return make_telegram_request(token, 'deleteWebhook', {'drop_pending_updates': False})


def send_telegram_chat_action(token, chat_id, action='typing'):
    """
    Sends chat action (e.g. typing) to Telegram to show bot activity.
    """
    if not token or not chat_id:
        return {'ok': False}
    return make_telegram_request(token, 'sendChatAction', {'chat_id': chat_id, 'action': action})


from html.parser import HTMLParser
import html
import re


class TelegramHTMLSanitizer(HTMLParser):
    ALLOWED_TAGS = {
        'b': 'b',
        'strong': 'b',
        'i': 'i',
        'em': 'i',
        'u': 'u',
        'ins': 'u',
        's': 's',
        'strike': 's',
        'del': 's',
        'code': 'code',
        'pre': 'pre',
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []
        self.tag_stack = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        if tag_lower in ('script', 'style'):
            self.skip_depth += 1
            return

        if self.skip_depth > 0:
            return

        if tag_lower in ('div', 'p', 'br'):
            self.output.append('\n')
            return

        if tag_lower in self.ALLOWED_TAGS:
            out_tag = self.ALLOWED_TAGS[tag_lower]
            self.output.append(f"<{out_tag}>")
            self.tag_stack.append(out_tag)
        elif tag_lower == 'span':
            attrs_dict = dict(attrs)
            style = attrs_dict.get('style', '').lower()
            if 'font-weight: bold' in style or 'font-weight:bold' in style or 'font-weight: 700' in style:
                self.output.append('<b>')
                self.tag_stack.append('b')
            elif 'font-style: italic' in style or 'font-style:italic' in style:
                self.output.append('<i>')
                self.tag_stack.append('i')
            elif 'text-decoration: underline' in style or 'text-decoration:underline' in style:
                self.output.append('<u>')
                self.tag_stack.append('u')
            elif 'text-decoration: line-through' in style or 'text-decoration:line-through' in style:
                self.output.append('<s>')
                self.tag_stack.append('s')
            else:
                self.tag_stack.append(None)
        elif tag_lower == 'a':
            attrs_dict = dict(attrs)
            href = attrs_dict.get('href', '')
            if href.startswith('http://') or href.startswith('https://'):
                clean_href = html.escape(href, quote=True)
                self.output.append(f'<a href="{clean_href}">')
                self.tag_stack.append('a')
            else:
                self.tag_stack.append(None)
        else:
            self.tag_stack.append(None)

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in ('script', 'style'):
            if self.skip_depth > 0:
                self.skip_depth -= 1
            return

        if self.skip_depth > 0:
            return

        if tag_lower in ('div', 'p'):
            self.output.append('\n')
            return

        if self.tag_stack:
            expected = self.tag_stack.pop()
            if expected:
                self.output.append(f"</{expected}>")

    def handle_data(self, data):
        if self.skip_depth > 0:
            return
        escaped = html.escape(data, quote=False)
        self.output.append(escaped)

    def get_result(self):
        while self.tag_stack:
            expected = self.tag_stack.pop()
            if expected:
                self.output.append(f"</{expected}>")
        text = "".join(self.output)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


def format_text_for_telegram(text):
    """
    Converts Markdown formatting (such as `* **Title:** text`) into Telegram-friendly HTML:
    - Replaces bullet asterisks/dashes (*, -, +) with clean bullet dots (•)
    - Replaces Markdown headers (### Header) with bold headers (<b>Header</b>)
    - Converts **bold** to <b>bold</b>
    - Converts *italic* / _italic_ to <i>italic</i>
    - Converts [text](url) to <a href="url">text</a>
    - Converts `code` to <code>code</code> and ```blocks``` to <pre><code>...</code></pre>
    - Ensures valid Telegram HTML with properly escaped entities.
    """
    if not text:
        return ""

    s = str(text).strip()

    # 1. Protect code blocks ```...``` and `...`
    code_blocks = []
    def save_code_block(m):
        code_content = m.group(1).strip()
        code_blocks.append(f"<pre><code>{html.escape(code_content)}</code></pre>")
        return f"@@@CODE_BLOCK_{len(code_blocks)-1}@@@"

    s = re.sub(r'```(?:[a-zA-Z0-9_\-\+]+)?\n?(.*?)```', save_code_block, s, flags=re.DOTALL)

    inline_codes = []
    def save_inline_code(m):
        inline_codes.append(f"<code>{html.escape(m.group(1))}</code>")
        return f"@@@INLINE_CODE_{len(inline_codes)-1}@@@"

    s = re.sub(r'`([^`\n]+)`', save_inline_code, s)

    # 2. If the text doesn't contain HTML tags already, escape <, > and &
    has_existing_tags = bool(re.search(r'</?(?:b|i|u|s|code|pre|a)\b', s, re.IGNORECASE))
    if not has_existing_tags:
        s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    # 3. Format lines: Headers and Bullet points
    lines = s.split('\n')
    formatted_lines = []
    for line in lines:
        stripped = line.strip()

        # Markdown Headers: # H1, ## H2, ### H3, etc.
        m_head = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if m_head:
            header_text = m_head.group(2).strip()
            header_text = re.sub(r'^\*\*(.*?)\*\*$', r'\1', header_text)
            formatted_lines.append(f"<b>{header_text}</b>")
            continue

        # Bullet lists: `* `, `- `, `+ ` or indented `  * `
        m_bullet = re.match(r'^(\s*)[\*\-\+]\s+(.+)$', line)
        if m_bullet:
            indent = m_bullet.group(1)
            content = m_bullet.group(2)
            formatted_lines.append(f"{indent}• {content}")
            continue

        formatted_lines.append(line)

    s = '\n'.join(formatted_lines)

    # 4. Bold: **text** or __text__
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s, flags=re.DOTALL)
    s = re.sub(r'__(.+?)__', r'<b>\1</b>', s, flags=re.DOTALL)

    # 5. Italic: _text_ (surrounded by non-word boundaries)
    s = re.sub(r'(?<!\w)_([^_]+?)_(?!\w)', r'<i>\1</i>', s)

    # 6. Links: [label](url)
    def format_link(m):
        label = m.group(1)
        url = m.group(2)
        return f'<a href="{url}">{label}</a>'
    s = re.sub(r'\[([^\]]+)\]\((https?://[^\s\)]+)\)', format_link, s)

    # 7. Restore code blocks
    for idx, cb in enumerate(code_blocks):
        s = s.replace(f"@@@CODE_BLOCK_{idx}@@@", cb)
    for idx, ic in enumerate(inline_codes):
        s = s.replace(f"@@@INLINE_CODE_{idx}@@@", ic)

    # 8. Clean up extra consecutive line breaks (max 2)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()


def sanitize_for_telegram(raw):
    """
    Sanitizes HTML for Telegram Bot API sendMessage, preserving allowed formatting:
    <b>, <i>, <u>, <s>, <code>, <pre>, <a href="...">, and line breaks.
    If raw input contains Markdown, converts it first into Telegram HTML.
    """
    if not raw:
        return ""
    
    # Check if raw input contains markdown features
    if any(k in raw for k in ['**', '* ', '- ', '+ ', '###', '##', '# ', '```', '`', '__']):
        raw = format_text_for_telegram(raw)

    if '<' not in raw and '&' not in raw:
        return raw.strip()
    parser = TelegramHTMLSanitizer()
    parser.feed(raw)
    return parser.get_result()


def send_telegram_bot_message(token, chat_id, text, reply_markup=None, parse_mode='HTML', reply_to_message_id=None):
    """
    Sends a message to a Telegram chat with optional HTML formatting and reply support.
    Falls back to plain text if Telegram reports parsing error.
    """
    if not token or not chat_id or not text:
        return {'ok': False}

    # If parse_mode is HTML, ensure clean Telegram HTML formatting
    if parse_mode == 'HTML':
        formatted_text = format_text_for_telegram(text)
    else:
        formatted_text = text

    payload = {
        'chat_id': chat_id,
        'text': formatted_text,
    }
    if parse_mode:
        payload['parse_mode'] = parse_mode
    if reply_markup:
        payload['reply_markup'] = reply_markup
    if reply_to_message_id:
        payload['reply_to_message_id'] = reply_to_message_id
        payload['allow_sending_without_reply'] = True

    res = make_telegram_request(token, 'sendMessage', payload)
    # If HTML parsing failed on Telegram, fallback to plain text so message is never lost
    if not res.get('ok') and parse_mode:
        payload.pop('parse_mode', None)
        plain_text = re.sub(r'<[^>]+>', '', formatted_text)
        payload['text'] = plain_text or text
        res = make_telegram_request(token, 'sendMessage', payload)
    return res


def calculate_typing_duration(text):
    """
    Calculates typing delay in seconds based on text length to simulate natural human typing.
    Average human mobile typing speed: ~10-14 chars/sec with natural pauses.
    Range: 3.0s to 16.0s with subtle human variance.
    """
    if not text:
        return 3.0
    char_count = len(str(text).strip())
    # Base preparation time + ~0.075s per character
    duration = 2.5 + (char_count * 0.075)
    # Add slight natural jitter (0.9 to 1.15)
    jitter = random.uniform(0.9, 1.15)
    duration = duration * jitter
    return round(min(max(duration, 3.0), 16.0), 2)


def simulate_typing(token, chat_id, duration_seconds):
    """
    Simulates human typing on Telegram by sending 'typing' chat action
    repeatedly every ~4 seconds until duration_seconds has elapsed.
    """
    import sys
    import time
    if 'test' in sys.argv or duration_seconds <= 0:
        return
    elapsed = 0.0
    while elapsed < duration_seconds:
        send_telegram_chat_action(token, chat_id, 'typing')
        chunk = min(4.0, duration_seconds - elapsed)
        time.sleep(chunk)
        elapsed += chunk


import threading
import time

_chat_state_lock = threading.Lock()
_chat_states = {}


class ChatStateTracker:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.latest_user_msg_id = None
        self.latest_user_text = ""
        self.latest_msg_time = 0.0
        self.active_trigger_id = None
        self.is_task_running = False



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
        welcome_txt = config.welcome_message or (
            f"Assalomu alaykum! {config.business.name} qo‘llab-quvvatlash xizmatiga xush kelibsiz.\n\n"
            "Sizni qiziqtirgan barcha savollarni bemalol shu yerga yozib qoldirishingiz mumkin. "
            "Mutaxassislarimiz savollaringizga shu yerning o‘zida javob berishadi.\n\n"
            "Sizga qanday yordam bera olamiz?"
        )
        
        # Tavsiyaviy savollar chiqarilmaydi, mavjud klaviaturani tozalash
        send_telegram_bot_message(
            config.telegram_bot_token,
            chat_id,
            welcome_txt,
            reply_markup={'remove_keyboard': True}
        )
        return {'ok': True}

    # 1. Save user's incoming message
    user_msg = ChatMessage.objects.create(
        chatbot=config,
        session=session,
        role='user',
        content=text
    )
    from .realtime import notify_chat_update
    notify_chat_update(config.business_id, session.session_id, user_msg.id)

    # Note: Typing status will be shown AFTER the configured delay expires (not immediately)

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
        esc_msg = ChatMessage.objects.create(
            chatbot=config,
            session=session,
            role='assistant',
            content=esc_reply
        )
        notify_chat_update(config.business_id, session.session_id, esc_msg.id)
        send_telegram_bot_message(config.telegram_bot_token, chat_id, esc_reply)
        return {'ok': True}

    # 4. If session is already assigned to an operator and waiting for reply
    if session.is_escalated and session.escalation_status in ['waiting_operator', 'operator_active', 'escalated_supervisor']:
        # The operator will reply from their TMA, but send acknowledgement if needed
        return {'ok': True}

    # 5. Dispatch or execute AI response processing with human-like delay, typing, and reply handling
    message_id = message.get('message_id')

    with _chat_state_lock:
        if chat_id not in _chat_states:
            _chat_states[chat_id] = ChatStateTracker(chat_id)
        tracker = _chat_states[chat_id]
        tracker.latest_user_msg_id = message_id
        tracker.latest_user_text = text
        tracker.latest_msg_time = time.time()
        already_running = tracker.is_task_running
        if not already_running:
            tracker.is_task_running = True
            tracker.active_trigger_id = message_id

    # If already running, the active task will incorporate the new message and reply to it
    if already_running:
        return {'ok': True}

    import sys
    is_testing = 'test' in sys.argv
    if is_testing:
        _process_telegram_response(config.id, session.id, chat_id, message_id, full_name)
    else:
        worker_thread = threading.Thread(
            target=_process_telegram_response,
            args=(config.id, session.id, chat_id, message_id, full_name),
            name=f"TelegramResponseWorker-{chat_id}",
            daemon=True
        )
        worker_thread.start()

    return {'ok': True}


def _process_telegram_response(config_id, session_id, chat_id, trigger_msg_id, full_name):
    """
    Processes AI RAG response for Telegram chat:
    1. Waits configured delay without showing typing indicator.
    2. Switches to 'typing' action when delay passes.
    3. Generates response and calculates typing duration from text length.
    4. Splits into parts if enabled, sending each part after its calculated typing duration.
    5. If a new user message arrived while sending parts, it will be processed in a subsequent turn.
    """
    import sys
    import logging
    from django.db import close_old_connections
    logger = logging.getLogger(__name__)
    is_testing = 'test' in sys.argv

    if not is_testing:
        close_old_connections()
    try:
        from .models import ChatbotConfig, ChatSession, ChatMessage
        config = ChatbotConfig.objects.select_related('business').get(id=config_id)
        session = ChatSession.objects.get(id=session_id)

        while True:
            # 1. Determine Initial Reading Delay (No typing indicator!)
            user_msgs_count = session.messages.filter(role='user').count()

            with _chat_state_lock:
                tracker = _chat_states.get(chat_id)
                latest_text = tracker.latest_user_text if tracker else ""
            if not latest_text:
                last_user_msg = session.messages.filter(role='user').order_by('-created_at').first()
                latest_text = last_user_msg.content if last_user_msg else ""

            if config.response_delay_enabled and not is_testing:
                configured_delay = config.first_message_delay_seconds if user_msgs_count <= 1 else config.subsequent_message_delay_seconds
                configured_delay = min(max(configured_delay, 0), 30)
                # Realistic reading time: human reads ~20-30 chars/sec + thinking time
                read_time = min(len(latest_text) * 0.03, 3.5)
                delay = max(configured_delay, read_time + 1.5) + random.uniform(0.5, 1.5)
            elif not is_testing:
                # Even if delay option is unchecked, human still takes 1.5 - 2.5s to read
                delay = min(len(latest_text) * 0.02, 2.0) + random.uniform(0.5, 1.0)
            else:
                delay = 0

            # Initial pause before typing begins (DO NOT send typing status during this delay)
            if delay > 0:
                elapsed = 0.0
                while elapsed < delay:
                    chunk = min(1.0, delay - elapsed)
                    time.sleep(chunk)
                    elapsed += chunk

            # 2. Switch to Typing Status!
            # Exactly after the reading delay has passed, show typing indicator
            send_telegram_chat_action(config.telegram_bot_token, chat_id, 'typing')
            rag_start = time.time()

            # 3. Generate AI response
            if not is_testing:
                close_old_connections()
            session.refresh_from_db()

            try:
                ai_reply = generate_rag_response(config, latest_text, session)
                from apps.team.services import check_if_needs_escalation, assign_session_to_operator
                needs_esc_ai, _ = check_if_needs_escalation(latest_text, ai_reply)
                if needs_esc_ai and not session.is_escalated:
                    assigned_staff = assign_session_to_operator(session, "AI to'liq javob bera olmadi")
                    if assigned_staff:
                        ai_reply += f"\n\n👨‍💼 Savolingiz bo'yicha mutaxassisimiz ({assigned_staff.name}) ulanmoqda..."
            except Exception as e:
                logger.error("Telegram RAG xatolik: %s", e, exc_info=True)
                ai_reply = "Kechirasiz, texnik nosozlik yuz berdi. Iltimos, qayta urinib ko'ring."

            rag_time = time.time() - rag_start

            # 4. Split message into parts if enabled
            if config.split_messages and '\n\n' in ai_reply:
                parts = [p.strip() for p in ai_reply.split('\n\n') if p.strip()]
            else:
                parts = [ai_reply.strip()]

            if not parts:
                parts = [ai_reply]

            # 5. Send parts sequentially with natural typing durations and pauses
            for idx, part in enumerate(parts):
                part_typing_dur = calculate_typing_duration(part) if not is_testing else 0.0

                if idx == 0:
                    # For the very first part, don't extinguish typing duration.
                    # Ensure active, visible typing continues naturally even if RAG took 2-3s.
                    if not is_testing:
                        remaining_typing = max(3.0, part_typing_dur - (rag_time * 0.4))
                        remaining_typing = min(remaining_typing, part_typing_dur)
                    else:
                        remaining_typing = 0.0
                else:
                    # Natural human pause between distinct message bubbles (2.5s - 4.0s)
                    # During this pause, hands are off the keyboard (no typing indicator)
                    if not is_testing:
                        pause_duration = round(random.uniform(2.5, 4.0), 2)
                        time.sleep(pause_duration)
                    remaining_typing = part_typing_dur

                if remaining_typing > 0:
                    simulate_typing(config.telegram_bot_token, chat_id, remaining_typing)

                send_telegram_bot_message(
                    config.telegram_bot_token,
                    chat_id,
                    part
                )

                # Save assistant message to DB
                if not is_testing:
                    close_old_connections()
                assistant_msg = ChatMessage.objects.create(
                    chatbot=config,
                    session=session,
                    role='assistant',
                    content=part
                )
                from .realtime import notify_chat_update
                notify_chat_update(config.business_id, session.session_id, assistant_msg.id)

            # Check if any brand new message arrived while we were sending the parts
            with _chat_state_lock:
                tracker = _chat_states.get(chat_id)
                if tracker and tracker.latest_user_msg_id:
                    if tracker.latest_user_msg_id > (trigger_msg_id or 0):
                        trigger_msg_id = tracker.latest_user_msg_id
                        tracker.active_trigger_id = trigger_msg_id
                        continue
                if tracker:
                    tracker.is_task_running = False
                break

    except Exception as ex:
        import logging
        logging.getLogger(__name__).error(f"[Telegram Worker] Task error: {ex}", exc_info=True)
        with _chat_state_lock:
            tracker = _chat_states.get(chat_id)
            if tracker:
                tracker.is_task_running = False
    finally:
        if not is_testing:
            close_old_connections()

