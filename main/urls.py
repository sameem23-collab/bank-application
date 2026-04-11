from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, api_views, admin_views

router = DefaultRouter()
router.register(r'accounts', api_views.AccountViewSet, basename='account')
router.register(r'transactions', api_views.TransactionViewSet, basename='transaction')
router.register(r'beneficiaries', api_views.BeneficiaryViewSet, basename='beneficiary')
router.register(r'payment-requests', api_views.PaymentRequestViewSet, basename='payment-request')
router.register(r'bills', api_views.BillViewSet, basename='bill')
router.register(r'loans', api_views.LoanViewSet, basename='loan')

urlpatterns = [
    path('api/session/', api_views.SessionView.as_view(), name='session'),
    path('api/login/', api_views.LoginView.as_view(), name='api_login'),
    path('api/register/', api_views.RegisterView.as_view(), name='api_register'),
    
    # NEW Admin API endpoints
    path('api/admin/stats/', api_views.AdminStatsView.as_view(), name='admin_stats'),
    path('api/admin/pending_accounts/', api_views.AdminPendingAccountsView.as_view(), name='admin_pending_accounts'),
    path('api/admin/pending_transactions/', api_views.AdminPendingTransactionsView.as_view(), name='admin_pending_transactions'),
    path('api/admin/audit_log/', api_views.AdminAuditLogView.as_view(), name='admin_audit_log'),
    path('api/admin/<int:pk>/<str:action_type>/', api_views.AdminActionView.as_view(), name='admin_action'),
    path('api/admin/notifications/', api_views.AdminNotificationsView.as_view(), name='admin_notifications'),
    path('api/admin/notifications/<int:pk>/read/', api_views.AdminNotificationsView.as_view(), name='admin_mark_notification_read'),
    path('api/notifications/', api_views.UserNotificationView.as_view(), name='user_notifications'),
    path('api/notifications/<int:pk>/read/', api_views.UserNotificationView.as_view(), name='user_mark_notification_read'),

    # Support / Complaint System
    path('support/submit/', views.submit_complaint, name='submit_complaint'),
    path('support/success/<str:complaint_id>/', views.complaint_success, name='complaint_success'),
    path('admin-dashboard/complaints/', admin_views.admin_complaints, name='admin_complaints'),
    path('admin-dashboard/complaints/<int:pk>/update/', admin_views.update_complaint_status, name='update_complaint_status'),

    # Credit Card Application Management (Admin)
    path('admin-dashboard/credit-cards/', admin_views.admin_credit_card_list, name='admin_credit_card_list'),
    path('admin-dashboard/credit-cards/<int:app_id>/approve/', admin_views.approve_credit_card, name='approve_credit_card'),
    path('admin-dashboard/credit-cards/<int:app_id>/reject/', admin_views.reject_credit_card, name='reject_credit_card'),

    # Loan Application Management (Admin)
    path('admin-dashboard/loans/', admin_views.admin_loan_list, name='admin_loan_list'),
    path('admin-dashboard/loans/<int:app_id>/approve/', admin_views.approve_loan, name='approve_loan'),
    path('admin-dashboard/loans/<int:app_id>/reject/', admin_views.reject_loan, name='reject_loan'),

    # Admin Core Management
    path('admin-dashboard/users/', admin_views.admin_users_list, name='admin_users_list'),
    path('admin-dashboard/users/add/', admin_views.admin_add_user, name='admin_add_user'),
    path('admin-dashboard/users/<int:user_id>/edit/', admin_views.admin_edit_user, name='admin_edit_user'),
    path('admin-dashboard/users/<int:user_id>/reset-password/', admin_views.admin_reset_user_password, name='admin_reset_user_password'),
    path('admin-dashboard/users/<int:user_id>/transactions/', admin_views.admin_user_transactions, name='admin_user_transactions'),
    path('admin-dashboard/users/<int:user_id>/remove/', admin_views.admin_remove_user, name='admin_remove_user'),
    path('admin-dashboard/accounts/', admin_views.admin_accounts_list, name='admin_accounts_list'),
    path('admin-dashboard/accounts/add/', admin_views.admin_add_account, name='admin_add_account'),
    path('admin-dashboard/transactions/', admin_views.admin_transactions_list, name='admin_transactions_list'),
    path('admin-dashboard/transactions/add/', admin_views.admin_add_transaction, name='admin_add_transaction'),

    path('', views.home, name='index'),
    path('search/', views.search_view, name='search'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('accounts/', views.accounts_view, name='accounts'),
    path('transactions/', views.transaction_view, name='transactions'),
    path('admin-dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('register/', views.register_view, name='register'),
    path('open-account/', views.open_account_view, name='open_account'),
    path('deposit/', views.deposit_view, name='deposit'),
    path('transfer/', views.transfer_view, name='transfer'),
    path('upi/', views.upi_view, name='upi'),
    path('check-balance/', views.check_balance_view, name='check_balance'),
    path('scheduled-transfer/', views.scheduled_transfer_view, name='scheduled_transfer'),
    path('requests/', views.requests_view, name='requests'),
    path('bills/', views.bills_view, name='bills'),
    path('statement/', views.statement_view, name='statement'),
    
    # Informational Pages
    path('locate-us/', views.locate_us, name='locate_us'),
    path('security-tips/', views.security_tips, name='security_tips'),
    path('terms/', views.terms, name='terms'),
    path('privacy/', views.privacy, name='privacy'),
    path('disclaimer/', views.disclaimer, name='disclaimer'),
    path('details/', views.details, name='details'),
    path('about/', views.about_us, name='about_us'),
    path('loans/', views.loans_view, name='loans'),
    path('loans/home/', views.home_loans, name='home_loans'),
    path('loans/personal/', views.personal_loans, name='personal_loans'),
    path('loans/vehicle/', views.vehicle_loans, name='vehicle_loans'),
    path('loans/apply/<str:loan_type>/', views.apply_loan, name='apply_loan'),
    path('credit-cards/', views.credit_cards, name='credit_cards'),
    path('apply-credit-card/<str:card_type>/', views.apply_credit_card, name='apply_credit_card'),
    path('digital-deposits/', views.digital_deposits, name='digital_deposits'),
    path('wealth-management/', views.wealth_management, name='wealth_management'),
    path('wealth-management/strategies/', views.wealth_management_strategies, name='wealth_management_strategies'),
    path('rates/', views.rates, name='rates'),
    path('contact-us/', views.contact_us, name='contact_us'),
    path('products/', views.products, name='products'),
    path('chatbot/', views.chatbot_view, name='chatbot'),
    path('calculate-roi/', views.calculate_roi, name='calculate_roi'),
    path('chatbot-api/', views.chatbot_response, name='chatbot_response'),
    
    # Auth URLs for password reset
    path('', include('django.contrib.auth.urls')),
    
    # API endpoints
    path('api/', include(router.urls)),
]
