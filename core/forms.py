from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import (
    Review, Profile, PayoutRequest, Category, 
    PromotionPlan, AdvertiserVerification, SubscriptionPrice
)

# --- 1. SELLER PROMOTION FORM ---
class PromotionRequestForm(forms.ModelForm):
    # Added Website URL for website owners
    website_url = forms.URLField(
        required=False, 
        label="WEBSITE LINK (IF NOT USING WHATSAPP)",
        widget=forms.URLInput(attrs={'placeholder': 'E.G. HTTPS://YOURSTORE.COM/PRODUCT'})
    )
    
    # FIXED: Defined as ChoiceField to fix the "tiny box" issue
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
            'duration_days'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'DESCRIBE YOUR PRODUCT...'}),
            'product_name': forms.TextInput(attrs={'placeholder': 'E.G. WIRELESS NOISE-CANCELLING HEADPHONES'}),
            'product_price': forms.NumberInput(attrs={'placeholder': 'E.G. 50000.00', 'min': '0'}),
            # FIXED: Hard-enforced value='0' and autocomplete='off'
            'commission_percentage': forms.NumberInput(attrs={
                'placeholder': '0', 
                'min': '0', 
                'max': '100', 
                'value': '0',
                'autocomplete': 'off'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # FIXED: Hard-set initial commission value to 0
        if not self.instance.pk:
            self.initial['commission_percentage'] = 0

        # --- DYNAMIC PLAN LOOKUP ---
        plans = SubscriptionPrice.objects.all().order_by('duration_days')
        if plans.exists():
            self.fields['duration_days'].choices = [
                (p.duration_days, f"{p.plan_name} (₦{p.price:,.0f})") for p in plans
            ]
        
        # Apply premium styling to all fields
        for field in self.fields:
            if field != 'agree_to_commissions':
                current_widget = self.fields[field].widget
                css_class = 'form-select' if isinstance(current_widget, forms.Select) else 'form-control'
                current_widget.attrs.update({'class': f'{css_class} fw-bold border-2 rounded-4'})

# --- 2. PROFILE UPDATE FORM ---
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image', 'whatsapp_number', 'bank_name', 'account_number', 'account_name']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control fw-bold rounded-4'}),
            'whatsapp_number': forms.TextInput(attrs={'class': 'form-control fw-bold border-2 rounded-4', 'placeholder': 'E.G. 2348030000000'}),
            'bank_name': forms.Select(attrs={'class': 'form-select fw-bold border-2 rounded-4'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control fw-bold border-2 rounded-4', 'maxlength': '10'}),
            'account_name': forms.TextInput(attrs={'class': 'form-control fw-bold border-2 rounded-4'}),
        }

    def clean_whatsapp_number(self):
        number = self.cleaned_data.get('whatsapp_number')
        if number:
            clean_num = number.replace("+", "").replace(" ", "").replace("-", "")
            if not clean_num.isdigit():
                raise forms.ValidationError("WHATSAPP NUMBER MUST CONTAIN ONLY DIGITS.")
            return clean_num
        return number

# --- 3. REVIEW FORM ---
class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'title', 'content']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select fw-bold border-2 rounded-4'}),
            'title': forms.TextInput(attrs={'class': 'form-control fw-bold border-2 rounded-4'}),
            'content': forms.Textarea(attrs={'class': 'form-control fw-bold border-2 rounded-4', 'rows': 4}),
        }

# --- 4. REGISTRATION FORM ---
class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    user_type = forms.ChoiceField(choices=Profile.USER_TYPES, widget=forms.Select(attrs={'class': 'form-select fw-bold border-2 rounded-4'}))

    class Meta:
        model = User
        fields = ['username', 'email']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
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
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control fw-bold border-2 rounded-4'})

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount > self.user_balance:
            raise forms.ValidationError(f"INSUFFICIENT BALANCE. YOU HAVE ₦{self.user_balance}.")
        return amount

# --- 6. IDENTITY VERIFICATION FORM ---
class AdvertiserVerificationForm(forms.ModelForm):
    class Meta:
        model = AdvertiserVerification
        fields = [
            'business_name', 
            'full_name', 
            'contact_number', 
            'residential_address', 
            'proof_of_identity', 
            'proof_of_address'
        ]
        widgets = {
            'business_name': forms.TextInput(attrs={'placeholder': 'LEGAL BUSINESS NAME'}),
            'full_name': forms.TextInput(attrs={'placeholder': 'YOUR LEGAL FULL NAME'}),
            'contact_number': forms.TextInput(attrs={'placeholder': 'E.G. 234...'}),
            'residential_address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'FULL HOME OR OFFICE ADDRESS'}),
            'proof_of_identity': forms.FileInput(attrs={'accept': 'image/*,application/pdf'}),
            'proof_of_address': forms.FileInput(attrs={'accept': 'image/*,application/pdf'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control fw-bold border-2 rounded-4 p-3'
            })