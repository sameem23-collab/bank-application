from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from datetime import timedelta
from .models import Account, CustomerProfile, Transaction, Notification, Complaint, ScheduledTransfer, CreditCardApplication, LoanApplication
from .forms import UserRegistrationForm, DepositForm, TransferForm, AccountOpeningForm, ScheduledTransferForm, LoanApplicationForm
from .utils import process_scheduled_transfers, generate_pan



def search_view(request):
    query = request.GET.get('q', '')
    # Simple static search implementation
    pages = [
        {'title': 'About Us', 'url': 'about_us', 'desc': 'Learn more about Indie Bank'},
        {'title': 'Home Loans', 'url': 'home_loans', 'desc': 'Find the best rates for home loans'},
        {'title': 'Credit Cards', 'url': 'credit_cards', 'desc': 'Explore our premium credit cards'},
        {'title': 'Digital Deposits', 'url': 'digital_deposits', 'desc': 'High-yield digital deposits'},
        {'title': 'Wealth Management', 'url': 'wealth_management', 'desc': 'Bespoke investment portfolios'},
        {'title': 'Rates', 'url': 'rates', 'desc': 'View our current interest rates'},
        {'title': 'Contact Us', 'url': 'contact_us', 'desc': 'Get in touch with customer support'},
        {'title': 'Products', 'url': 'products', 'desc': 'Explore all products and services'}
    ]
    
    results = []
    if query:
        q_lower = query.lower()
        results = [p for p in pages if q_lower in p['title'].lower() or q_lower in p['desc'].lower()]
        
    return render(request, 'search_results.html', {'query': query, 'results': results})

def login_view(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            # Staff/superusers bypass KYC approval check
            if not user.is_staff:
                try:
                    profile = user.customerprofile
                    if not profile.is_approved:
                        Notification.objects.create(
                            user=user,
                            title="Unapproved Login Attempt",
                            message=f"User {user.username} (ID: {user.id}) attempted to login but is pending approval.",
                            notification_type='LOGIN_ATTEMPT'
                        )
                        return render(request, 'login.html', {
                            'error': 'Your account is pending admin approval. Please wait for verification.'
                        })
                except CustomerProfile.DoesNotExist:
                    return render(request, 'login.html', {
                        'error': 'No profile found. Please contact support.'
                    })
            login(request, user)
            if user.is_staff:
                return redirect('admin_dashboard')
            return redirect('dashboard')
        else:
            return render(request, 'login.html', {'error': 'Invalid username or password'})
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('index')

# @login_required  # Disabled for "No Security"
def dashboard(request):
    user = request.user
    if not user.is_authenticated:
        # Default to the first user for demo purposes if not logged in
        from django.contrib.auth.models import User
        user = User.objects.first()
    
    try:
        profile = user.customerprofile
        if not profile.is_approved:
            messages.warning(request, "Your account is pending admin approval. You will have full access once approved.")
            return render(request, 'dashboard.html', {'account': None, 'transactions': [], 'pending_approval': True})
    except CustomerProfile.DoesNotExist:
        return redirect('index')

    account = Account.objects.filter(user=user).first()
    
    # Process Scheduled Transfers
    if user.is_authenticated:
        process_scheduled_transfers(user)
        
    transactions = account.transactions.all() if account else []
    return render(request, 'dashboard.html', {'account': account, 'transactions': transactions, 'user': user})

def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password'])
                user.save()
                
                # Create profile with pending approval - admin must approve before login
                pan = generate_pan()
                while CustomerProfile.objects.filter(pan_number=pan).exists():
                    pan = generate_pan()
                CustomerProfile.objects.create(user=user, is_approved=False, pan_number=pan)
                # Generate a simple 12 digit account number based on user ID for demo purposes
                account_num = f"1000{user.id:08d}"
                Account.objects.create(user=user, account_number=account_num)
                
                # Notify Admins
                Notification.objects.create(
                    user=user,
                    title="New User Registration",
                    message=f"A new user {user.username} has registered and requires KYC approval.",
                    notification_type='NEW_USER'
                )
                
                messages.success(request, 'Registration successful! Please login.')
                return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'register.html', {'form': form})

