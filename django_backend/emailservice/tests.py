from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest import mock

from .models import EmailTemplate
from .dispatcher import enqueue_email
from .emailer import _render


class EmailTemplateTests(TestCase):
	def test_template_fallback_and_render(self):
		EmailTemplate.objects.create(key='welcome', locale='en', subject='Hi {{ name }}', body_html='<p>Hello {{ name }}</p>', status='published', version=1)
		tmpl = EmailTemplate.objects.filter(key='welcome', locale='en', status='published').first()
		self.assertIsNotNone(tmpl)
		rendered = _render(tmpl.subject, {'name': 'Alice'})
		self.assertIn('Alice', rendered)

	def test_missing_variable_raises(self):
		EmailTemplate.objects.create(key='missing_var', locale='en', subject='Hi {{ name }}', body_html='<p>Hello {{ name }}</p>', status='published', version=1)
		tmpl = EmailTemplate.objects.filter(key='missing_var').first()
		with self.assertRaises(Exception):
			_render(tmpl.subject, {})


class DispatcherTests(TestCase):
	@mock.patch('emailservice.tasks.send_email_task.apply_async')
	def test_enqueue_creates_outbox_and_enqueues(self, mock_apply):
		outbox = enqueue_email('otp', 'test@example.com', data={'otp': '123456'}, priority='critical')
		self.assertIsNotNone(outbox)
		self.assertEqual(outbox.to_email, 'test@example.com')
		mock_apply.assert_called()


class AdminAPITests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.admin = User.objects.create_superuser(email='admin@example.com', password='pass')

	def test_admin_endpoint_requires_admin(self):
		url = '/api/emailservice/admin/otp/'
		resp = self.client.post(url, {'to_email': 'a@b.com', 'otp': '123456'}, content_type='application/json')
		self.assertEqual(resp.status_code, 403)  # anonymous
		self.client.force_login(self.admin)
		resp = self.client.post(url, {'to_email': 'a@b.com', 'otp': '123456'}, content_type='application/json')
		self.assertIn(resp.status_code, (200, 201))

# Create your tests here.
