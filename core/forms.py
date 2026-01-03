from django import forms
from .models import Review, Profile, PayoutRequest
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

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
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email']

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image']

class PayoutRequestForm(forms.ModelForm):
    class Meta:
        model = PayoutRequest
        fields = ['amount', 'bank_name', 'account_number', 'account_name']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '10'}),
            'bank_name': forms.Select(attrs={'class': 'form-select'}), 
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0123456789'}),
            'account_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Account Holder Name'}),
        }

    def __init__(self, *args, **kwargs):
        self.user_balance = kwargs.pop('user_balance', 0)
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount > self.user_balance:
            raise forms.ValidationError("Insufficient funds. You cannot withdraw more than you have.")
        if amount < 10:
            # Updated to Naira symbol
            raise forms.ValidationError("Minimum withdrawal is ₦10.00")
        return amount