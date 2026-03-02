from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import (
    Review, Profile, PayoutRequest, Category, 
    PromotionPlan, AdvertiserVerification, SubscriptionPrice
)

# --- 1. SELLER PROMOTION FORM ---
class PromotionRequestForm(forms.ModelForm):
    website_url = forms.URLField(
        required=False, 
        label="WEBSITE LINK",
        widget=forms.URLInput(attrs={'placeholder': 'E.G. HTTPS://YOURSTORE.COM/PRODUCT'})
    )
    
    duration_days = forms.ChoiceField(
        label="SELECT SUBSCRIPTION PLAN",
        choices=[], 
        widget=forms.Select(attrs={'class': 'form-select fw-bold border-2 rounded-4'})
    )

    agree_to_commissions = forms.BooleanField(
        required=True,
        label="I AGREE TO THE CALCULATED COMMISSION FOR VOUCHLY MARKETERS",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = PromotionPlan
        fields = [
            'product_name', 
            'category', 
            'product_price', 
            'commission_percentage', 
            'product_image', 
            'description', 
            'duration_days',
            'destination_type', 
            'website_url'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'DESCRIBE YOUR PRODUCT...'}),
            'product_name': forms.TextInput(attrs={'placeholder': 'E.G. WIRELESS NOISE-CANCELLING HEADPHONES'}),
            'product_price': forms.NumberInput(attrs={'placeholder': 'E.G. 50000.00', 'min': '0'}),
            'commission_percentage': forms.NumberInput(attrs={
                'placeholder': '0', 
                'min': '0', 
                'max': '100', 
                'value': '0',
                'autocomplete': 'off'
            }),
            'destination_type': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial['commission_percentage'] = 0

        plans = SubscriptionPrice.objects.all().order_by('duration_days')
        if plans.exists():
            self.fields['duration_days'].choices = [
                (p.duration_days, f"{p.plan_name} (₦{p.price:,.0f})") for p in plans
            ]
        
        for field in self.fields:
            if field != 'agree_to_commissions':
                current_widget = self.fields[field].widget
                css_class = 'form-select' if isinstance(current_widget, forms.Select) else 'form-control'
                current_widget.attrs.update({'class': f'{css_class} fw-bold border-2 rounded-4'})

# --- 2. PROFILE UPDATE FORM ---
class ProfileUpdateForm(forms.ModelForm):
    email = forms.EmailField(
        required=False,
        label="EMAIL ADDRESS",
        widget=forms.EmailInput(attrs={'placeholder': 'YOUR EMAIL ADDRESS'})
    )

    class Meta:
        model = Profile
        fields = ['image', 'whatsapp_number', 'bank_name', 'account_number', 'account_name']
        widgets = {
            'image': forms.FileInput(attrs={'id': 'id_image'}), 
            'whatsapp_number': forms.TextInput(attrs={'placeholder': 'E.G. 08031234567'}),
            'bank_name': forms.Select(), 
            'account_number': forms.TextInput(attrs={'maxlength': '10', 'placeholder': '10-DIGIT ACCOUNT NUMBER'}),
            'account_name': forms.TextInput(attrs={'readonly': 'readonly', 'placeholder': 'AUTO-VERIFIED NAME'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['email'].initial = self.instance.user.email

        for field in self.fields:
            current_widget = self.fields[field].widget
            css_class = 'form-select' if isinstance(current_widget, forms.Select) else 'form-control'
            current_widget.attrs.update({'class': f'{css_class} fw-bold border-2 rounded-4'})

# --- 3. REVIEW FORM ---
class ReviewForm(forms.ModelForm):
    RATING_CHOICES = [
        (5, '⭐⭐⭐⭐⭐ (5/5) - Excellent'),
        (4, '⭐⭐⭐⭐ (4/5) - Very Good'),
        (3, '⭐⭐⭐ (3/5) - Average'),
        (2, '⭐⭐ (2/5) - Poor'),
        (1, '⭐ (1/5) - Terrible'),
    ]
    
    rating = forms.ChoiceField(
        choices=RATING_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-select fw-bold border-2 rounded-4', 'style': 'padding: 12px; background-color: #f8fafc;'})
    )

    class Meta:
        model = Review
        fields = ['rating', 'title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control fw-bold border-2 rounded-4', 'placeholder': 'Summarize your vouch...', 'style': 'padding: 12px; background-color: #f8fafc;'}),
            'content': forms.Textarea(attrs={'class': 'form-control fw-bold border-2 rounded-4', 'rows': 4, 'placeholder': 'Tell the community about your experience...', 'style': 'padding: 12px; background-color: #f8fafc;'}),
        }

# --- 4. REGISTRATION FORM ---
class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control fw-bold border-2 rounded-4'}))
    user_type = forms.ChoiceField(
        choices=[('MARKETER', 'Marketer'), ('ADVERTISER', 'Advertiser')], 
        widget=forms.Select(attrs={'class': 'form-select fw-bold border-2 rounded-4'}),
        required=True,
        label="Account Role"
    )

    class Meta:
        model = User
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control fw-bold border-2 rounded-4'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            if hasattr(user, 'profile'):
                profile = user.profile
                profile.user_type = self.cleaned_data.get('user_type')
                profile.save()
        return user

# --- 5. PAYOUT FORM ---
class PayoutRequestForm(forms.ModelForm):
    class Meta:
        model = PayoutRequest
        fields = ['amount', 'bank_name', 'account_number', 'account_name']

    def __init__(self, *args, **kwargs):
        self.user_balance = kwargs.pop('user_balance', 0)
        super().__init__(*args, **kwargs)
        self.fields['bank_name'].widget = forms.Select(choices=Profile.BANK_CHOICES)
        
        for field in self.fields:
            css_class = 'form-select' if isinstance(self.fields[field].widget, forms.Select) else 'form-control'
            self.fields[field].widget.attrs.update({'class': f'{css_class} fw-bold border-2 rounded-4'})

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount > self.user_balance:
            raise forms.ValidationError(f"INSUFFICIENT BALANCE. YOU HAVE ₦{self.user_balance}.")
        return amount

# --- 6. IDENTITY VERIFICATION FORM (UPDATED FOR NIN-ONLY) ---
class AdvertiserVerificationForm(forms.ModelForm):
    class Meta:
        model = AdvertiserVerification
        fields = [
            'business_name', 
            'nin_number', 
            'proof_of_identity'
        ]
        widgets = {
            'business_name': forms.TextInput(attrs={'placeholder': 'Legal Business or Store Name'}),
            'nin_number': forms.TextInput(attrs={'placeholder': '11-Digit National Identification Number', 'maxlength': '11'}),
            'proof_of_identity': forms.FileInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control fw-bold border-2 rounded-4 p-3'
            })

    def clean_nin_number(self):
        nin = self.cleaned_data.get('nin_number')
        if nin and (not nin.isdigit() or len(nin) != 11):
            raise forms.ValidationError("NIN MUST BE EXACTLY 11 DIGITS.")
        return nin