def open_account_view(request):
    if request.method == 'POST':
        form = AccountOpeningForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Create User
                    user = User.objects.create_user(
                        username=form.cleaned_data['username'],
                        email=form.cleaned_data['email'],
                        password=form.cleaned_data['password'],
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name']
                    )
                    
                    # 2. Create Profile
                    pan = generate_pan()
                    while CustomerProfile.objects.filter(pan_number=pan).exists():
                        pan = generate_pan()
                    CustomerProfile.objects.create(
                        user=user,
                        phone_number=form.cleaned_data['phone_number'],
                        address=form.cleaned_data['address'],
                        is_approved=False,  # Requires admin KYC approval
                        pan_number=pan
                    )
                    
                    # 3. Create Account
                    account_num = f"1000{user.id:08d}"
                    Account.objects.create(
                        user=user,
                        account_number=account_num,
                        account_type=form.cleaned_data['account_type'],
                        balance=0.00
                    )
                    
                    # Notify Admins
                    Notification.objects.create(
                        user=user,
                        title="New Account Application",
                        message=f"New user {user.username} has applied for a {form.cleaned_data['account_type']} and requires approval.",
                        notification_type='NEW_USER'
                    )
                    
                    messages.success(request, 'Application submitted successfully! Our team will review your details. You can login once approved.')
                    return redirect('login')
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
    else:
        form = AccountOpeningForm()
    return render(request, 'open_account.html', {'form': form})

# @login_required  # Disabled for "No Security"
def deposit_view(request):
    user = request.user
    if not user.is_authenticated:
        from django.contrib.auth.models import User
        user = User.objects.first()
        
    account = Account.objects.filter(user=user).first()
    if not account:
        messages.error(request, "No account found.")
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = DepositForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            # Large transaction threshold
            status = 'APPROVED'
            
            with transaction.atomic():
                if status == 'APPROVED':
                    account.balance += amount
                    account.save()
                
                Transaction.objects.create(
                    account=account,
                    description="Deposit - Branch Transfer",
                    amount=amount,
                    transaction_type='CREDIT',
                    status=status
                )
            
            messages.success(request, f'Successfully deposited ₹{amount}.')
            return redirect('dashboard')
    else:
        form = DepositForm()
    return render(request, 'deposit.html', {'form': form})



# @login_required  # Disabled for "No Security"
def transfer_view(request):
    user = request.user
    if not user.is_authenticated:
        from django.contrib.auth.models import User
        user = User.objects.first()

    sender_account = Account.objects.filter(user=user).first()
    if not sender_account:
        messages.error(request, "No account found.")
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = TransferForm(request.POST)
        if form.is_valid():
            target_acc_num = form.cleaned_data['target_account_number']
            amount = form.cleaned_data['amount']
            
            if target_acc_num == sender_account.account_number:
                messages.error(request, "Cannot transfer to your own account.")
                return render(request, 'transfer.html', {'form': form})
                
            receiver_account = Account.objects.filter(account_number=target_acc_num).first()
            if not receiver_account:
                messages.error(request, "Target account not found.")
                return render(request, 'transfer.html', {'form': form})
                
            if sender_account.balance >= amount:
                # Mandatory admin approval for all dashboard transfers (User Request)
                status = 'PENDING'
                
                with transaction.atomic():
                    # Deduct from sender immediately (locked until approved/rejected)
                    sender_account.balance -= amount
                    sender_account.save()
                    
                    Transaction.objects.create(
                        account=sender_account,
                        receiver_account=receiver_account,
                        description=f"Transfer to A/C {target_acc_num}",
                        amount=amount,
                        transaction_type='DEBIT',
                        status=status
                    )
                    
                    if status == 'APPROVED':
                        receiver_account.balance += amount
                        receiver_account.save()
                        Transaction.objects.create(
                            account=receiver_account,
                            description=f"Transfer from A/C {sender_account.account_number}",
                            amount=amount,
                            transaction_type='CREDIT',
                            status='APPROVED'
                        )
                
                messages.success(request, f'Transfer of ₹{amount} to account {target_acc_num} initiated. Pending admin approval.')
                return redirect('dashboard')
            else:
                messages.error(request, 'Insufficient balance.')
    else:
        form = TransferForm()
    return render(request, 'transfer.html', {'form': form})

