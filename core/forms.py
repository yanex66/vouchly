from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Review, Profile, PayoutRequest, Category

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'title', 'content']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Summarize your experience'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'What did you like or dislike?'}),
        }

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Required. A valid email address.")

    class Meta:
        model = User
        fields = ['username', 'email']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image']

class PayoutRequestForm(forms.ModelForm):
    class Meta:
        model = PayoutRequest
        fields = ['amount', 'bank_name', 'account_number', 'account_name']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control fw-bold', 
                'placeholder': 'Enter Naira amount'
            }),
            'bank_name': forms.Select(attrs={
                'class': 'form-select',
            }),
            'account_number': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '10-digit Account Number',
                'maxlength': '10'
            }),
            'account_name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Full Name on Account'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user_balance = kwargs.pop('user_balance', 0)
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount > self.user_balance:
            raise forms.ValidationError(f"Insufficient balance. You only have ₦{self.user_balance} available.")
        if amount < 1000:
            raise forms.ValidationError("Minimum withdrawal is ₦1,000.00")
        return amount

    def clean_account_number(self):
        acc_num = self.cleaned_data.get('account_number')
        if acc_num and (not acc_num.isdigit() or len(acc_num) != 10):
            raise forms.ValidationError("Account number must be exactly 10 digits.")
        return acc_num