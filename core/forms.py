from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Review, Profile, PayoutRequest, Category

class ReviewForm(forms.ModelForm):
    # 1. Define the choices for the dropdown
    RATING_CHOICES = [
        ('', 'SELECT RATING'),
        (5, '5 STARS - EXCELLENT'),
        (4, '4 STARS - VERY GOOD'),
        (3, '3 STARS - GOOD'),
        (2, '2 STARS - FAIR'),
        (1, '1 STAR - POOR'),
    ]

    # 2. Add the field with choices and bold styling
    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select fw-bold border-2'})
    )

    class Meta:
        model = Review
        fields = ['rating', 'title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control fw-bold border-2', 
                'placeholder': 'SUMMARIZE YOUR EXPERIENCE'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control fw-bold border-2', 
                'rows': 4, 
                'placeholder': 'WHAT DID YOU LIKE OR DISLIKE?'
            }),
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
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control fw-bold'})
        }

class PayoutRequestForm(forms.ModelForm):
    class Meta:
        model = PayoutRequest
        fields = ['amount', 'bank_name', 'account_number', 'account_name']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control fw-bold border-2', 
                'placeholder': 'ENTER NAIRA AMOUNT'
            }),
            'bank_name': forms.Select(attrs={
                'class': 'form-select fw-bold border-2',
            }),
            'account_number': forms.TextInput(attrs={
                'class': 'form-control fw-bold border-2', 
                'placeholder': '10-DIGIT ACCOUNT NUMBER',
                'maxlength': '10'
            }),
            'account_name': forms.TextInput(attrs={
                'class': 'form-control fw-bold border-2', 
                'placeholder': 'FULL NAME ON ACCOUNT'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user_balance = kwargs.pop('user_balance', 0)
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount > self.user_balance:
            raise forms.ValidationError(f"INSUFFICIENT BALANCE. YOU ONLY HAVE ₦{self.user_balance} AVAILABLE.")
        if amount < 1000:
            raise forms.ValidationError("MINIMUM WITHDRAWAL IS ₦1,000.00")
        return amount

    def clean_account_number(self):
        acc_num = self.cleaned_data.get('account_number')
        if acc_num and (not acc_num.isdigit() or len(acc_num) != 10):
            raise forms.ValidationError("ACCOUNT NUMBER MUST BE EXACTLY 10 DIGITS.")
        return acc_num