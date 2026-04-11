from django import forms
from django.contrib.auth.models import User
from decimal import Decimal

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

class DepositForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={'step': '0.01', 'placeholder': 'Enter amount '})
    )


class TransferForm(forms.Form):
    target_account_number = forms.CharField(
        max_length=12,
        widget=forms.TextInput(attrs={'placeholder': 'Enter 12-digit Account Number'})
    )
    amount = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={'step': '0.01', 'placeholder': 'Enter amount '})
    )

class AccountOpeningForm(UserRegistrationForm):
    phone_number = forms.CharField(max_length=15, required=True, widget=forms.TextInput(attrs={'placeholder': 'Enter phone number'}))
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter permanent address'}), required=True)
    account_type = forms.ChoiceField(
        choices=[
            ('SAVINGS', 'Savings Account'),
            ('CHECKING', 'Checking Account'),
        ],
        initial='SAVINGS',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta(UserRegistrationForm.Meta):
        pass

from .models import ScheduledTransfer, LoanApplication

class ScheduledTransferForm(forms.ModelForm):
    class Meta:
        model = ScheduledTransfer
        fields = ['receiver_account_number', 'amount', 'description', 'scheduled_at', 'frequency']
        widgets = {
            'scheduled_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'receiver_account_number': forms.TextInput(attrs={'placeholder': '12-digit Account Number'}),
            'description': forms.TextInput(attrs={'placeholder': 'e.g. Rent, EMI, Savings'}),
        }

class LoanApplicationForm(forms.ModelForm):
    class Meta:
        model = LoanApplication
        fields = ['loan_type', 'amount', 'tenure_years', 'full_name', 'pan_number', 'annual_income']
        widgets = {
            'loan_type': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter loan amount'}),
            'tenure_years': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter tenure in years'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter legal full name'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter 10-digit PAN'}),
            'annual_income': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. ₹12,00,000'}),
        }
