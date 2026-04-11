from django.test import TestCase, Client
from django.contrib.auth.models import User
from decimal import Decimal
from .models import Account, Transaction

class APITransferTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client = Client()
        self.client.login(username='testuser', password='password')
        
        self.account = Account.objects.create(
            user=self.user,
            account_number='123456789012',
            balance=Decimal('1000.00'),
            account_type='SAVINGS'
        )
        
        self.receiver_user = User.objects.create_user(username='receiver', password='password')
        self.receiver_account = Account.objects.create(
            user=self.receiver_user,
            account_number='098765432109',
            balance=Decimal('500.00'),
            account_type='SAVINGS'
        )

    def test_transfer_success(self):
        url = f'/api/accounts/{self.account.id}/transfer/'
        data = {
            'target_account_number': '098765432109',
            'amount': '100.50'
        }
        response = self.client.post(url, data, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        self.account.refresh_from_db()
        self.receiver_account.refresh_from_db()
        
        self.assertEqual(self.account.balance, Decimal('899.50'))
        self.assertEqual(self.receiver_account.balance, Decimal('600.50'))
        self.assertEqual(Transaction.objects.count(), 2)

    def test_deposit_success(self):
        url = f'/api/accounts/{self.account.id}/deposit/'
        data = {
            'amount': '250.75'
        }
        response = self.client.post(url, data, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('1250.75'))
        self.assertEqual(Transaction.objects.count(), 1)
