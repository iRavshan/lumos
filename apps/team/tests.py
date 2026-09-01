import json
from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from apps.businesses.models import Business
from apps.chatbot.models import ChatbotConfig, ChatSession, ChatMessage
from apps.team.models import StaffMember, EscalationLog
from apps.team.services import check_if_needs_escalation, assign_session_to_operator, check_and_escalate_overdue_chats


class TeamAndEscalationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='boss_ali',
            password='TestPassword123!',
            first_name='Ali'
        )
        self.business = Business.objects.create(
            user=self.user,
            name='Ali Gadgets & Electronics',
            category='Elektronika do\'koni',
            phone='+998901112233',
            description='Smartfonlar va aksessuarlar sotuvi.'
        )
        self.chatbot = ChatbotConfig.objects.create(
            business=self.business,
            bot_name='Ali AI Yordamchi'
        )

        # Create Operator and Supervisor
        self.operator = StaffMember.objects.create(
            business=self.business,
            name='Sardor Operator',
            role='operator',
            telegram_username='@sardor_support',
            sla_minutes=5,
            is_active=True,
            is_online=True
        )
        self.supervisor = StaffMember.objects.create(
            business=self.business,
            name='Kamola Supervisor',
            role='supervisor',
            telegram_username='@kamola_super',
            is_active=True,
            is_online=True
        )

    def test_escalation_detection_service(self):
        # 1. Direct human request
        needs_esc, reason = check_if_needs_escalation("Menga operator bilan gaplashish kerak")
        self.assertTrue(needs_esc)
        self.assertIn("operator", reason.lower())

        # 2. AI unable to answer
        needs_esc2, _ = check_if_needs_escalation("Savol", ai_reply="Kechirasiz, aniq ma'lumot topilmadi.")
        self.assertTrue(needs_esc2)

        # 3. Normal question
        needs_esc3, _ = check_if_needs_escalation("Ish vaqtingiz qachon?", ai_reply="Biz 09:00 dan ishlaymiz")
        self.assertFalse(needs_esc3)

    def test_assign_session_to_operator(self):
        session = ChatSession.objects.create(
            chatbot=self.chatbot,
            session_id='test_sess_esc_1'
        )
        staff = assign_session_to_operator(session, "Mijoz operator so'radi")
        self.assertEqual(staff, self.operator)

        session.refresh_from_db()
        self.assertTrue(session.is_escalated)
        self.assertEqual(session.escalation_status, 'waiting_operator')
        self.assertEqual(session.assigned_staff, self.operator)
        self.assertIsNotNone(session.sla_deadline)

        # Check EscalationLog
        log = EscalationLog.objects.filter(session=session).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.operator, self.operator)
        self.assertFalse(log.is_sla_breached)

    def test_operator_reply_via_tma_api(self):
        session = ChatSession.objects.create(
            chatbot=self.chatbot,
            session_id='test_sess_esc_2',
            assigned_staff=self.operator,
            escalation_status='waiting_operator',
            is_escalated=True
        )
        EscalationLog.objects.create(
            session=session,
            operator=self.operator
        )

        url = reverse('team:tma_reply', kwargs={'token': self.operator.auth_token, 'session_id': session.session_id})
        response = self.client.post(
            url,
            data=json.dumps({'message': 'Assalomu alaykum, men operator Sardor. Qanday yordam bera olaman?'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        # Check message saved as staff
        msg = ChatMessage.objects.filter(session=session, role='staff').first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.sender_staff, self.operator)
        self.assertIn('operator Sardor', msg.content)

        session.refresh_from_db()
        self.assertEqual(session.escalation_status, 'operator_active')

    def test_sla_breach_and_auto_escalation_to_supervisor(self):
        # Create session with expired SLA deadline (10 minutes ago)
        past_time = timezone.now() - timedelta(minutes=10)
        session = ChatSession.objects.create(
            chatbot=self.chatbot,
            session_id='test_sess_overdue_1',
            assigned_staff=self.operator,
            escalation_status='waiting_operator',
            is_escalated=True,
            escalated_at=past_time,
            sla_deadline=past_time
        )
        log = EscalationLog.objects.create(
            session=session,
            operator=self.operator,
            escalated_to_operator_at=past_time
        )

        # Run overdue scanner
        escalated_count = check_and_escalate_overdue_chats(self.business)
        self.assertEqual(escalated_count, 1)

        session.refresh_from_db()
        self.assertEqual(session.escalation_status, 'escalated_supervisor')
        self.assertEqual(session.assigned_staff, self.supervisor)

        log.refresh_from_db()
        self.assertTrue(log.is_sla_breached)
        self.assertEqual(log.supervisor, self.supervisor)
        self.assertIsNotNone(log.escalated_to_supervisor_at)

    def test_supervisor_resolves_chat_via_tma(self):
        session = ChatSession.objects.create(
            chatbot=self.chatbot,
            session_id='test_sess_overdue_2',
            assigned_staff=self.supervisor,
            escalation_status='escalated_supervisor',
            is_escalated=True
        )
        log = EscalationLog.objects.create(
            session=session,
            operator=self.operator,
            supervisor=self.supervisor,
            is_sla_breached=True
        )

        url = reverse('team:tma_resolve', kwargs={'token': self.supervisor.auth_token, 'session_id': session.session_id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)

        session.refresh_from_db()
        self.assertEqual(session.escalation_status, 'resolved')
        self.assertEqual(session.status, 'completed')

        log.refresh_from_db()
        self.assertEqual(log.resolved_by, 'supervisor')
        self.assertIsNotNone(log.resolved_at)

    def test_tma_toggle_status_api(self):
        url = reverse('team:tma_toggle_status', kwargs={'token': self.operator.auth_token})
        self.assertTrue(self.operator.is_online)

        res = self.client.post(url)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()['is_online'])

        self.operator.refresh_from_db()
        self.assertFalse(self.operator.is_online)

    def test_team_dashboard_web_views(self):
        self.client.login(username='boss_ali', password='TestPassword123!')

        # 1. Team List
        list_res = self.client.get(reverse('team:team_list'))
        self.assertEqual(list_res.status_code, 200)
        self.assertContains(list_res, 'Sardor Operator')
        self.assertContains(list_res, 'Kamola Supervisor')

        # 2. Add new operator
        add_res = self.client.post(reverse('team:team_create'), {
            'name': 'Bekzod Kuryer-Operator',
            'role': 'operator',
            'telegram_username': '@bekzod_ops',
            'sla_minutes': 7,
            'is_active': 'on',
            'is_online': 'on'
        })
        self.assertRedirects(add_res, reverse('team:team_list'))
        self.assertTrue(StaffMember.objects.filter(name='Bekzod Kuryer-Operator').exists())

        # 3. Analytics page
        analytics_res = self.client.get(reverse('team:team_analytics'))
        self.assertEqual(analytics_res.status_code, 200)
        self.assertContains(analytics_res, 'Sardor Operator')
