import random
import string
import logging
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from .models import Account, Transaction, Notification, ScheduledTransfer

logger = logging.getLogger(__name__)

def generate_pan():
    """Generates a random unique-ish 10-character PAN (5 letters, 4 digits, 1 letter)."""
    letters = ''.join(random.choices(string.ascii_uppercase, k=5))
    digits = ''.join(random.choices(string.digits, k=4))
    last_letter = random.choice(string.ascii_uppercase)
    return f"{letters}{digits}{last_letter}"

def process_scheduled_transfers(user=None):
    """
    Checks for and executes due scheduled transfers.
    If 'user' is NOT provided, it processes due transfers for ALL users.
    """
    now = timezone.now()
    
    # Filter for PENDING transfers where scheduled_at is in the past OR exactly now
    query = ScheduledTransfer.objects.filter(
        status='PENDING',
        scheduled_at__lte=now
    )
    
    # Only limit to user if explicitly requested
    if user and user.is_authenticated:
        query = query.filter(user=user)
    
    due_transfers = query.select_related('sender_account', 'user')
    
    processed_count = 0
    for st in due_transfers:
        # Prevent double execution in the same minute if last_run_at is too close
        if st.last_run_at and (now - st.last_run_at).total_seconds() < 30:
            continue
            
        sender_account = st.sender_account
        receiver_account = Account.objects.filter(account_number=st.receiver_account_number).first()
        
        # IMPROVED ERROR HANDLING: Cancel transfer if receiver is invalid
        if not receiver_account:
            logger.warning(f"Invalid receiver A/C {st.receiver_account_number} for scheduled transfer {st.id}. Cancelling.")
            st.status = 'CANCELLED'
            st.save()
            
            Notification.objects.create(
                user=st.user,
                title="Scheduled Transfer CANCELLED",
                message=f"Oops! We couldn't find account number {st.receiver_account_number}. Your scheduled payment of ₹{st.amount:,.2f} has been cancelled.",
                notification_type='TRANSACTION'
            )
            continue
            
        if sender_account.balance >= st.amount:
            try:
                with transaction.atomic():
                    # Perform the transfer
                    sender_account.balance -= st.amount
                    sender_account.save()
                    
                    receiver_account.balance += st.amount
                    receiver_account.save()
                    
                    # Create Transaction records
                    Transaction.objects.create(
                        account=sender_account,
                        receiver_account=receiver_account,
                        description=f"Auto Payout: {st.description}",
                        amount=st.amount,
                        transaction_type='DEBIT',
                        status='APPROVED'
                    )
                    Transaction.objects.create(
                        account=receiver_account,
                        description=f"Auto Received: {st.description}",
                        amount=st.amount,
                        transaction_type='CREDIT',
                        status='APPROVED'
                    )
                    
                    # Update ScheduledTransfer state
                    st.last_run_at = now
                    
                    if st.frequency == 'ONE_TIME':
                        st.status = 'COMPLETED'
                    else:
                        # Calculate next scheduled_at
                        if st.frequency == 'DAILY':
                            st.scheduled_at += timedelta(days=1)
                        elif st.frequency == 'WEEKLY':
                            st.scheduled_at += timedelta(weeks=1)
                        elif st.frequency == 'MONTHLY':
                            # Simplistic monthly rollover
                            new_month = st.scheduled_at.month + 1
                            new_year = st.scheduled_at.year
                            if new_month > 12:
                                new_month = 1
                                new_year += 1
                            try:
                                st.scheduled_at = st.scheduled_at.replace(year=new_year, month=new_month)
                            except ValueError:
                                # Handle cases like Jan 31 -> Feb 28
                                st.scheduled_at = (st.scheduled_at.replace(year=new_year, month=new_month, day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                    
                    st.save()
                    processed_count += 1
                    
                    # Notify Sender
                    Notification.objects.create(
                        user=st.user,
                        title="Amount Deducted - Scheduled Transfer",
                        message=f"₹{st.amount:,.2f} has been automatically deducted and transferred to A/C {st.receiver_account_number} for '{st.description}'.",
                        notification_type='TRANSACTION'
                    )
                    
                    # Notify Receiver
                    if receiver_account.user:
                        Notification.objects.create(
                            user=receiver_account.user,
                            title="Amount Received - Scheduled Transfer",
                            message=f"₹{st.amount:,.2f} has been credited to your account from {st.user.username} (Scheduled Payment).",
                            notification_type='TRANSACTION'
                        )
                    
                    logger.info(f"Executed scheduled transfer {st.id} for user {st.user.username}")
            except Exception as e:
                logger.error(f"Error processing scheduled transfer {st.id}: {str(e)}")
        else:
            logger.warning(f"Insufficient funds for scheduled transfer {st.id} (user: {st.user.username})")
            
    return processed_count