def home(request):
    return render(request, 'home.html')

def upi_view(request):
    """View for the dedicated UPI payments page."""
    return render(request, 'upi.html')

def check_balance_view(request):
    """View for checking account balance via mock PIN."""
    user = request.user
    if not user.is_authenticated:
        from django.contrib.auth.models import User
        user = User.objects.first()
        
    from .models import Account
    account = Account.objects.filter(user=user).first() if user else None
    return render(request, 'check_balance.html', {'account': account, 'user': user})

def is_admin(user):
    return user.is_authenticated and user.is_staff

# ─── Removed Admin Complaint Views (Moved to admin_views.py) ───────────────────


def submit_complaint(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        query_type = request.POST.get('query_type', 'GENERAL')
        message = request.POST.get('message')
        
        complaint = Complaint.objects.create(
            user=request.user if request.user.is_authenticated else None,
            full_name=full_name,
            email=email,
            query_type=query_type,
            message=message
        )
        
        # Send Confirmation Email
        subject = 'Complaint Received - Indie Bank'
        html_message = render_to_string('emails/complaint_confirmation.html', {
            'complaint': complaint,
            'user_name': full_name
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            'support@indiebank.com',
            [email],
            html_message=html_message,
            fail_silently=True
        )
        
        return redirect('complaint_success', complaint_id=complaint.complaint_id)
    
    return render(request, 'complaint_form.html')

def complaint_success(request, complaint_id):
    return render(request, 'complaint_success.html', {'complaint_id': complaint_id})

# Moved to utils.py

# @login_required  # Disabled for "No Security"
def scheduled_transfer_view(request):
    user = request.user
    if not user.is_authenticated:
        from django.contrib.auth.models import User
        user = User.objects.first()
        
    if request.method == 'POST':
        form = ScheduledTransferForm(request.POST)
        if form.is_valid():
            st = form.save(commit=False)
            st.user = user
            # Default to user's first account for this demo
            source_acc = Account.objects.filter(user=user).first()
            if source_acc:
                st.sender_account = source_acc
                st.save()
                # Run one-time check immediately in case it's scheduled for now
                process_scheduled_transfers(user)
                messages.success(request, f'Transfer to {st.receiver_account_number} scheduled for {st.scheduled_at}.')
                return redirect('scheduled_transfer')
            else:
                messages.error(request, 'Source account not found.')
    else:
        form = ScheduledTransferForm()
        
    schedules = ScheduledTransfer.objects.filter(user=user).order_by('status', 'scheduled_at')
    return render(request, 'scheduled_transfer.html', {'form': form, 'schedules': schedules})


# Informational Pages
def about_us(request):
    return render(request, 'about_us.html')

def home_loans(request):
    applications = []
    if request.user.is_authenticated:
        applications = LoanApplication.objects.filter(user=request.user, loan_type='HOME').order_by('-applied_at')
    return render(request, 'home_loans.html', {'applications': applications})

def personal_loans(request):
    applications = []
    if request.user.is_authenticated:
        applications = LoanApplication.objects.filter(user=request.user, loan_type='PERSONAL').order_by('-applied_at')
    return render(request, 'personal_loans.html', {'applications': applications})

def vehicle_loans(request):
    applications = []
    if request.user.is_authenticated:
        applications = LoanApplication.objects.filter(user=request.user, loan_type='VEHICLE').order_by('-applied_at')
    return render(request, 'vehicle_loans.html', {'applications': applications})

def apply_loan(request, loan_type):
    # Map friendly URL names to model choices
    type_map = {
        'home-loan': 'HOME',
        'personal-loan': 'PERSONAL',
        'vehicle-loan': 'VEHICLE',
        'Home Loan': 'HOME',
        'Personal Loan': 'PERSONAL',
        'Vehicle Loan': 'VEHICLE'
    }
    
    internal_type = type_map.get(loan_type, 'HOME')
    
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in to apply for a loan.')
            return redirect('login')
            
        form = LoanApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.user = request.user
            application.loan_type = internal_type
            application.status = 'PENDING'
            application.save()
            
            # Notify admins
            Notification.objects.create(
                user=request.user,
                title=f"New Loan Application: {application.get_loan_type_display()}",
                message=(
                    f"User {request.user.username} has applied for a {application.get_loan_type_display()} "
                    f"of ₹{application.amount:,.2f}.\nPAN: {application.pan_number}"
                ),
                notification_type='SYSTEM'
            )
            
            if internal_type == 'HOME':
                return redirect('home_loans')
            elif internal_type == 'PERSONAL':
                return redirect('personal_loans')
            else:
                return redirect('vehicle_loans')
    else:
        # Pre-fill with data from profile if available
        initial_data = {'loan_type': internal_type}
        if request.user.is_authenticated:
            try:
                profile = request.user.customerprofile
                initial_data.update({
                    'full_name': f"{request.user.first_name} {request.user.last_name}",
                    'pan_number': profile.pan_number,
                })
            except CustomerProfile.DoesNotExist:
                pass
        form = LoanApplicationForm(initial=initial_data)
        
    return render(request, 'apply_loan.html', {
        'form': form, 
        'loan_type_display': loan_type.replace('-', ' ').title()
    })

def credit_cards(request):
    applications = []
    if request.user.is_authenticated:
        applications = CreditCardApplication.objects.filter(user=request.user).order_by('-applied_at')
    return render(request, 'credit_cards.html', {'applications': applications})

def apply_credit_card(request, card_type):
    # Redirect if user already has a pending or approved application
    if request.user.is_authenticated:
        existing = CreditCardApplication.objects.filter(
            user=request.user, status__in=['PENDING', 'APPROVED']
        ).first()
        if existing:
            messages.warning(request, f'You already have an application ({existing.get_status_display()}) for a {existing.get_requested_card_type_display()} Card.')
            return redirect('credit_cards')

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in to apply for a credit card.')
            return redirect('login')

        full_name = request.POST.get('full_name', '').strip()
        pan_number = request.POST.get('pan_number', '').strip().upper()
        annual_income = request.POST.get('annual_income', '')

        if not full_name or not pan_number or not annual_income:
            messages.error(request, 'All fields are required.')
            return render(request, 'apply_credit_card.html', {'card_type': card_type})

        application = CreditCardApplication.objects.create(
            user=request.user,
            requested_card_type=card_type.upper(),
            full_name=full_name,
            pan_number=pan_number,
            annual_income=annual_income,
        )

        # Notify admins via a Notification (visible on admin dashboard)
        Notification.objects.create(
            user=request.user,
            title=f"Credit Card Application: {card_type.capitalize()} Card",
            message=(
                f"User {request.user.username} (ID: {request.user.id}) has applied for a "
                f"{card_type.capitalize()} Credit Card.\n"
                f"Full Name: {full_name}\nPAN: {pan_number}\nAnnual Income: {annual_income}\n"
                f"Application ID: {application.id}"
            ),
            notification_type='CREDIT_CARD'
        )

        messages.success(request, f'Your {card_type.capitalize()} Card application has been submitted! We will review and notify you within 24-48 hours.')
        return redirect('credit_cards')

    card_display = card_type.replace('-', ' ').capitalize()
    profile = request.user.customerprofile if request.user.is_authenticated else None
    return render(request, 'apply_credit_card.html', {'card_type': card_type, 'card_display': card_display, 'profile': profile})

def digital_deposits(request):
    return render(request, 'digital_deposits.html')

def loans_view(request):
    applications = []
    if request.user.is_authenticated:
        applications = LoanApplication.objects.filter(user=request.user).order_by('-applied_at')
    return render(request, 'loans.html', {'applications': applications})

def wealth_management(request):
    return render(request, 'wealth_management.html')

def wealth_management_strategies(request):
    return render(request, 'wealth_management_strategies.html')

def rates(request):
    return render(request, 'rates.html')
def contact_us(request):
    """
    Redirect legacy contact-us to the new unified and enhanced support/complaint system.
    """
    return redirect('submit_complaint')

def products(request):
    return render(request, 'products.html')

def accounts_view(request):
    return render(request, 'accounts.html')

def calculate_roi(request):
    return render(request, 'calculate_roi.html')

def transaction_view(request):
    return render(request, 'transaction.html')

def requests_view(request):
    return render(request, 'requests.html')

def bills_view(request):
    return render(request, 'bills.html')

def statement_view(request):
    user = request.user
    if not user.is_authenticated:
        from django.contrib.auth.models import User
        user = User.objects.first()
    
    account = Account.objects.filter(user=user).first()
    transactions = account.transactions.all() if account else []
    return render(request, 'statement.html', {'account': account, 'transactions': transactions, 'user': user})



def chatbot_view(request):
    return render(request, 'chatbot.html')

def locate_us(request):
    return render(request, 'locate_us.html')

def security_tips(request):
    return render(request, 'security_tips.html')

def terms(request):
    return render(request, 'terms.html')

def privacy(request):
    return render(request, 'privacy.html')

def disclaimer(request):
    return render(request, 'disclaimer.html')

def details(request):
    user = request.user
    is_demo = False
    
    if not user.is_authenticated:
        is_demo = True
        approved_loans = [
            {'loan_type': 'HOME', 'amount': 4500000.00, 'tenure_years': 20, 'id': 7742, 'get_loan_type_display': 'Home Loan', 'admin_remarks': 'Preferential interest rate applied for platinum members.'},
            {'loan_type': 'PERSONAL', 'amount': 500000.00, 'tenure_years': 5, 'id': 8821, 'get_loan_type_display': 'Personal Loan'}
        ]
        credit_cards = [
            {'card_type': 'PLATINUM', 'account_number': '440122998822', 'balance': 185200.50, 'credit_limit': 500000.00},
        ]
    else:
        # Real data from DB
        approved_loans = list(LoanApplication.objects.filter(user=user, status='APPROVED'))
        credit_cards = list(Account.objects.filter(user=user, account_type='CREDIT'))
        
        # If user has no active portfolio products, show them a "Sample Portfolio" to demonstrate features
        if not approved_loans and not credit_cards:
            is_demo = True
            approved_loans = [
                {'loan_type': 'HOME', 'amount': 5250000.00, 'tenure_years': 15, 'id': 9901, 'get_loan_type_display': 'Home Loan (Preview)'},
            ]
            credit_cards = [
                {'card_type': 'GOLD', 'account_number': '510277334411', 'balance': 45000.00, 'credit_limit': 200000.00},
            ]

    return render(request, 'details.html', {
        'approved_loans': approved_loans,
        'credit_cards': credit_cards,
        'is_demo': is_demo
    })

from django.http import JsonResponse
import random

def chatbot_response(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        user_message = data.get('message', '').lower()
        lang = data.get('lang', 'en')
        
        # English Responses
        responses_en = {
            'hello': "Hello! I'M SARA, your Indie Bank AI Assistant. How can I help you today?",
            'hi': "Hi there! Welcome to Indie Bank. I'm SARA. What can I help you with?",
            'balance': "You can check your current balance directly on your personalized Dashboard. It's listed under the 'Total Balance' section of your primary account.",
            'transfer': "To transfer money, go to the 'Transfer' page from your dashboard. You'll need the recipient's account number and the amount you wish to send.",
            'history': "Your full transaction history is available on the 'Transactions' page. You can search by description or filter by Income and Expense to track your spending.",
            'transaction': "Your full transaction history is available on the 'Transactions' page. You can search by description or filter by Income and Expense to track your spending.",
            'loan': "Indie Bank offers Home Loans starting at 8.35% and Personal Loans starting at 10.5%. Visit our 'Home Loans' page to see all available plans.",
            'rate': "Our current savings interest rates are 4.5% p.a., and Fixed Deposits range from 6.5% to 7.8% depending on the tenure.",
            'card': "We offer a range of premium Credit Cards, including the 'Indie Signature' with 5% cashback on all travel and dining.",
            'open account': "Opening a new account is easy! You can apply online through our 'Open Account' page. You'll need your ID proof and a photograph.",
            'deposit': "You can make a deposit at any Indie Bank branch or via a branch transfer. Use the 'Deposit' section on your dashboard.",
            'roi': "Our Return on Investment (ROI) for Fixed Deposits is highly competitive. You can use our interactive 'ROI Calculator'.",
            'calculate': "Our Return on Investment (ROI) for Fixed Deposits is highly competitive. You can use our interactive 'ROI Calculator'.",
            'secure': "Your security is our priority. We use 256-bit encryption and multi-factor authentication to keep your assets safe.",
            'safe': "Your security is our priority. We use 256-bit encryption and multi-factor authentication to keep your assets safe.",
            'support': "Our 24/7 support team is here to help! You can reach us at support@indiebank.com or call our hotline at 1800 123 4567.",
            'contact': "Our 24/7 support team is here to help! You can reach us at support@indiebank.com or call our hotline at 1800 123 4567.",
            'help': "I can help with checking balances, explaining transfers, or finding loan rates. Just ask or tap one of the quick actions below!",
        }

        # Hindi Responses
        responses_hi = {
            'hello': "नमस्ते! मैं सारा (SARA) हूँ, आपका इंडी बैंक AI सहायक। मैं आज आपकी कैसे मदद कर सकती हूँ?",
            'hi': "नमस्ते! इंडी बैंक में आपका स्वागत है। मैं सारा हूँ। मैं आपकी क्या मदद कर सकती हूँ?",
            'balance': "आप अपने व्यक्तिगत डैशबोर्ड पर सीधे अपना वर्तमान बैलेंस देख सकते हैं। यह आपके प्राथमिक खाते के 'कुल बैलेंस' अनुभाग में सूचीबद्ध है।",
            'transfer': "पैसे ट्रांसफर करने के लिए, अपने डैशबोर्ड से 'ट्रांसफर' पेज पर जाएं। आपको प्राप्तकर्ता का खाता संख्या और वह राशि चाहिए जो आप भेजना चाहते हैं।",
            'history': "आपका पूरा लेनदेन इतिहास 'लेनदेन' पेज पर उपलब्ध है। आप अपना खर्च ट्रैक करने के लिए विवरण द्वारा खोज या फ़िल्टर कर सकते हैं।",
            'transaction': "आपका पूरा लेनदेन इतिहास 'लेनदेन' पेज पर उपलब्ध है। आप अपना खर्च ट्रैक करने के लिए विवरण द्वारा खोज या फ़िल्टर कर सकते हैं।",
            'loan': "इंडी बैंक 8.35% से शुरू होने वाले होम लोन और 10.5% से शुरू होने वाले पर्सनल लोन प्रदान करता है।",
            'rate': "हमारी वर्तमान बचत ब्याज दरें 4.5% प्रति वर्ष हैं, और फिक्स्ड डिपॉजिट की अवधि के आधार पर 6.5% से 7.8% तक हैं।",
            'card': "हम प्रीमियम क्रेडिट कार्ड की एक श्रृंखला प्रदान करते हैं, जिसमें सभी यात्रा और डाइनिंग पर 5% कैशबैक के साथ 'इंडी सिग्नेचर' शामिल है।",
            'open account': "नया खाता खोलना आसान है! आप हमारे 'खाता खोलें' पेज के माध्यम से ऑनलाइन आवेदन कर सकते हैं।",
            'deposit': "आप किसी भी इंडी बैंक शाखा में या शाखा हस्तांतरण के माध्यम से जमा कर सकते हैं। अपने डैशबोर्ड पर 'जमा' अनुभाग का उपयोग करें।",
            'roi': "फिक्स्ड डिपॉजिट के लिए हमारा निवेश पर रिटर्न (ROI) अत्यधिक प्रतिस्पर्धी है। आप हमारे इंटरैक्टिव 'ROI कैलकुलेटर' का उपयोग कर सकते हैं।",
            'calculate': "फिक्स्ड डिपॉजिट के लिए हमारा निवेश पर रिटर्न (ROI) अत्यधिक प्रतिस्पर्धी है। आप हमारे इंटरैक्टिव 'ROI कैलकुलेटर' का उपयोग कर सकते हैं।",
            'secure': "आपकी सुरक्षा हमारी प्राथमिकता है। हम आपकी संपत्ति को सुरक्षित रखने के लिए 256-बिट एन्क्रिप्शन का उपयोग करते हैं।",
            'safe': "आपकी सुरक्षा हमारी प्राथमिकता है। हम आपकी संपत्ति को सुरक्षित रखने के लिए 256-बिट एन्क्रिप्शन का उपयोग करते हैं।",
            'support': "हमारी 24/7 सहायता टीम यहाँ मदद के लिए है! आप support@indiebank.com पर संपर्क कर सकते हैं या 1800 123 4567 पर कॉल कर सकते हैं।",
            'contact': "हमारी 24/7 सहायता टीम यहाँ मदद के लिए है! आप support@indiebank.com पर संपर्क कर सकते हैं या 1800 123 4567 पर कॉल कर सकते हैं।",
            'help': "मैं बैलेंस चेक करने, ट्रांसफर समझाने या लोन दरों को खोजने में मदद कर सकती हूँ। बस पूछें!",
        }
        
        # Hindi Keyword Mappings (Map Hindi keywords to English keys)
        hindi_keywords = {
            'नमस्ते': 'hello', 'बैलेंस': 'balance', 'पैसा': 'balance', 'खाता': 'balance',
            'ट्रांसफर': 'transfer', 'भेजना': 'transfer', 'इतिहास': 'history', 'लेनदेन': 'transaction',
            'लोन': 'loan', 'ब्याज': 'rate', 'दर': 'rate', 'कार्ड': 'card', 'क्रेडिट': 'card',
            'नया': 'open account', 'खोलना': 'open account', 'जमा': 'deposit', 'सुरक्षा': 'secure',
            'मदद': 'help', 'कस्टमर': 'support'
        }

        # Default responses
        default_en = "That's an interesting question! While I'm still learning, I can certainly help you with your balance, transfers, loan rates, or account security. Feel free to try our quick action buttons or call our 24/7 hotline at 1800 123 4567."
        default_hi = "यह एक दिलचस्प सवाल है! मुझे आपकी बात समझ नहीं आई। मैं आपके बैलेंस, ट्रांसफर, लोन दरों या खाते की सुरक्षा में मदद कर सकती हूँ। कृपया 1800 123 4567 पर कॉल करें।"
        
        response_text = default_hi if lang == 'hi' else default_en
        active_responses = responses_hi if lang == 'hi' else responses_en
        
        # 1. Check direct map against English keys
        matched = False
        for key in sorted(active_responses.keys(), key=len, reverse=True):
            if key in user_message:
                response_text = active_responses[key]
                matched = True
                break
                
        # 2. Check Hindi keyword mappings if no match yet
        if not matched and lang == 'hi':
            for hi_word, en_key in hindi_keywords.items():
                if hi_word in user_message:
                    response_text = active_responses[en_key]
                    break
                    
        return JsonResponse({'response': response_text})
    return JsonResponse({'error': 'Invalid request'}, status=405)
