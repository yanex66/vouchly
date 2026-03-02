from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from core.views import flyer_view

# IMPORT ALLAUTH LOGIN VIEW
from allauth.account.views import LoginView

# Import all custom views explicitly from core.views
from core.views import (
    home, 
    marketplace,
    item_detail, 
    add_review, 
    search, 
    user_dashboard, 
    referrals_page,
    redeem_tokens, 
    delete_review, 
    category_list, 
    category_detail, 
    register,
    set_role_session,
    edit_profile,
    verify_bank_account,
    buy_item,
    request_payout,
    promote_request,
    promotion_payment,
    verify_promotion_payment,
    ad_analytics,
    about, 
    contact, 
    privacy, 
    terms,
    verify_identity,
    product_checkout,
    verify_product_payment,
    verify_delivery, 
    mark_as_shipped, 
    checkout_desk,
    bulk_add_categories,
    request_refund, 
    cancel_order,
    delete_product, # NEW: Added Advertiser Delete View
    logout_user     # NEW: Added Custom Logout View
)

urlpatterns = [
    # --- Administrative Tools ---
    path('admin/', admin.site.urls),
    path('run-bulk-categories/', bulk_add_categories, name='bulk_add_categories'),

    # --- Home & Search ---
    path('', home, name='home'),
    path('search/', search, name='search'),

    # --- Authentication & Identity ---
    path('accounts/', include('allauth.urls')),
    path('register/', register, name='register'),
    
    # Using LoginView to support email-only login via allauth configuration
    path('login/', LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', logout_user, name='logout'), # UPDATED: Pointing to custom logout view
    
    path('set-role-session/', set_role_session, name='set_role_session'),
    path('accounts/profile/', lambda request: redirect('dashboard')),
    
    # --- Password Management ---
    path('settings/password/', auth_views.PasswordChangeView.as_view(
        template_name='core/change_password.html',
        success_url='/profile/edit/'
    ), name='change_password'),
    
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='core/password_reset.html',
        subject_template_name='core/emails/password_reset_subject.txt',
        email_template_name='core/emails/password_reset_email.html',
        success_url='/password-reset/done/'
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='core/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='core/password_reset_confirm.html',
        success_url='/password-reset-complete/'
    ), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='core/password_reset_complete.html'
    ), name='password_reset_complete'),

    # --- Profile & Banking ---
    path('profile/edit/', edit_profile, name='edit_profile'),
    path('payout/request/', request_payout, name='request_payout'), 
    path('verify-bank-account/', verify_bank_account, name='verify_bank_account'), 
    path('verify-identity/', verify_identity, name='verify_identity'),

    # --- Marketplace & Browsing ---
    path('marketplace/', marketplace, name='marketplace'), 
    path('categories/', category_list, name='category_list'),
    path('category/<slug:slug>/', category_detail, name='category_detail'),
    path('item/<slug:slug>/', item_detail, name='item_detail'),
    
    # --- Dashboards & Rewards ---
    path('dashboard/', user_dashboard, name='dashboard'),
    path('referrals/', referrals_page, name='referrals_page'), 
    path('redeem/', redeem_tokens, name='redeem_tokens'), 

    # --- Escrow Orders & Payout Flow ---
    path('checkout-desk/', checkout_desk, name='checkout_desk'),
    path('checkout/<slug:slug>/', product_checkout, name='product_checkout'),
    path('checkout/verify-payment/', verify_product_payment, name='verify_product_payment'),
    
    # --- Shipping & PIN Verification ---
    path('order/mark-shipped/<int:order_id>/', mark_as_shipped, name='mark_shipped'),
    path('verify-delivery/<int:order_id>/', verify_delivery, name='verify_delivery'),
    path('order/refund/<int:order_id>/', request_refund, name='request_refund'), 
    path('order/cancel/<int:order_id>/', cancel_order, name='cancel_order'),

    # --- Advertiser Product Listing ---
    path('promote/request/', promote_request, name='promote_request'),
    path('promote/payment/<int:pk>/', promotion_payment, name='promotion_payment'),
    path('promote/verify/', verify_promotion_payment, name='verify_promotion_payment'),
    path('promote/analytics/', ad_analytics, name='ad_analytics'),
    path('product/<slug:slug>/delete/', delete_product, name='delete_product'), # NEW: Route to delete product
    
    # --- Marketer Affiliate Redirect ---
    path('buy/<slug:slug>/', buy_item, name='buy_item'),

    # --- Social & Reviews ---
    path('item/<slug:slug>/add-review/', add_review, name='add_review'),
    path('review/delete/<int:review_id>/', delete_review, name='delete_review'),

    # --- Information Pages ---
    path('about/', about, name='about'),
    path('contact/', contact, name='contact'),
    path('privacy/', privacy, name='privacy'),
    path('terms/', terms, name='terms'),


path('flyer/', flyer_view, name='flyer'),]

# --- CRITICAL: MEDIA & STATIC SERVING ---
# This block allows Django to serve uploaded images (media) during development.
# If this is missing, images will appear to "vanish" after being saved.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)