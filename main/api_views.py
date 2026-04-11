from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction as db_transaction
from decimal import Decimal, InvalidOperation
from .models import Account, Transaction, CustomerProfile, Notification, Complaint, Beneficiary, PaymentRequest, Bill, LoanApplication, CreditCardApplication
from .serializers import AccountSerializer, TransactionSerializer, CustomerProfileSerializer, UserSerializer, NotificationSerializer, BeneficiarySerializer, PaymentRequestSerializer, BillSerializer, LoanApplicationSerializer
from .utils import process_scheduled_transfers

class SessionView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        if request.user.is_authenticated:
            return Response({
                'authenticated': True, 
                'user': UserSerializer(request.user).data,
                'is_staff': request.user.is_staff
            })
        return Response({'authenticated': False})

from django.contrib.auth import authenticate, login
from .forms import UserRegistrationForm

@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        form = UserRegistrationForm(request.data)
        if form.is_valid():
            with db_transaction.atomic():
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password'])
                user.save()
                CustomerProfile.objects.create(user=user)
                account_num = f"1000{user.id:08d}"
                Account.objects.create(user=user, account_number=account_num)
                Notification.objects.create(
                    user=user,
                    title="New User Registration via API",
                    message=f"A new user {user.username} has registered and requires KYC approval.",
                    notification_type='NEW_USER'
                )
            return Response({'message': 'Registration successful. Please login.'}, status=status.HTTP_201_CREATED)
        return Response({'error': form.errors}, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if not user.is_staff:
                try:
                    profile = user.customerprofile
                    if not profile.is_approved:
                        Notification.objects.create(
                            user=user,
                            title="Unapproved API Login Attempt",
                            message=f"User {user.username} attempted to login via API but is pending approval.",
                            notification_type='LOGIN_ATTEMPT'
                        )
                        return Response({'error': 'Account pending admin approval.'}, status=status.HTTP_403_FORBIDDEN)
                except CustomerProfile.DoesNotExist:
                    return Response({'error': 'No profile found. Please contact support.'}, status=status.HTTP_404_NOT_FOUND)
            login(request, user)
            return Response({'message': 'Login successful', 'is_staff': user.is_staff})
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

@method_decorator(csrf_exempt, name='dispatch')
class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            # For "Unlocked" Mode, if no user is logged in, show accounts for the first user
            from django.contrib.auth.models import User
            user = User.objects.first()
            
        # Process Scheduled Transfers on every account list fetch for real-time feel (Global check)
        process_scheduled_transfers()
            
        return Account.objects.filter(user=user)

    @action(detail=True, methods=['post'])
    def transfer(self, request, pk=None):
        sender_account = self.get_object()
        target_acc_num = request.data.get('target_account_number')
        try:
            amount = Decimal(str(request.data.get('amount', 0)))
        except (ValueError, TypeError, InvalidOperation):
            amount = Decimal('0')

        if not target_acc_num or amount <= 0:
            return Response({'error': 'Invalid target account or amount'}, status=status.HTTP_400_BAD_REQUEST)

        # SECURITY LIMITATIONS
        # All transfers above this threshold require admin review.
        PENDING_THRESHOLD = Decimal('500000.00')

        if target_acc_num == sender_account.account_number:
            return Response({'error': 'Cannot transfer to your own account'}, status=status.HTTP_400_BAD_REQUEST)

        receiver_account = Account.objects.filter(account_number=target_acc_num).first()
        if not receiver_account:
            return Response({'error': 'Target account not found'}, status=status.HTTP_404_NOT_FOUND)

        if sender_account.balance < amount:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

        # Mandatory admin approval for all transfers (User Request)
        trans_status = 'PENDING'

        with db_transaction.atomic():
            # Always debit sender
            sender_account.balance -= amount
            sender_account.save()
            
            # Create DEBIT record for sender
            Transaction.objects.create(
                account=sender_account,
                receiver_account=receiver_account,
                description=f"Transfer to A/C {target_acc_num}",
                amount=amount,
                transaction_type='DEBIT',
                status=trans_status
            )
            
            # Notify Sender
            Notification.objects.create(
                user=sender_account.user,
                title="Transfer Initiated",
                message=f"₹{amount:,.2f} has been debited towards A/C {target_acc_num}. Current status: {trans_status}.",
                notification_type='TRANSACTION'
            )

            # Conditional Credit for instant transfers
            if trans_status == 'APPROVED':
                receiver_account.balance += amount
                receiver_account.save()

                # Create CREDIT record for receiver
                Transaction.objects.create(
                    account=receiver_account,
                    description=f"Transfer from A/C {sender_account.account_number}",
                    amount=amount,
                    transaction_type='CREDIT',
                    status='APPROVED'
                )
                
                # Notify Receiver
                Notification.objects.create(
                    user=receiver_account.user,
                    title="Amount Credited",
                    message=f"₹{amount:,.2f} has been credited to your account from {sender_account.user.username}.",
                    notification_type='TRANSACTION'
                )

        return Response({
            'status': trans_status,
            'message': f'Transfer initiated. Awaiting administrator approval.'
        })

    @action(detail=True, methods=['post'])
    def upi_payment(self, request, pk=None):
        sender_account = self.get_object()
        upi_id = request.data.get('upi_id', '').strip()
        note = request.data.get('note', '').strip()
        
        try:
            amount = Decimal(str(request.data.get('amount', 0)))
        except (ValueError, TypeError, InvalidOperation):
            amount = Decimal('0')

        if not upi_id or amount <= 0:
            return Response({'error': 'Invalid UPI ID or amount'}, status=status.HTTP_400_BAD_REQUEST)

        if sender_account.balance < amount:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

        # Receiver detection
        is_internal = upi_id.endswith('.ib@indiebank')
        receiver_account = None

        if is_internal:
            username = upi_id.replace('.ib@indiebank', '')
            from django.contrib.auth.models import User
            receiver_user = User.objects.filter(username=username).first()
            if not receiver_user:
                return Response({'error': 'Invalid UPI ID: User not found in Indie Bank.'}, status=status.HTTP_404_NOT_FOUND)
            
            receiver_account = Account.objects.filter(user=receiver_user).first()
            if not receiver_account:
                return Response({'error': 'Receiver does not have an active bank account.'}, status=status.HTTP_400_BAD_REQUEST)

            if receiver_account.account_number == sender_account.account_number:
                return Response({'error': 'Cannot transfer to your own account via UPI.'}, status=status.HTTP_400_BAD_REQUEST)

        trans_status = 'APPROVED'
        desc_suffix = f" (Note: {note})" if note else ""

        with db_transaction.atomic():
            # Deduct Sender
            sender_account.balance -= amount
            sender_account.save()

            Transaction.objects.create(
                account=sender_account,
                receiver_account=receiver_account,
                description=f"UPI Payment to {upi_id}{desc_suffix}",
                amount=amount,
                transaction_type='DEBIT',
                status=trans_status
            )
            
            # Notify Sender
            Notification.objects.create(
                user=sender_account.user,
                title="Amount Debited",
                message=f"₹{amount} has been debited from your account towards UPI ID {upi_id}.",
                notification_type='TRANSACTION'
            )

            # Credit Receiver if Internal
            if is_internal and receiver_account:
                receiver_account.balance += amount
                receiver_account.save()
                
                sender_upi = f"{sender_account.user.username}.ib@indiebank" if sender_account.user else "Indie Bank User"
                
                Transaction.objects.create(
                    account=receiver_account,
                    description=f"UPI Payment from {sender_upi}{desc_suffix}",
                    amount=amount,
                    transaction_type='CREDIT',
                    status=trans_status
                )
                
                # Notify Receiver
                Notification.objects.create(
                    user=receiver_user,
                    title="Amount Credited",
                    message=f"₹{amount} has been credited to your account from {sender_upi}.",
                    notification_type='TRANSACTION'
                )

        return Response({
            'status': trans_status,
            'message': f'Successfully paid ₹{amount} to {upi_id}.'
        })

    @action(detail=True, methods=['post'])
    def deposit(self, request, pk=None):
        account = self.get_object()
        try:
            amount = Decimal(str(request.data.get('amount', 0)))
        except (ValueError, TypeError, InvalidOperation):
            amount = Decimal('0')

        if amount <= 0:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

        trans_status = 'APPROVED'

        with db_transaction.atomic():
            if trans_status == 'APPROVED':
                account.balance += amount
                account.save()
            
            Transaction.objects.create(
                account=account,
                description="Deposit - Digital Terminal",
                amount=amount,
                transaction_type='CREDIT',
                status=trans_status
            )
            
            # Notify User
            Notification.objects.create(
                user=account.user,
                title="Deposit Successful",
                message=f"₹{amount:,.2f} has been credited to your account via Digital Terminal.",
                notification_type='TRANSACTION'
            )

        return Response({
            'status': trans_status,
            'message': f'Amount ₹{amount} is pending verification.' if trans_status == 'PENDING' else f'Successfully deposited ₹{amount}.'
        })




class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            # For "Unlocked" Mode, if no user is logged in, show transactions for the first user
            from django.contrib.auth.models import User
            user = User.objects.first()
        return Transaction.objects.filter(account__user=user).order_by('-date')

class AdminStatsView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        from django.contrib.auth.models import User
        total_balance = sum(Account.objects.values_list('balance', flat=True))
        total_users = User.objects.count()
        total_accounts = Account.objects.count()
        total_transactions = Transaction.objects.count()
        pending_accounts = CustomerProfile.objects.filter(is_approved=False).count()
        pending_transactions = Transaction.objects.filter(status='PENDING').count()
        pending_complaints = Complaint.objects.filter(status='PENDING').count()
        pending_loans = LoanApplication.objects.filter(status='PENDING').count()
        pending_cards = CreditCardApplication.objects.filter(status='PENDING').count()
        
        return Response({
            'total_balance': total_balance,
            'total_users': total_users,
            'total_accounts': total_accounts,
            'total_transactions': total_transactions,
            'pending_approvals': pending_accounts + pending_transactions + pending_loans + pending_cards,
            'pending_complaints': pending_complaints,
            'system_status': 'OPTIMAL'
        })

class AdminPendingAccountsView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        profiles = CustomerProfile.objects.filter(is_approved=False)
        return Response(CustomerProfileSerializer(profiles, many=True).data)

class AdminPendingTransactionsView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        txns = Transaction.objects.filter(status='PENDING')
        return Response(TransactionSerializer(txns, many=True).data)

class AdminAuditLogView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        txns = Transaction.objects.all().order_by('-date')[:50]
        return Response(TransactionSerializer(txns, many=True).data)

@method_decorator(csrf_exempt, name='dispatch')
class AdminActionView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, pk, action_type):
        try:
            if action_type == 'approve-account':
                profile = CustomerProfile.objects.get(id=pk)
                profile.is_approved = True
                profile.save()

                # Autogenerated message for the user
                account = Account.objects.filter(user=profile.user).first()
                acc_num = account.account_number if account else "N/A"
                Notification.objects.create(
                    user=profile.user,
                    title="Account Approved - Welcome to Indie Bank",
                    message=(
                        f"Congratulations {profile.user.username}! Your account has been approved.\n\n"
                        f"Customer ID: {profile.user.id}\n"
                        f"Account Number: {acc_num}\n"
                        f"Password: [As set during registration]\n\n"
                        "You can now log in and access all banking services."
                    ),
                    notification_type='SYSTEM'
                )

                # Send Email
                if profile.user.email:
                    email_subject = "Welcome to Indie Bank - Account Approved"
                    email_body = (
                        f"Dear {profile.user.first_name or profile.user.username},\n\n"
                        f"Congratulations! Your Indie Bank account has been approved and is now active.\n\n"
                        f"Customer ID: {profile.user.id}\n"
                        f"Account Number: {acc_num}\n"
                        f"Password: [The password you chose during registration]\n\n"
                        "You can now log in to the portal and start using our digital banking services.\n\n"
                        "Thank you for choosing Indie Bank.\n"
                        "Best Regards,\n"
                        "The Indie Bank Team"
                    )
                    send_mail(
                        email_subject,
                        email_body,
                        'support@indiebank.com',
                        [profile.user.email],
                        fail_silently=True,
                    )

                return Response({'status': 'success', 'message': f'Account for {profile.user.username} approved and notification sent.'})

            elif action_type == 'approve-transaction':
                txn = Transaction.objects.get(id=pk)
                if txn.status == 'PENDING':
                    with db_transaction.atomic():
                        txn.status = 'APPROVED'
                        txn.save()

                        # If it's a DEBIT with a receiver, we must credit the receiver now
                        if txn.transaction_type == 'DEBIT' and txn.receiver_account:
                            receiver_acc = txn.receiver_account
                            receiver_acc.balance += txn.amount
                            receiver_acc.save()

                            # Create the CREDIT record for the receiver
                            Transaction.objects.create(
                                account=receiver_acc,
                                description=f"Transfer from A/C {txn.account.account_number}",
                                amount=txn.amount,
                                transaction_type='CREDIT',
                                status='APPROVED'
                            )

                            # Notify Receiver
                            Notification.objects.create(
                                user=receiver_acc.user,
                                title="Amount Credited",
                                message=f"₹{txn.amount:,.2f} has been credited to your account from {txn.account.user.username} after admin approval.",
                                notification_type='TRANSACTION'
                            )

                            # Notify Sender that it's approved
                            Notification.objects.create(
                                user=txn.account.user,
                                title="Transfer Approved",
                                message=f"Your transfer of ₹{txn.amount:,.2f} to A/C {receiver_acc.account_number} has been approved by the administrator.",
                                notification_type='TRANSACTION'
                            )
                
                return Response({'status': 'success', 'message': f'Transaction {txn.id} approved and funds disbursed.'})

            elif action_type == 'reject-transaction':
                txn = Transaction.objects.get(id=pk)
                if txn.status == 'PENDING':
                    if txn.transaction_type == 'DEBIT':
                        txn.account.balance += txn.amount
                        txn.account.save()
                    
                    txn.status = 'REJECTED'
                    txn.save()

                    # Notify Sender
                    Notification.objects.create(
                        user=txn.account.user,
                        title="Transfer Rejected",
                        message=f"Your transfer of ₹{txn.amount:,.2f} to A/C {txn.receiver_account.account_number if txn.receiver_account else 'N/A'} was rejected by the administrator. The funds have been returned to your account.",
                        notification_type='TRANSACTION'
                    )
                
                return Response({'status': 'success', 'message': f'Transaction {txn.id} rejected and funds reverted.'})

            return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

        except (CustomerProfile.DoesNotExist, Transaction.DoesNotExist) as e:
            return Response({'error': f'Object not found: {str(e)}'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AdminNotificationsView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        notifications = Notification.objects.filter(is_read=False)
        return Response(NotificationSerializer(notifications, many=True).data)

    def post(self, request, pk):
        try:
            notification = Notification.objects.get(id=pk)
            notification.is_read = True
            notification.save()
            return Response({'status': 'success', 'message': f'Notification {pk} marked as read.'})
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

class UserNotificationView(APIView):
    permission_classes = [permissions.AllowAny]

    def _get_user(self, request):
        if request.user.is_authenticated:
            return request.user
        from django.contrib.auth.models import User
        return User.objects.first()

    def get(self, request):
        user = self._get_user(request)
        if not user:
            return Response([])
        notifications = Notification.objects.filter(user=user).order_by('-created_at')
        return Response(NotificationSerializer(notifications, many=True).data)

    def post(self, request, pk):
        user = self._get_user(request)
        if not user:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            notification = Notification.objects.get(id=pk, user=user)
            notification.is_read = True
            notification.save()
            return Response({'status': 'success', 'message': 'Notification marked as read.'})
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

@method_decorator(csrf_exempt, name='dispatch')
class BeneficiaryViewSet(viewsets.ModelViewSet):
    serializer_class = BeneficiarySerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = [SessionAuthentication]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            from django.contrib.auth.models import User
            user = User.objects.first()
        return Beneficiary.objects.filter(user=user)

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_authenticated:
            from django.contrib.auth.models import User
            user = User.objects.first()
        serializer.save(user=user)

@method_decorator(csrf_exempt, name='dispatch')
class PaymentRequestViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentRequestSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            from django.contrib.auth.models import User
            user = User.objects.first()
        from django.db.models import Q
        return PaymentRequest.objects.filter(Q(requester=user) | Q(receiver=user)).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        user = self.request.user
        if not user.is_authenticated:
            from django.contrib.auth.models import User
            user = User.objects.first()
        
        target_username = request.data.get('receiver_username')
        amount = Decimal(str(request.data.get('amount', 0)))
        description = request.data.get('description', 'Money Request')

        if not target_username or amount <= 0:
            return Response({'error': 'Invalid receiver or amount'}, status=status.HTTP_400_BAD_REQUEST)

        from django.contrib.auth.models import User
        receiver = User.objects.filter(username=target_username).first()
        if not receiver:
            return Response({'error': f'User {target_username} not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if receiver == user:
            return Response({'error': 'Cannot request money from yourself'}, status=status.HTTP_400_BAD_REQUEST)

        req = PaymentRequest.objects.create(
            requester=user,
            receiver=receiver,
            amount=amount,
            description=description
        )
        
        # Notify Receiver
        Notification.objects.create(
            user=receiver,
            title="Money Request Received",
            message=f"{user.username} has requested ₹{amount} from you for '{description}'.",
            notification_type='TRANSACTION'
        )

        return Response(PaymentRequestSerializer(req).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        payment_req = self.get_object()
        user = self.request.user
        if not user.is_authenticated:
            from django.contrib.auth.models import User
            user = User.objects.first()

        if payment_req.receiver != user:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
        
        if payment_req.status != 'PENDING':
            return Response({'error': 'Request already processed'}, status=status.HTTP_400_BAD_REQUEST)

        payer_account = Account.objects.filter(user=user).first()
        requester_account = Account.objects.filter(user=payment_req.requester).first()

        if not payer_account or not requester_account:
            return Response({'error': 'Bank account not found for one of the parties'}, status=status.HTTP_400_BAD_REQUEST)

        if payer_account.balance < payment_req.amount:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

        with db_transaction.atomic():
            # Transfers funds
            payer_account.balance -= payment_req.amount
            payer_account.save()
            
            requester_account.balance += payment_req.amount
            requester_account.save()

            # Mark request as paid
            payment_req.status = 'PAID'
            from django.utils import timezone
            payment_req.paid_at = timezone.now()
            payment_req.save()

            # Create Transactions
            Transaction.objects.create(
                account=payer_account,
                receiver_account=requester_account,
                description=f"Payment for Request: {payment_req.description}",
                amount=payment_req.amount,
                transaction_type='DEBIT',
                status='APPROVED'
            )
            
            Transaction.objects.create(
                account=requester_account,
                description=f"Received Payment from {user.username}: {payment_req.description}",
                amount=payment_req.amount,
                transaction_type='CREDIT',
                status='APPROVED'
            )

            # Notify Requester (credited)
            Notification.objects.create(
                user=payment_req.requester,
                title="Payment Received",
                message=f"₹{payment_req.amount:,.2f} credited to your account. {user.username} paid your request for '{payment_req.description}'.",
                notification_type='TRANSACTION'
            )

            # Notify Payer (debited)
            Notification.objects.create(
                user=user,
                title="Amount Debited",
                message=f"₹{payment_req.amount:,.2f} has been debited from your account as payment to {payment_req.requester.username} for '{payment_req.description}'.",
                notification_type='TRANSACTION'
            )

        return Response({'status': 'success', 'message': 'Payment successful'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        payment_req = self.get_object()
        user = self.request.user
        if not user.is_authenticated:
            from django.contrib.auth.models import User
            user = User.objects.first()
            
        if payment_req.receiver != user:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
            
        payment_req.status = 'REJECTED'
        payment_req.save()
        
        # Notify Requester
        Notification.objects.create(
            user=payment_req.requester,
            title="Request Rejected",
            message=f"{user.username} has rejected your request for ₹{payment_req.amount}.",
            notification_type='TRANSACTION'
        )
        
        return Response({'status': 'success', 'message': 'Request rejected'})

@method_decorator(csrf_exempt, name='dispatch')
class BillViewSet(viewsets.ModelViewSet):
    serializer_class = BillSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            from django.contrib.auth.models import User
            user = User.objects.first()
        return Bill.objects.filter(user=user).order_by('due_date')

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_authenticated:
            from django.contrib.auth.models import User
            user = User.objects.first()
        serializer.save(user=user)

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        bill = self.get_object()
        user = self.request.user
        if not user.is_authenticated:
            from django.contrib.auth.models import User
            user = User.objects.first()

        if bill.user != user:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
        
        if bill.status == 'PAID':
            return Response({'error': 'Bill already paid'}, status=status.HTTP_400_BAD_REQUEST)

        account = Account.objects.filter(user=user).first()
        if not account:
            return Response({'error': 'Bank account not found'}, status=status.HTTP_400_BAD_REQUEST)

        if account.balance < bill.amount:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

        with db_transaction.atomic():
            account.balance -= bill.amount
            account.save()

            bill.status = 'PAID'
            bill.save()

            Transaction.objects.create(
                account=account,
                description=f"Bill Payment: {bill.name} ({bill.detail})",
                amount=bill.amount,
                transaction_type='DEBIT',
                status='APPROVED'
            )

            # Notify user that bill was paid
            Notification.objects.create(
                user=user,
                title="Bill Payment Successful",
                message=f"₹{bill.amount:,.2f} debited from your account for {bill.name} ({bill.detail}). Your bill has been paid successfully.",
                notification_type='TRANSACTION'
            )

        return Response({'status': 'success', 'message': f'Bill {bill.name} paid successfully'})

@method_decorator(csrf_exempt, name='dispatch')
class LoanViewSet(viewsets.ModelViewSet):
    serializer_class = LoanApplicationSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            from django.contrib.auth.models import User
            user = User.objects.first()
        return LoanApplication.objects.filter(user=user).order_by('-applied_at')
