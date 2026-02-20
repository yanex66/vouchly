from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

# Import all custom views explicitly from core.views
from core.views import (
    home, 
    marketplace,  # Added this
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
    confirm_receipt,
    mark_as_shipped, 
    checkout_desk,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    
    # --- NEW MARKETPLACE PATH ---
    path('marketplace/', marketplace, name='marketplace'), 
    
    # --- Authentication URLs ---
    path('accounts/', include('allauth.urls')),
    path('register/', register, name='register'),
    path('set-role-session/', set_role_session, name='set_role_session'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='core/logout.html'), name='logout'),
    
    # --- Password Management ---
    path('settings/password/', auth_views.PasswordChangeView.as_view(
        template_name='core/change_password.html',
        success_url='/dashboard/'
    ), name='password_change'),
    
    path('accounts/profile/', lambda request: redirect('dashboard')),

    # --- Marketplace & Search ---
    path('search/', search, name='search'),
    path('dashboard/', user_dashboard, name='dashboard'),
    path('referrals/', referrals_page, name='referrals_page'), 
    path('redeem/', redeem_tokens, name='redeem_tokens'), 
    path('categories/', category_list, name='category_list'),
    path('category/<slug:slug>/', category_detail, name='category_detail'),
    path('item/<slug:slug>/', item_detail, name='item_detail'),
    
    # --- Escrow Checkout & Payment ---
    path('checkout/<slug:slug>/', product_checkout, name='product_checkout'),
    path('checkout/verify-payment/', verify_product_payment, name='verify_product_payment'),
    
    # --- Delivery & PIN Verification ---
    path('order/confirm-receipt/<int:order_id>/', confirm_receipt, name='confirm_receipt'),
    path('order/mark-shipped/<int:order_id>/', mark_as_shipped, name='mark_as_shipped'),

    # --- Reviews ---
    path('item/<slug:slug>/add-review/', add_review, name='add_review'),
    path('review/delete/<int:review_id>/', delete_review, name='delete_review'),
    
    # --- User Profile & Payouts ---
    path('profile/edit/', edit_profile, name='edit_profile'),
    path('payout/request/', request_payout, name='request_payout'), 
    path('verify-bank/', verify_bank_account, name='verify_bank_account'), 
    path('verify-identity/', verify_identity, name='verify_identity'),

    # --- Advertiser Subscription URLs ---
    path('promote/request/', promote_request, name='promote_request'),
    path('promote/payment/<int:pk>/', promotion_payment, name='promotion_payment'),
    path('promote/verify/', verify_promotion_payment, name='verify_promotion_payment'),
    path('promote/analytics/', ad_analytics, name='ad_analytics'),
    
    # --- Affiliate Tracking Legacy Redirect ---
    path('buy/<slug:slug>/', buy_item, name='buy_item'),

    # --- Static Pages ---
    path('about/', about, name='about'),
    path('contact/', contact, name='contact'),
    path('privacy/', privacy, name='privacy'),
    path('terms/', terms, name='terms'),
    path('checkout-desk/', checkout_desk, name='checkout_desk'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)