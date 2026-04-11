import os
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'banking_project.settings')
django.setup()

from django.contrib.auth.models import User
from main.models import Account, ScheduledTransfer
from django.utils import timezone

# clear existing
ScheduledTransfer.objects.all().delete()

# Get users
users = User.objects.all()

if not users:
    print("No users found. Creating a test user...")
    user = User.objects.create_user(username='testuser', password='password123', is_staff=True)
    sender_account = Account.objects.create(user=user, account_number='100000000001', balance=50000.00)
else:
    user = users.first()
    sender_account = Account.objects.filter(user=user).first()
    if not sender_account:
        sender_account = Account.objects.create(user=user, account_number='100000000001', balance=50000.00)

today = timezone.now().date()

schedules = [
    {
        'receiver_account_number': '100000000002',
        'amount': 5000.00,
        'description': 'Monthly Rent payment',
        'scheduled_date': today + timedelta(days=2),
        'frequency': 'MONTHLY',
        'status': 'PENDING'
    },
    {
        'receiver_account_number': '100000000003',
        'amount': 1500.00,
        'description': 'Internet Bill',
        'scheduled_date': today + timedelta(days=5),
        'frequency': 'MONTHLY',
        'status': 'PENDING'
    },
    {
        'receiver_account_number': '100000000004',
        'amount': 8000.00,
        'description': 'Car Loan EMI',
        'scheduled_date': today + timedelta(days=15),
        'frequency': 'MONTHLY',
        'status': 'PENDING'
    },
    {
        'receiver_account_number': '100000000005',
        'amount': 1000.00,
        'description': 'Gym Membership',
        'scheduled_date': today - timedelta(days=2),
        'frequency': 'MONTHLY',
        'status': 'COMPLETED'
    }
]

for s in schedules:
    ScheduledTransfer.objects.create(
        user=user,
        sender_account=sender_account,
        receiver_account_number=s['receiver_account_number'],
        amount=s['amount'],
        description=s['description'],
        scheduled_date=s['scheduled_date'],
        frequency=s['frequency'],
        status=s['status']
    )

print("Created 4 fake scheduled transfers successfully.")
