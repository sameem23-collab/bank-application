from django.db import models
from django.contrib.auth.models import User

class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    pan_number = models.CharField(max_length=10, blank=True, null=True)
    is_approved = models.BooleanField(default=False) # Requires admin approval

    def __str__(self):
        return f"{self.user.username}'s Profile"

class Account(models.Model):
    ACCOUNT_TYPES = [
        ('SAVINGS', 'Savings Account'),
        ('CHECKING', 'Checking Account'),
        ('CREDIT', 'Credit Card'),
    ]

    CARD_TYPE_CHOICES = [
        ('PLATINUM', 'Platinum'),
        ('GOLD', 'Gold'),
        ('SILVER', 'Silver'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    account_number = models.CharField(max_length=12, unique=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='SAVINGS')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    # Credit card specific fields
    card_type = models.CharField(max_length=20, choices=CARD_TYPE_CHOICES, null=True, blank=True)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_account_type_display()} - {self.account_number}"

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('CREDIT', 'Credit'),
        ('DEBIT', 'Debit'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    receiver_account = models.ForeignKey(Account, on_delete=models.SET_NULL, related_name='received_transactions', null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='APPROVED')

    class Meta:
        ordering = ['-date'] # Show newest first

    def __str__(self):
        return f"{self.date.strftime('%Y-%m-%d')} - {self.description} ({self.amount})"

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('NEW_USER', 'New User Registration'),
        ('LOGIN_ATTEMPT', 'Unapproved Login Attempt'),
        ('SYSTEM', 'System Alert'),
        ('TRANSACTION', 'Transaction Alert'),
        ('COMPLAINT', 'Complaint Update'),
        ('CREDIT_CARD', 'Credit Card Application'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True) # The user related to this notification
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='SYSTEM')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.title}"

class Complaint(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
    ]

    QUERY_CHOICES = [
        ('ACCOUNT', 'Account Related'),
        ('LOAN', 'Loan Inquiry'),
        ('CARD', 'Credit Card Support'),
        ('TECH', 'Technical Issue'),
        ('OTHER', 'Other'),
        ('GENERAL', 'General Support'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='complaints')
    complaint_id = models.CharField(max_length=20, unique=True, editable=False)
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    query_type = models.CharField(max_length=20, choices=QUERY_CHOICES, default='GENERAL')
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.complaint_id:
            import random
            from django.utils import timezone
            # Generate ID format: COMP-YYYYMMDD-XXXX
            date_str = timezone.now().strftime('%Y%m%d')
            random_str = ''.join(random.choices('0123456789', k=4))
            self.complaint_id = f"COMP-{date_str}-{random_str}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.complaint_id} - {self.full_name}"

class ScheduledTransfer(models.Model):
    FREQUENCY_CHOICES = [
        ('ONE_TIME', 'One-time'),
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scheduled_transfers')
    sender_account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='scheduled_debits')
    receiver_account_number = models.CharField(max_length=12)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255)
    scheduled_at = models.DateTimeField()
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='ONE_TIME')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    last_run_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} to {self.receiver_account_number} on {self.scheduled_at}"

class Beneficiary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='beneficiaries')
    name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=12)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.account_number})"

    @property
    def initials(self):
        names = self.name.split()
        if len(names) >= 2:
            return f"{names[0][0]}{names[1][0]}".upper()
        return self.name[:2].upper()

class PaymentRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('REJECTED', 'Rejected'),
    ]
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_requests')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Request: {self.requester.username} -> {self.receiver.username} ({self.amount})"

class Bill(models.Model):
    STATUS_CHOICES = [
        ('UNPAID', 'Unpaid'),
        ('PAID', 'Paid'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bills')
    name = models.CharField(max_length=255)
    detail = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UNPAID')
    icon = models.CharField(max_length=50, default='fas fa-file-invoice-dollar')
    color = models.CharField(max_length=20, default='#3b82f6')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Bill: {self.name} for {self.user.username} ({self.amount})"


class CreditCardApplication(models.Model):
    CARD_TYPE_CHOICES = [
        ('PLATINUM', 'Platinum'),
        ('GOLD', 'Gold'),
        ('SILVER', 'Silver'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credit_card_applications')
    requested_card_type = models.CharField(max_length=20, choices=CARD_TYPE_CHOICES)
    full_name = models.CharField(max_length=255)
    pan_number = models.CharField(max_length=10)
    annual_income = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    # Assigned by admin on approval
    assigned_card_type = models.CharField(max_length=20, choices=CARD_TYPE_CHOICES, null=True, blank=True)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    admin_remarks = models.TextField(blank=True, null=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.requested_card_type} Card Application ({self.status})"

class LoanApplication(models.Model):
    LOAN_TYPES = [
        ('HOME', 'Home Loan'),
        ('PERSONAL', 'Personal Loan'),
        ('VEHICLE', 'Vehicle Loan'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loan_applications')
    loan_type = models.CharField(max_length=20, choices=LOAN_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    tenure_years = models.IntegerField()
    full_name = models.CharField(max_length=255)
    pan_number = models.CharField(max_length=10)
    annual_income = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    admin_remarks = models.TextField(blank=True, null=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.loan_type} Application ({self.status})"
