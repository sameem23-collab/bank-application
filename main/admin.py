from django.contrib import admin
from .models import CustomerProfile, Account, Transaction, Complaint

@admin.action(description="Approve KYC for selected profiles")
def approve_kyc(modeladmin, request, queryset):
    queryset.update(is_approved=True)

@admin.action(description="Revoke KYC for selected profiles")
def revoke_kyc(modeladmin, request, queryset):
    queryset.update(is_approved=False)

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'is_approved')
    list_filter = ('is_approved',)
    actions = [approve_kyc, revoke_kyc]

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('account_number', 'user', 'account_type', 'balance')
    list_filter = ('account_type',)
    search_fields = ('account_number', 'user__username')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'account', 'description', 'amount', 'transaction_type')
    list_filter = ('transaction_type', 'date')
    search_fields = ('description', 'account__account_number')

@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('complaint_id', 'full_name', 'email', 'query_type', 'status', 'created_at')
    list_filter = ('status', 'query_type', 'created_at')
    search_fields = ('complaint_id', 'full_name', 'email', 'message')
    readonly_fields = ('complaint_id', 'created_at', 'updated_at')
