from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.http import HttpResponseRedirect
from datetime import timedelta
from .models import (
    Category, Item, Review, Profile, Referral, 
    PayoutRequest, PromotionPlan, ProductReferral, ChatMessage,
    AdvertiserVerification, SubscriptionPrice, Order  # Added Order here
)

# --- INLINE SETTINGS ---
class ItemInline(admin.TabularInline):
    model = Item
    extra = 1 
    fields = ('name', 'price', 'commission_naira', 'is_featured', 'image')
    show_change_link = True 

# --- 1. CATEGORY & ITEM ADMIN ---
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ItemInline]

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'commission_naira', 'category', 'is_escrow_required', 'is_featured', 'created_at')
    list_filter = ('category', 'is_featured', 'is_escrow_required')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        (None, {'fields': ('category', 'owner', 'name', 'slug', 'description')}),
        ('Pricing & Commission', {'fields': ('price', 'commission_naira')}),
        ('Media & Links', {'fields': ('image', 'external_url', 'whatsapp_number')}), # FIXED: 'external_url'
        ('Advanced Control', {'fields': ('is_escrow_required', 'is_featured'), 'classes': ('collapse',)}),
    )

# --- 2. ORDER & ESCROW MANAGEMENT ---
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'item', 'buyer', 'seller', 'amount', 'status', 'delivery_pin', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('payment_reference', 'delivery_pin', 'buyer__username', 'seller__username')
    readonly_fields = ('delivery_pin', 'payment_reference', 'created_at')
    list_editable = ('status',) # Allows quick status updates from the list view

# --- 3. SELLER PROMOTION ADMIN (DYNAMIC) ---
@admin.register(PromotionPlan)
class PromotionPlanAdmin(admin.ModelAdmin):
    list_display = (
        'product_name', 'seller', 'duration_days', 'is_paid', 'is_approved', 
        'calculated_reward', 'revenue_display'
    )
    list_filter = ('is_paid', 'is_approved', 'duration_days')
    search_fields = ('product_name', 'seller__username')
    list_editable = ('duration_days', 'is_paid', 'is_approved')
    actions = ['approve_promotions']

    def save_model(self, request, obj, form, change):
        if change and 'duration_days' in form.changed_data:
            obj.subscription_expiry = timezone.now() + timedelta(days=obj.duration_days)
            messages.info(request, f"Plan changed: Expiry updated for {obj.product_name}.")
        super().save_model(request, obj, form, change)

    def calculated_reward(self, obj):
        reward = (obj.product_price * obj.commission_percentage) / 100
        reward_str = "{:,.2f}".format(reward)
        return format_html('<span style="color: #d32f2f; font-weight: bold;">₦{}</span>', reward_str)
    calculated_reward.short_description = "Marketer Reward"

    def revenue_display(self, obj):
        price_setting = SubscriptionPrice.objects.filter(duration_days=obj.duration_days).first()
        amount = price_setting.price if price_setting else 0
        amount_str = "{:,.2f}".format(amount)
        return format_html('<span style="color: #2e7d32; font-weight: bold;">₦{}</span>', amount_str)
    revenue_display.short_description = "Sub Revenue"

    @admin.action(description="Approve and activate selected promotions")
    def approve_promotions(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, "Selected promotions are now approved and active.")

# --- 4. SYSTEM SETTINGS ---
@admin.register(SubscriptionPrice)
class SubscriptionPriceAdmin(admin.ModelAdmin):
    list_display = ('plan_name', 'duration_days', 'price', 'formatted_price') 
    list_editable = ('price',)

    def formatted_price(self, obj):
        return "₦{:,.2f}".format(obj.price)
    formatted_price.short_description = "Current Display Price"

# --- 5. IDENTITY & PROFILE ADMIN ---
@admin.register(AdvertiserVerification)
class AdvertiserVerificationAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'user', 'view_identity', 'view_address', 'verification_actions', 'submitted_at')
    readonly_fields = ('view_identity_large', 'view_address_large', 'submitted_at')

    def verification_actions(self, obj):
        status = obj.user.profile.verification_status
        if status == 'VERIFIED':
            return mark_safe('<span style="color: #16a34a; font-weight: 800;">✅ VERIFIED</span>')
        
        approve_url = f"approve/{obj.id}/"
        reject_url = f"reject/{obj.id}/"
        
        return format_html(
            '<a class="button" style="background: #16a34a; color: white; padding: 4px 10px; border-radius: 6px; font-weight: 700; margin-right: 5px; text-decoration: none;" href="{}">APPROVE</a>'
            '<a class="button" style="background: #dc2626; color: white; padding: 4px 10px; border-radius: 6px; font-weight: 700; text-decoration: none;" href="{}">REJECT</a>',
            approve_url, reject_url
        )
    verification_actions.short_description = "Quick Actions"

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('approve/<int:pk>/', self.admin_site.admin_view(self.approve_now), name='approve-verification'),
            path('reject/<int:pk>/', self.admin_site.admin_view(self.reject_now), name='reject-verification'),
        ]
        return custom_urls + urls

    def approve_now(self, request, pk):
        verify_obj = self.get_object(request, pk)
        profile = verify_obj.user.profile
        profile.verification_status = 'VERIFIED'
        profile.save()
        self.message_user(request, f"{verify_obj.business_name} verified!", messages.SUCCESS)
        return HttpResponseRedirect("../../")

    def reject_now(self, request, pk):
        verify_obj = self.get_object(request, pk)
        profile = verify_obj.user.profile
        profile.verification_status = 'REJECTED'
        profile.save()
        self.message_user(request, f"Rejected: {verify_obj.business_name}.", messages.WARNING)
        return HttpResponseRedirect("../../")

    def view_identity(self, obj):
        if obj.proof_of_identity:
            return format_html('<a href="{}" target="_blank">📄 NIN</a>', obj.proof_of_identity.url)
        return "No File"
    
    def view_address(self, obj):
        if obj.proof_of_address:
            return format_html('<a href="{}" target="_blank">📄 Address</a>', obj.proof_of_address.url)
        return "No File"

    def view_identity_large(self, obj):
        if obj.proof_of_identity:
            return format_html('<img src="{}" style="max-width: 500px; border-radius: 10px;" />', obj.proof_of_identity.url)
        return "No Image"
    
    def view_address_large(self, obj):
        if obj.proof_of_address:
            return format_html('<img src="{}" style="max-width: 500px; border-radius: 10px;" />', obj.proof_of_address.url)
        return "No Image"

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type', 'verification_status', 'formatted_balance')
    list_filter = ('user_type', 'verification_status')
    list_editable = ('verification_status',)

    def formatted_balance(self, obj): 
        return "₦{:,.2f}".format(obj.balance)
    formatted_balance.short_description = 'Wallet'

# --- 6. REVENUE & TRACKING ADMIN ---
@admin.register(ProductReferral)
class ProductReferralAdmin(admin.ModelAdmin):
    list_display = ('referrer', 'item', 'clicks', 'last_click')

@admin.register(PayoutRequest)
class PayoutRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount_display', 'bank_name', 'status', 'created_at')
    list_filter = ('status',)
    list_editable = ('status',)

    def amount_display(self, obj):
        return "₦{:,.2f}".format(obj.amount)
    amount_display.short_description = 'Amount'

# --- 7. OTHERS ---
admin.site.register(Referral)
admin.site.register(Review)
admin.site.register(ChatMessage)