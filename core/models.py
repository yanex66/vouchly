from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
import os
import uuid
import random

# Helper function for secure file naming
def secure_verification_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join(f'secure_vault/user_{instance.user.id}/verification/', filename)

# --- 1. CATEGORIES & ITEMS ---
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.CASCADE)
    icon = models.ImageField(upload_to='category_icons/', blank=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Item(models.Model):
    category = models.ForeignKey(Category, related_name='items', on_delete=models.CASCADE)
    owner = models.ForeignKey(User, related_name='claimed_items', on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    commission_naira = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # --- HYBRID ESCROW LOGIC ---
    is_escrow_required = models.BooleanField(default=True, help_text="Uncheck for Admin/Agency items that don't need internal payment.")
    external_url = models.URLField(blank=True, null=True, help_text="Direct link for Agency items (e.g. Travelstart)")
    
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    image = models.ImageField(upload_to='item_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    is_featured = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        type_label = "ESCROW" if self.is_escrow_required else "DIRECT"
        return f"[{type_label}] {self.name}"

# --- 2. SUBSCRIPTIONS ---
class PromotionPlan(models.Model):
    seller = models.ForeignKey(User, related_name='promotions', on_delete=models.CASCADE)
    product_name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    product_image = models.ImageField(upload_to='promotion_requests/')
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    destination_type = models.CharField(max_length=10, choices=[('whatsapp', 'WhatsApp'), ('website', 'Website')], default='whatsapp')
    website_url = models.URLField(blank=True, null=True)
    agree_to_commissions = models.BooleanField(default=False)
    product_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    commission_percentage = models.PositiveIntegerField(default=0)
    duration_days = models.IntegerField() 
    is_paid = models.BooleanField(default=False)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    subscription_expiry = models.DateTimeField(null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

# --- 3. REVIEWS & REFERRALS ---
class Review(models.Model):
    item = models.ForeignKey(Item, related_name='reviews', on_delete=models.CASCADE)
    author = models.ForeignKey(User, related_name='reviews', on_delete=models.CASCADE)
    rating = models.IntegerField()
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        unique_together = ('item', 'author')

class ProductReferral(models.Model):
    referrer = models.ForeignKey(User, related_name='product_referrals', on_delete=models.CASCADE)
    item = models.ForeignKey(Item, related_name='referral_clicks', on_delete=models.CASCADE)
    clicks = models.PositiveIntegerField(default=0)
    last_click = models.DateTimeField(auto_now=True)

# --- 4. USER PROFILES, WALLET & VERIFICATION ---
class Profile(models.Model):
    USER_TYPES = [
        ('MARKETER', 'Marketer'), 
        ('ADVERTISER', 'Advertiser'),
        ('BUYER', 'Buyer')
    ]
    
    VERIFICATION_STATUS = [
        ('UNVERIFIED', 'Unverified'),
        ('PENDING', 'Pending Review'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected'),
    ]

    BANK_CHOICES = [
        ('', 'Select Bank'),
        ('044', 'Access Bank'),
        ('050', 'Ecobank'),
        ('070', 'Fidelity Bank'),
        ('011', 'First Bank of Nigeria'),
        ('214', 'First City Monument Bank (FCMB)'),
        ('058', 'Guaranty Trust Bank (GTB)'),
        ('030', 'Heritage Bank'),
        ('082', 'Keystone Bank'),
        ('50211', 'Kuda Bank'),
        ('50515', 'Moniepoint MFB'),
        ('999992', 'OPay'),
        ('999991', 'PalmPay'),
        ('076', 'Polaris Bank'),
        ('221', 'Stanbic IBTC Bank'),
        ('068', 'Standard Chartered Bank'),
        ('232', 'Sterling Bank'),
        ('032', 'Union Bank of Nigeria'),
        ('033', 'United Bank for Africa (UBA)'),
        ('035', 'Wema Bank'),
        ('057', 'Zenith Bank'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='MARKETER')
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='UNVERIFIED')
    image = models.ImageField(default='default.jpg', upload_to='profile_pics')
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Seller Contact Info")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    token_rewards = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    bank_name = models.CharField(max_length=100, choices=BANK_CHOICES, null=True, blank=True)
    account_number = models.CharField(max_length=10, null=True, blank=True)
    account_name = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.verification_status})"

class AdvertiserVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='verification_docs')
    business_name = models.CharField(max_length=255)
    
    # Updated NIN fields
    nin_number = models.CharField(max_length=11, help_text="11-digit National Identification Number")
    full_name = models.CharField(max_length=255, blank=True) 
    residential_address = models.TextField(blank=True)
    
    proof_of_identity = models.FileField(upload_to=secure_verification_path, help_text="Upload NIN slip or Card image")
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"NIN Verification: {self.business_name}"

# --- 5. SYSTEM SETTINGS ---
class SubscriptionPrice(models.Model):
    plan_name = models.CharField(max_length=50)
    duration_days = models.IntegerField(unique=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.plan_name} ({self.duration_days} Days)"

# --- 6. MARKETPLACE & ESCROW ORDERS ---
class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Waiting for Payment'),
        ('PAID', 'Paid - Funds Held in Escrow'), 
        ('SHIPPED', 'In Transit'),
        ('COMPLETED', 'Delivered & Funds Released'),
        ('REFUNDED', 'Refunded to Buyer'),
        ('CANCELLED', 'Cancelled'),
    ]

    item = models.ForeignKey(Item, related_name='orders', on_delete=models.CASCADE)
    buyer = models.ForeignKey(User, related_name='purchases', on_delete=models.CASCADE)
    seller = models.ForeignKey(User, related_name='sales', on_delete=models.CASCADE)
    referrer = models.ForeignKey(User, related_name='referred_orders', on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    commission_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    delivery_pin = models.CharField(max_length=4, blank=True)
    is_delivered = models.BooleanField(default=False)
    payment_reference = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    refund_deadline = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.delivery_pin:
            self.delivery_pin = str(random.randint(1000, 9999))
        if not self.refund_deadline:
            base_time = self.created_at if self.created_at else timezone.now()
            self.refund_deadline = base_time + timedelta(hours=48)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.id} - {self.item.name}"

# --- 7. OTHERS & SIGNALS ---
class Referral(models.Model):
    referrer = models.ForeignKey(User, related_name='referrals_made', on_delete=models.CASCADE)
    referred_user = models.OneToOneField(User, related_name='referred_by', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class PayoutRequest(models.Model):
    user = models.ForeignKey(User, related_name='payouts', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2) 
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    account_number = models.CharField(max_length=10, null=True, blank=True)
    account_name = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    is_from_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

@receiver(post_save, sender=User)
def manage_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)
    if hasattr(instance, 'profile'):
        instance.profile.save()

# --- 8. SYSTEM UTILS ---
class FAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return self.question