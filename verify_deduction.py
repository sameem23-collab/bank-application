import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'banking_project.settings')
django.setup()

from django.utils import timezone
from datetime import timedelta
from main.models import User, Account, ScheduledTransfer, Transaction, Notification
from main.utils import process_scheduled_transfers

def test_scheduled_deduction():
    from django.contrib.auth.models import User
    from main.models import Account
    user = User.objects.filter(username='sameem23').first()
    if not user:
        print("No user `sameem23` found.")
        return

    account = Account.objects.filter(user=user).first()
    if not account:
        print(f"No account found for user {user.username}.")
        return

    print(f"Testing for user: {user.username}, current balance: {account.balance}")
    
    # Create a transfer for 1 minute ago
    scheduled_at = timezone.now() - timedelta(minutes=1)
    
    st = ScheduledTransfer.objects.create(
        user=user,
        sender_account=account,
        receiver_account_number="100000000024", # Valid receiver
        amount=100.00,
        description="Timezone & Receiver Verification",
        scheduled_at=scheduled_at,
        frequency='ONE_TIME',
        status='PENDING'
    )
    print(f"Created scheduled transfer ID {st.id} for {st.scheduled_at}")

    # Trigger processing
    processed = process_scheduled_transfers(user)
    print(f"Processed {processed} transfers.")

    # Refresh data
    account.refresh_from_db()
    st.refresh_from_db()

    print(f"New balance: {account.balance}")
    print(f"Transfer status: {st.status}")
    
    # Check for notifications
    from main.models import Account
    receiver_acc = Account.objects.filter(account_number="100000000024").first()
    sender_notif = Notification.objects.filter(user=user, title__icontains="Amount Deducted").first()
    receiver_notif = Notification.objects.filter(user=receiver_acc.user, title__icontains="Amount Received").first()
    
    if sender_notif:
        print(f"Sender Notification received: {sender_notif.title}")
    if receiver_notif:
        print(f"Receiver Notification received: {receiver_notif.title}")
    
    if not sender_notif and not receiver_notif:
        print("No notification found.")

if __name__ == "__main__":
    test_scheduled_deduction()
