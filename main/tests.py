from django.test import TestCase, Client
from django.urls import reverse

class ContactUsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.contact_url = reverse('contact_us')

    def test_contact_us_get(self):
        response = self.client.get(self.contact_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'contact_us.html')

    def test_contact_us_post(self):
        data = {
            'full_name': 'Test User',
            'email': 'test@example.com',
            'query_type': 'Account Related',
            'message': 'Hello, this is a test message.'
        }
        response = self.client.post(self.contact_url, data, follow=True)
        self.assertContains(response, "Thank you, Test User!")

class HomePageTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.home_url = reverse('home')

    def test_home_page_status(self):
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')
