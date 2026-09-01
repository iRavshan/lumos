from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Business


class BusinessSystemTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='alisher',
            email='alisher@example.com',
            password='SecretPassword123!',
            first_name='Alisher'
        )

    def test_landing_page(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Biznesingizni ro'yxatdan o'tkazing")

    def test_user_registration(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'bobur_dev',
            'first_name': 'Bobur',
            'last_name': 'Karimov',
            'email': 'bobur@example.com',
            'password1': 'StrongPass12345!',
            'password2': 'StrongPass12345!'
        })
        self.assertEqual(response.status_code, 302)
        # Should redirect to onboarding
        self.assertRedirects(response, reverse('businesses:onboarding'))
        self.assertTrue(User.objects.filter(username='bobur_dev').exists())

    def test_onboarding_and_dashboard_flow(self):
        # Login user without business
        self.client.login(username='alisher', password='SecretPassword123!')
        
        # Accessing dashboard before business registration redirects to onboarding
        dash_response = self.client.get(reverse('businesses:dashboard'))
        self.assertRedirects(dash_response, reverse('businesses:onboarding'))

        # Register business
        onboard_response = self.client.post(reverse('businesses:onboarding'), {
            'name': 'Lumos Tech Solutions',
            'category': 'IT & Texnologiya',
            'website': 'https://lumostech.uz',
            'telegram': '@lumostech',
            'instagram': 'lumos_tech',
            'phone': '+998901234567',
            'description': 'IT xizmatlari va dasturiy ta\'minot ishlab chiqish.'
        })
        self.assertEqual(onboard_response.status_code, 302)
        self.assertRedirects(onboard_response, reverse('businesses:dashboard'))

        # Check business created
        business = Business.objects.get(user=self.user)
        self.assertEqual(business.name, 'Lumos Tech Solutions')
        self.assertEqual(business.telegram_link, 'https://t.me/lumostech')
        self.assertEqual(business.instagram_link, 'https://instagram.com/lumos_tech')

        # Now dashboard loads successfully
        dash_view = self.client.get(reverse('businesses:dashboard'))
        self.assertEqual(dash_view.status_code, 200)
        self.assertContains(dash_view, 'Lumos Tech Solutions')
        self.assertContains(dash_view, 'IT &amp; Texnologiya')

    def test_edit_business(self):
        # Create business for user
        business = Business.objects.create(
            user=self.user,
            name='Eski Nomi',
            category='Savdo',
            website='https://old.uz',
            telegram='old_tg',
            instagram='old_ig',
            description='Eski tavsif ma\'lumoti.'
        )

        self.client.login(username='alisher', password='SecretPassword123!')
        
        edit_response = self.client.post(reverse('businesses:edit'), {
            'name': 'Yangi Nomi',
            'category': 'Yangi Soha',
            'website': 'https://new.uz',
            'telegram': '@new_tg',
            'instagram': '@new_ig',
            'phone': '+998991234567',
            'description': 'Yangi yangilangan tavsif.'
        })
        self.assertRedirects(edit_response, reverse('businesses:dashboard'))

        business.refresh_from_db()
        self.assertEqual(business.name, 'Yangi Nomi')
        self.assertEqual(business.category, 'Yangi Soha')

    def test_public_profile(self):
        business = Business.objects.create(
            user=self.user,
            name='Public Store',
            category='Savdo',
            website='https://store.uz',
            telegram='store_tg',
            instagram='store_ig',
            description='Ommaviy do\'kon tavsifi.'
        )

        response = self.client.get(reverse('businesses:public_profile', kwargs={'slug': business.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Store')
        self.assertContains(response, 'https://store.uz')

    def test_business_analytics_view_and_calculations(self):
        business = Business.objects.create(
            user=self.user,
            name='Super Market AI',
            category='Supermarket',
            phone='+998901234567',
            description='Oziq-ovqat va maishiy tovarlar savdosi.'
        )

        from apps.chatbot.models import ChatbotConfig, ChatSession, ChatMessage
        chatbot = ChatbotConfig.objects.create(
            business=business,
            bot_name='Super Bot'
        )

        # Create sample sessions and messages
        s1 = ChatSession.objects.create(
            chatbot=chatbot,
            session_id='sess_analytics_1',
            is_escalated=False
        )
        ChatMessage.objects.create(chatbot=chatbot, session=s1, role='user', content='Tovar narxi qancha?')
        ChatMessage.objects.create(chatbot=chatbot, session=s1, role='assistant', content='Narxlar 50000 so\'m.')

        s2 = ChatSession.objects.create(
            chatbot=chatbot,
            session_id='sess_analytics_2',
            is_escalated=True
        )
        ChatMessage.objects.create(chatbot=chatbot, session=s2, role='user', content='Yetkazib berish va nasiya bormi?')

        # Login and view analytics page
        self.client.login(username='alisher', password='SecretPassword123!')
        res_30d = self.client.get(reverse('businesses:analytics'))
        self.assertEqual(res_30d.status_code, 200)
        self.assertContains(res_30d, 'Biznes Analitikasi')
        self.assertContains(res_30d, 'AI Tavsiyalar')
        self.assertContains(res_30d, 'Super Market AI')
        self.assertContains(res_30d, 'AI Avtomatizatsiyasi')

        # Test period filter
        res_7d = self.client.get(reverse('businesses:analytics') + '?period=7d')
        self.assertEqual(res_7d.status_code, 200)

        from apps.businesses.analytics import get_business_analytics
        data = get_business_analytics(business, period='30d')
        self.assertEqual(data['total_sessions'], 2)
        self.assertEqual(data['ai_resolution_rate'], 50.0)
        self.assertTrue(len(data['top_topics']) > 0)
        self.assertTrue(len(data['recommendations']) > 0)

