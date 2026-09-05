import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from apps.businesses.models import Business
from .models import ChatbotConfig, ChatMessage, ChatSession
from .services import build_business_context, generate_rag_response


class ChatbotTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='jasur_ceo',
            password='TestPassword123!',
            first_name='Jasur'
        )
        self.business = Business.objects.create(
            user=self.user,
            name='Fast Delivery Express',
            category='Yetkazib berish xizmati',
            website='https://fastdelivery.uz',
            telegram='@fastdelivery_bot',
            instagram='fastdelivery_uz',
            phone='+998712001122',
            description='Toshkent shahri va viloyatlar bo\'yicha tezkor kuryerlik xizmati.'
        )
        self.chatbot = ChatbotConfig.objects.create(
            business=self.business,
            bot_name='Fast Delivery AI Bot',
            extra_knowledge='Ish vaqti: Har kuni 24/7 ishlaymiz.\nToshkent bo\'yicha yetkazib berish narxi: 15 000 so\'m.'
        )

    def test_business_context_builder(self):
        context = build_business_context(self.chatbot)
        self.assertIn('Fast Delivery Express', context)
        self.assertIn('Yetkazib berish xizmati', context)
        self.assertIn('+998712001122', context)
        self.assertIn('https://fastdelivery.uz', context)
        self.assertIn('https://t.me/fastdelivery_bot', context)
        self.assertIn('24/7', context)

    def test_rag_response_generator(self):
        # 1. Services question
        reply_services = generate_rag_response(self.chatbot, "Qanday xizmatlar ko'rsatasizlar?")
        self.assertIn("Fast Delivery Express", reply_services)
        self.assertIn("tezkor kuryerlik", reply_services.lower())

        # 2. Telegram question
        reply_tg = generate_rag_response(self.chatbot, "Telegram bormi?")
        self.assertIn("fastdelivery_bot", reply_tg)

        # 3. Contact question
        reply_contact = generate_rag_response(self.chatbot, "Telefon raqamingiz qanaqa?")
        self.assertIn("712001122", reply_contact)

        # 4. Extra knowledge question
        reply_faq = generate_rag_response(self.chatbot, "Yetkazib berish narxi qancha?")
        self.assertIn("15 000", reply_faq)

    def test_api_config_endpoint(self):
        url = reverse('chatbot:api_config', kwargs={'api_key': self.chatbot.api_key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['bot_name'], 'Fast Delivery AI Bot')
        self.assertEqual(data['business_name'], 'Fast Delivery Express')
        self.assertEqual(response['Access-Control-Allow-Origin'], '*')

    def test_api_chat_endpoint(self):
        url = reverse('chatbot:api_chat', kwargs={'api_key': self.chatbot.api_key})
        response = self.client.post(
            url,
            data=json.dumps({
                'message': 'Xizmatlaringiz haqida aytib bering',
                'session_id': 'test_session_123'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(len(data['reply']) > 0)
        self.assertEqual(data['bot_name'], 'Fast Delivery AI Bot')

        # Check messages logged in database
        self.assertEqual(ChatMessage.objects.filter(chatbot=self.chatbot).count(), 2)
        user_msg = ChatMessage.objects.filter(chatbot=self.chatbot, role='user').first()
        bot_msg = ChatMessage.objects.filter(chatbot=self.chatbot, role='assistant').first()
        self.assertEqual(user_msg.content, 'Xizmatlaringiz haqida aytib bering')
        self.assertEqual(bot_msg.content, data['reply'])

    def test_api_chat_inactive_bot(self):
        self.chatbot.is_active = False
        self.chatbot.save()

        url = reverse('chatbot:api_chat', kwargs={'api_key': self.chatbot.api_key})
        response = self.client.post(
            url,
            data=json.dumps({'message': 'Salom'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

    def test_widget_views(self):
        iframe_url = reverse('chatbot:widget_iframe', kwargs={'api_key': self.chatbot.api_key})
        response = self.client.get(iframe_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fast Delivery AI Bot')

        demo_url = reverse('chatbot:demo_page', kwargs={'api_key': self.chatbot.api_key})
        demo_res = self.client.get(demo_url)
        self.assertEqual(demo_res.status_code, 200)
        self.assertContains(demo_res, 'Fast Delivery Express')

    def test_chatbot_settings_view(self):
        self.client.login(username='jasur_ceo', password='TestPassword123!')
        url = reverse('chatbot:settings')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        post_res = self.client.post(url, {
            'bot_name': 'Yangilangan Bot',
            'welcome_message': 'Salom! Qanday yordam beray?',
            'theme_color': '#2563eb',
            'is_active': 'on',
            'suggested_questions': 'Savol 1\nSavol 2',
            'extra_knowledge': 'Yangi bilim'
        })
        self.assertRedirects(post_res, reverse('businesses:dashboard'))
        self.chatbot.refresh_from_db()
        self.assertEqual(self.chatbot.bot_name, 'Yangilangan Bot')
        self.assertEqual(self.chatbot.theme_color, '#2563eb')

    def test_contact_auto_extraction_and_inbox_flow(self):
        # Visitor sends a message with phone and name
        url = reverse('chatbot:api_chat', kwargs={'api_key': self.chatbot.api_key})
        session_id = 'lead_sess_999'
        
        self.client.post(
            url,
            data=json.dumps({
                'message': 'Assalomu alaykum, mening ismim Temur. Telefonim: +998 90 123 45 67, xizmatlaringiz haqida ma\'lumot kerak.',
                'session_id': session_id
            }),
            content_type='application/json'
        )

        session = ChatSession.objects.get(session_id=session_id)
        self.assertEqual(session.visitor_name, 'Temur')
        self.assertIn('+998 90 123 45 67', session.visitor_phone)
        self.assertEqual(session.status, 'new')

        # Business owner logs in and views Inbox
        self.client.login(username='jasur_ceo', password='TestPassword123!')
        inbox_res = self.client.get(reverse('chatbot:inbox'))
        self.assertEqual(inbox_res.status_code, 200)
        self.assertContains(inbox_res, 'Temur')
        self.assertContains(inbox_res, '+998 90 123 45 67')

        # Detail view for this session
        detail_res = self.client.get(reverse('chatbot:inbox_detail', kwargs={'session_id': session_id}))
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, 'Temur')

        # Update lead status and note
        update_url = reverse('chatbot:update_lead', kwargs={'session_id': session_id})
        update_res = self.client.post(update_url, {
            'visitor_name': 'Temur Mahmudov',
            'visitor_phone': '+998 90 123 45 67',
            'visitor_email': 'temur@example.com',
            'status': 'in_progress',
            'notes': 'Mijoz ertaga 10:00 da qo\'ng\'iroq qilishni so\'radi.'
        })
        self.assertRedirects(update_res, reverse('chatbot:inbox_detail', kwargs={'session_id': session_id}))

        session.refresh_from_db()
        self.assertEqual(session.visitor_name, 'Temur Mahmudov')
        self.assertEqual(session.status, 'in_progress')
        self.assertEqual(session.notes, 'Mijoz ertaga 10:00 da qo\'ng\'iroq qilishni so\'radi.')

    def test_telegram_bot_settings_page_and_token_saving(self):
        self.client.login(username='jasur_ceo', password='TestPassword123!')
        url = reverse('chatbot:telegram_settings')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Telegram Bot Boshqaruvi')
        self.assertContains(response, 'BotFather')

        # Mock token verification
        from unittest.mock import patch
        with patch('apps.chatbot.views.verify_telegram_bot_token') as mock_verify, \
             patch('apps.chatbot.views.set_telegram_webhook') as mock_webhook:
            mock_verify.return_value = (True, {'id': 12345, 'username': 'FastDeliveryBot', 'first_name': 'Fast Delivery AI'}, "")
            mock_webhook.return_value = {'ok': True}

            post_res = self.client.post(url, {
                'telegram_bot_token': '123456789:MockTokenXYZ',
                'telegram_bot_active': 'on'
            })
            self.assertRedirects(post_res, reverse('chatbot:telegram_settings'))

            self.chatbot.refresh_from_db()
            self.assertEqual(self.chatbot.telegram_bot_token, '123456789:MockTokenXYZ')
            self.assertEqual(self.chatbot.telegram_bot_username, 'FastDeliveryBot')
            self.assertTrue(self.chatbot.telegram_bot_active)

    def test_telegram_webhook_handling_and_rag_response(self):
        self.chatbot.telegram_bot_token = '123456789:MockTokenXYZ'
        self.chatbot.telegram_bot_username = 'FastDeliveryBot'
        self.chatbot.telegram_bot_active = True
        self.chatbot.save()

        from unittest.mock import patch
        with patch('apps.chatbot.telegram_service.send_telegram_bot_message') as mock_send:
            mock_send.return_value = {'ok': True}

            webhook_url = reverse('chatbot:telegram_webhook', kwargs={'api_key': self.chatbot.api_key})
            
            # 1. Test /start update
            start_payload = {
                'update_id': 1001,
                'message': {
                    'message_id': 1,
                    'from': {'id': 987654, 'first_name': 'Rustam', 'username': 'rustam_uz'},
                    'chat': {'id': 987654, 'type': 'private'},
                    'text': '/start'
                }
            }
            res_start = self.client.post(webhook_url, data=json.dumps(start_payload), content_type='application/json')
            self.assertEqual(res_start.status_code, 200)

            # 2. Test Question update
            msg_payload = {
                'update_id': 1002,
                'message': {
                    'message_id': 2,
                    'from': {'id': 987654, 'first_name': 'Rustam', 'username': 'rustam_uz'},
                    'chat': {'id': 987654, 'type': 'private'},
                    'text': 'Yetkazib berish narxi qancha?'
                }
            }
            res_msg = self.client.post(webhook_url, data=json.dumps(msg_payload), content_type='application/json')
            self.assertEqual(res_msg.status_code, 200)

            # Check session created as Telegram lead
            session = ChatSession.objects.filter(session_id='tg_987654').first()
            self.assertIsNotNone(session)
            self.assertIn('Rustam', session.visitor_name)
            self.assertEqual(session.visitor_email, '@rustam_uz')

            # Check messages logged
            msgs = ChatMessage.objects.filter(session=session)
            self.assertEqual(msgs.count(), 2)
            user_msg = msgs.filter(role='user').first()
            bot_msg = msgs.filter(role='assistant').first()
            self.assertEqual(user_msg.content, 'Yetkazib berish narxi qancha?')
            self.assertIn('15 000', bot_msg.content)

    def test_export_inbox_excel(self):
        self.client.login(username='jasur_ceo', password='TestPassword123!')
        
        # Create a website lead and a telegram lead
        ChatSession.objects.create(
            chatbot=self.chatbot,
            session_id='sess_web_101',
            visitor_name='Ali Valiyev',
            visitor_phone='+998901112233'
        )
        ChatSession.objects.create(
            chatbot=self.chatbot,
            session_id='tg_998877',
            visitor_name='Vali Aliyev',
            visitor_phone='+998909998877'
        )

        export_url = reverse('chatbot:export_excel')
        response = self.client.get(export_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertIn('.xlsx', response['Content-Disposition'])

        # Verify Excel sheets using openpyxl
        import io, openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(response.content))
        self.assertIn("Vebsayt Murojaatlari", wb.sheetnames)
        self.assertIn("Telegram Murojaatlari", wb.sheetnames)

        ws_web = wb["Vebsayt Murojaatlari"]
        ws_tg = wb["Telegram Murojaatlari"]

        # Check content in web sheet
        web_names = [row[1] for row in ws_web.iter_rows(values_only=True) if row[1]]
        self.assertIn("Ali Valiyev", web_names)

        # Check content in tg sheet
        tg_names = [row[1] for row in ws_tg.iter_rows(values_only=True) if row[1]]
        self.assertIn("Vali Aliyev", tg_names)



