from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Account, Transaction, CustomerProfile, Notification, Beneficiary, PaymentRequest, Bill, LoanApplication

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class CustomerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = CustomerProfile
        fields = ['id', 'user', 'is_approved', 'phone_number', 'address']

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'description', 'amount', 'transaction_type', 'date', 'status']

class AccountSerializer(serializers.ModelSerializer):
    transactions = TransactionSerializer(many=True, read_only=True)
    class Meta:
        model = Account
        fields = ['id', 'account_number', 'balance', 'account_type', 'credit_limit', 'card_type', 'transactions']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'is_read', 'created_at']

class BeneficiarySerializer(serializers.ModelSerializer):
    initials = serializers.ReadOnlyField()
    class Meta:
        model = Beneficiary
        fields = ['id', 'name', 'account_number', 'initials']

class PaymentRequestSerializer(serializers.ModelSerializer):
    requester = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)
    class Meta:
        model = PaymentRequest
        fields = ['id', 'requester', 'receiver', 'amount', 'description', 'status', 'created_at', 'paid_at']

class BillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bill
        fields = ['id', 'name', 'detail', 'amount', 'due_date', 'status', 'icon', 'color', 'created_at']
class LoanApplicationSerializer(serializers.ModelSerializer):
    get_loan_type_display = serializers.CharField(source='get_loan_type_display', read_only=True)
    get_status_display = serializers.CharField(source='get_status_display', read_only=True)
    class Meta:
        model = LoanApplication
        fields = ['id', 'loan_type', 'get_loan_type_display', 'amount', 'tenure_years', 'status', 'get_status_display', 'applied_at']

