from django.contrib import admin
from django.contrib import messages
from .models import Category, Item, Review, Profile, Referral, PayoutRequest

# --- INLINE SETTING ---
class ItemInline(admin.TabularInline):
    model = Item
    extra = 1 
    fields = ('name', 'price', 'discount_price', 'is_featured', 'image')
    show_change_link = True 

# 1. Customize Category Admin
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ItemInline]

# 2. Customize Item Admin
@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category', 'is_featured', 'created_at')
    list_filter = ('category', 'is_featured')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        (None, {
            'fields': ('category', 'owner', 'name', 'slug', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'discount_price'),
        }),
        ('Media & Links', {
            'fields': ('image', 'website', 'affiliate_link')
        }),
        ('Advanced', {
            'fields': ('specifications', 'is_featured'),
            'classes': ('collapse',),
        }),
    )

# 3. Customize Review Admin
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('item', 'author', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')

# 4. Customize Profile Admin
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'formatted_tokens', 'formatted_balance')
    search_fields = ('user__username',)
    
    def formatted_tokens(self, obj):
        return f"₦{obj.token_rewards:,.2f}"
    formatted_tokens.short_description = 'Token Rewards (Unredeemed)'

    def formatted_balance(self, obj):
        return f"₦{obj.balance:,.2f}"
    formatted_balance.short_description = 'Wallet Balance (Spendable)'

    fields = ('user', 'image', 'token_rewards', 'balance')

# 5. Customize Referral Admin
@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('referrer', 'referred_user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('referrer__username', 'referred_user__username')

# 6. Customize Payout Request Admin
@admin.register(PayoutRequest)
class PayoutRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'bank_name', 'status', 'created_at')
    list_filter = ('status', 'bank_name', 'created_at')
    search_fields = ('user__username', 'account_number', 'account_name')
    list_editable = ('status',)
    
    actions = ['mark_as_paid']

    @admin.action(description="Mark selected requests as PAID")
    def mark_as_paid(self, request, queryset):
        updated = queryset.update(status='PAID')
        self.message_user(
            request, 
            f"Successfully marked {updated} requests as PAID.", 
            messages.SUCCESS
        )

    def current_wallet_balance(self, obj):
        return f"₦{obj.user.profile.balance:,.2f}"
    current_wallet_balance.short_description = "User's Available Wallet"

    fieldsets = (
        ('Request Info', {
            'fields': ('user', 'current_wallet_balance', 'amount', 'status', 'created_at')
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'account_number', 'account_name'),
        }),
    )
    
    readonly_fields = ('current_wallet_balance', 'created_at')