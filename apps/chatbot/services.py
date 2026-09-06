import os
import re
import urllib.request
import json


def extract_contact_info(text):
    """
    Extracts phone number, email and name declarations from user message text.
    """
    contacts = {
        'phone': None,
        'email': None,
        'name': None
    }
    if not text:
        return contacts

    # 1. Phone number detection (Uzbekistan & international formats)
    # Matches +998XXXXXXXXX, 998XXXXXXXXX, 90 123 45 67, +998 90 123-45-67, etc.
    phone_pattern = r'(?:\+?998[\s-]?)?(?:\(?\d{2}\)?[\s-]?)?\d{3}[\s-]?\d{2}[\s-]?\d{2}'
    phone_matches = re.findall(phone_pattern, text)
    for p in phone_matches:
        digits = re.sub(r'\D', '', p)
        if len(digits) >= 9:
            if len(digits) == 9:
                digits = "998" + digits
            if len(digits) == 12 and digits.startswith('998'):
                contacts['phone'] = f"+{digits[:3]} {digits[3:5]} {digits[5:8]} {digits[8:10]} {digits[10:12]}"
                break
            elif len(digits) >= 9:
                contacts['phone'] = p.strip()
                break

    # 2. Email detection
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    email_match = re.search(email_pattern, text)
    if email_match:
        contacts['email'] = email_match.group(0).lower()

    # 3. Name detection in Uzbek / Russian / English
    # "ismim [Ism]", "mening ismim [Ism]", "men [Ism]man", "меня зовут [Имя]", "my name is [Name]"
    name_patterns = [
        r'(?:mening\s+ismim|ismim|meni\s+ismim)\s+([A-ZА-Яa-zа-яЎўҚқҒғҲҳ\']+)',
        r'(?:меня\s+зовут|мое\s+имя)\s+([A-ZА-Яa-zа-я\']+)',
        r'(?:my\s+name\s+is|i\s+am|i\'m)\s+([A-Za-z\']+)',
        r'men\s+([A-ZА-Яa-zа-яЎўҚқҒғҲҳ\']+)(?:man|man\b)',
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip().capitalize()
            # Exclude common non-name words
            if len(candidate) > 2 and candidate.lower() not in ['salom', 'rahmat', 'ha', 'yoq', 'qanday', 'nima', 'kim']:
                contacts['name'] = candidate
                break

    return contacts


def build_business_context(chatbot_config):
    business = chatbot_config.business
    context_parts = [
        f"Kompaniya / Biznes nomi: {business.name}",
    ]
    if business.phone:
        context_parts.append(f"Telefon raqami: {business.phone}")
    if business.website:
        context_parts.append(f"Rasmiy vebsayt: {business.website}")
    if business.telegram:
        context_parts.append(f"Telegram: {business.telegram_link or business.telegram}")
    if business.instagram:
        context_parts.append(f"Instagram: {business.instagram_link or business.instagram}")
    if business.description:
        context_parts.append(f"Biznes haqida to'liq ma'lumot va xizmatlar:\n{business.description}")
    if chatbot_config.extra_knowledge:
        context_parts.append(f"Qo'shimcha ma'lumotlar va tez-tez so'raladigan savollar (FAQ):\n{chatbot_config.extra_knowledge}")

    return "\n\n".join(context_parts)


def ask_gemini_api(system_prompt, user_message, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{system_prompt}\n\nMijoz savoli: {user_message}"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 800,
        }
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        res = json.loads(response.read().decode('utf-8'))
        candidates = res.get('candidates', [])
        if candidates:
            parts = candidates[0].get('content', {}).get('parts', [])
            if parts:
                return parts[0].get('text', '')
    return None


def contextual_fallback_agent(chatbot_config, user_message):
    """
    Intelligent contextual RAG engine for local/offline execution without third-party API keys.
    """
    msg = user_message.lower().strip()
    business = chatbot_config.business

    # 1. Greetings
    if any(w in msg for w in ['salom', 'assalom', 'qale', 'qalay', 'privet', 'hello', 'hi', 'xayrli']):
        return f"Assalomu alaykum! «{business.name}» virtual yordamchisiman. Sizga xizmatlarimiz, bog'lanish yoki boshqa ma'lumotlar bo'yicha qanday yordam bera olaman?"

    # 2. Telegram queries
    if 'telegram' in msg or ' tg ' in f" {msg} ":
        if business.telegram:
            tg_link = business.telegram_link
            return f"Bizning rasmiy Telegram manzilimiz: {tg_link or business.telegram}. Savollaringiz bo'lsa to'g'ridan-to'g'ri yozishingiz mumkin!"
        return f"«{business.name}» uchun Telegram manzili hali ko'rsatilmagan. Biz bilan telefon orqali bog'lanishingiz mumkin."

    # 3. Instagram queries
    if 'instagram' in msg or 'insta' in msg or ' ig ' in f" {msg} ":
        if business.instagram:
            ig_link = business.instagram_link
            return f"Bizning Instagram sahifamiz: {ig_link or business.instagram}. Bizni kuzatib boring!"
        return f"«{business.name}» uchun Instagram sahifasi kiritilmagan."

    # 4. Website queries
    if any(w in msg for w in ['vebsayt', 'sayt', 'saytingiz', 'website', 'havola', 'link', 'url']):
        if business.website:
            return f"Bizning rasmiy vebsaytimiz: {business.website}"
        return f"«{business.name}» rasmiy vebsayti tez kunda ishga tushadi."

    # 5. Phone / Contact queries
    if any(w in msg for w in ['telefon', 'tel', 'nomer', 'raqam', 'aloqa', 'bog\'lanish', 'boglanish', 'kontakt', 'manzil', 'qayerda']):
        contacts = []
        if business.phone:
            contacts.append(f"📞 Telefon: {business.phone}")
        if business.telegram_link:
            contacts.append(f"✈️ Telegram: {business.telegram_link}")
        if business.instagram_link:
            contacts.append(f"📸 Instagram: {business.instagram_link}")
        if business.website:
            contacts.append(f"🌐 Vebsayt: {business.website}")

        if contacts:
            return f"«{business.name}» bilan bog'lanish ma'lumotlari:\n" + "\n".join(contacts)
        return f"«{business.name}» aloqa ma'lumotlari uchun ma'muriyatga murojaat qiling."

    # 6. Extra knowledge / FAQ search
    if chatbot_config.extra_knowledge:
        extra_lines = chatbot_config.extra_knowledge.split('\n')
        # Check if words in user query match extra knowledge
        words = [w for w in re.findall(r'\w+', msg) if len(w) > 3]
        matched_lines = []
        for line in extra_lines:
            line_clean = line.lower()
            if any(w in line_clean for w in words):
                matched_lines.append(line.strip())
        if matched_lines:
            return "\n".join(matched_lines)

    # 7. Services / Description / Company overview queries
    if any(w in msg for w in ['xizmat', 'faoliyat', 'nima qiladi', 'haqida', 'nima ish', 'kompaniya', 'biznes', 'ish', 'tavsif', 'mahsulot']):
        return f"«{business.name}» haqida ma'lumot:\n\n{business.description}"

    # 8. Semantic match against description
    words = [w for w in re.findall(r'\w+', msg) if len(w) > 3]
    desc_sentences = re.split(r'[.!?\n]+', business.description)
    matching_sentences = [s.strip() for s in desc_sentences if any(w in s.lower() for w in words) and len(s.strip()) > 5]

    if matching_sentences:
        return " ".join(matching_sentences[:3])

    # Default friendly fallback
    contact_hints = []
    if business.phone:
        contact_hints.append(f"telefon: {business.phone}")
    if business.telegram:
        contact_hints.append(f"Telegram: {business.telegram}")
    
    hint_text = f" ({', '.join(contact_hints)})" if contact_hints else ""
    return f"Kechirasiz, bu savol bo'yicha aniq ma'lumot topilmadi. Qo'shimcha ma'lumot olish uchun «{business.name}» ma'muriyati bilan bog'lanishingiz mumkin{hint_text}."


def generate_rag_response(chatbot_config, user_message, chat_history=None):
    """
    Primary RAG Response Generator.
    """
    gemini_key = os.environ.get('GEMINI_API_KEY')
    business_context = build_business_context(chatbot_config)

    if gemini_key:
        system_prompt = (
            f"Siz «{chatbot_config.business.name}» kompaniyasining aqlli va xushmuomala virtual AI yordamchisisiz (Nomingiz: {chatbot_config.bot_name}).\n"
            f"Quyida kompaniya haqidagi barcha rasmiy ma'lumotlar berilgan (KONTEKST):\n"
            f"--- KONTEKST BOSHLANDI ---\n"
            f"{business_context}\n"
            f"--- KONTEKST TUGADI ---\n\n"
            f"Qoidalar:\n"
            f"1. Faqat yuqoridagi kontekstda berilgan ma'lumotlarga tayangan holda aniq va lo'nda javob bering.\n"
            f"2. Agar kontekstda javob bo'lmasa, o'zingizdan to'qimang. Xushmuomalalik bilan mijozga mavjud telefon yoki Telegram kontaktlari orqali bog'lanishni tavsiya qiling.\n"
            f"3. Mijoz qaysi tilda savol bersa (o'zbek, rus, ingliz), shu tilda javob bering."
        )
        try:
            ai_reply = ask_gemini_api(system_prompt, user_message, gemini_key)
            if ai_reply:
                return ai_reply.strip()
        except Exception:
            pass

    # Fallback to intelligent local RAG matcher
    return contextual_fallback_agent(chatbot_config, user_message)


def analyze_session_insights(session):
    """
    Analyzes chat session conversation to determine customer intent, sentiment, key interest, and business recommendation.
    """
    user_msgs = [m.content for m in session.messages.all() if m.role == 'user']
    if not user_msgs:
        return {
            'sentiment': 'Noma\'lum',
            'sentiment_color': 'slate',
            'intent': 'Kuzatuvchi',
            'intent_badge': 'bg-slate-100 text-slate-700',
            'key_topic': 'Boshlang\'ich muloqot',
            'opinion': 'Mijoz hali o\'z savolini yozmagan yoki endi kirgan.',
            'recommendation': 'Mijoz bilan iliq salomlashib, unga qanday yordam bera olishingizni so\'rang.',
            'conversion_score': 20,
        }

    all_text = " ".join(user_msgs).lower()
    msg_count = len(user_msgs)

    # 1. Intent Detection
    has_contact = bool(session.visitor_phone or session.visitor_email)
    price_words = ['narx', 'narxi', 'qancha', 'sum', "so'm", 'tolov', "to'lov", 'dollar', 'skidka', 'chegirma', 'tarif']
    order_words = ['buyurtma', 'olmoqchiman', 'zakaz', 'shartnoma', 'sotib', 'yetkazib', 'manzil', 'yetkazish']
    problem_words = ['ishlamayapti', 'muammo', 'kechikdi', 'xato', 'shikoyat', 'yordam', 'boglanolmayapman']

    is_buying = any(w in all_text for w in order_words) or (has_contact and any(w in all_text for w in price_words))
    is_price_inquiry = any(w in all_text for w in price_words)
    is_problem = any(w in all_text for w in problem_words)

    if is_buying:
        intent = "Issiq Lead (Xaridga tayyor)"
        intent_badge = "bg-emerald-50 text-emerald-700 border-emerald-200"
        score = 85 if has_contact else 70
    elif is_price_inquiry:
        intent = "Narx / Shartlar qidirmoqda"
        intent_badge = "bg-indigo-50 text-indigo-700 border-indigo-200"
        score = 65 if has_contact else 50
    elif is_problem:
        intent = "Texnik / Qo'llab-quvvatlash"
        intent_badge = "bg-rose-50 text-rose-700 border-rose-200"
        score = 40
    else:
        intent = "Umumiy qiziqish"
        intent_badge = "bg-sky-50 text-sky-700 border-sky-200"
        score = 35 if msg_count > 2 else 25

    # 2. Sentiment
    if any(w in all_text for w in ['rahmat', 'katta rahmat', 'ajoyib', 'tushundim', 'yaxshi', 'super', 'zo\'r', 'zor']):
        sentiment = "Ijobiy (Qoniqish hosil qilgan)"
        sentiment_color = "emerald"
    elif is_problem or any(w in all_text for w in ['yoq', 'qoniqarsiz', 'yomon', 'kutmoqdaman']):
        sentiment = "E'tibor talab (Xavotirda)"
        sentiment_color = "rose"
    else:
        sentiment = "Neytral / Qiziquvchi"
        sentiment_color = "indigo"

    # 3. Key Topic
    if is_buying:
        key_topic = "Xarid & Xizmat buyurtmasi"
    elif is_price_inquiry:
        key_topic = "Narxlar va to'lov shartlari"
    elif 'telegram' in all_text or 'bot' in all_text:
        key_topic = "Telegram bot / Aloqa kanallari"
    elif 'yetkazib' in all_text or 'manzil' in all_text:
        key_topic = "Yetkazib berish va lokatsiya"
    else:
        key_topic = "Umumiy ma'lumotlar"

    # 4. Opinion (Fikr) & Recommendation (Tavsiya)
    if is_buying:
        opinion = f"Mijoz aniq taklif yoki xarid bo'yicha murojaat qilgan ({msg_count} ta xabar). Bitimni yopish ehtimoli yuqori."
        if session.visitor_phone:
            recommendation = f"Telefon orqali ({session.visitor_phone}) zudlik bilan bog'lanib, shartnomani rasmiylashtiring yoki buyurtmani qabul qiling."
        else:
            recommendation = "Mijozdan telefon raqamini so'rang yoki maxsus taklif/chegirma taqdim etib bitimni tezlashtiring."
    elif is_price_inquiry:
        opinion = "Mijoz narxlar va shartlarni taqqoslamoqda. To'g'ri tushuntirish orqali uni xaridga yo'naltirish mumkin."
        recommendation = "Mijozga biznesingizning asosiy ustunliklarini (sifat, kafolat, qulaylik) eslatib, batafsil hisob-kitob qilib bering."
    elif is_problem:
        opinion = "Mijozda noaniqlik yoki savol yuzaga kelgan. Zudlik bilan xushmuomalalik bilan tushuntirish talab etiladi."
        recommendation = "Mijozning muammosini tezda ijobiy hal qilib, ishonchni mustahkamlang."
    else:
        opinion = f"Mijoz xizmatlar bilan tanishmoqda ({msg_count} ta xabar almashilgan)."
        recommendation = "Mijozning asosiy ehtiyojini aniqlash uchun unga yo'naltiruvchi savol bering va konsultatsiya taklif qiling."

    return {
        'sentiment': sentiment,
        'sentiment_color': sentiment_color,
        'intent': intent,
        'intent_badge': intent_badge,
        'key_topic': key_topic,
        'opinion': opinion,
        'recommendation': recommendation,
        'conversion_score': score,
    }
