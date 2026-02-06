from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

# Import all custom views explicitly from core.views
# Removed "from . import views" to fix the ImportError
from core.views import (
    home, 
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
    payment_success,
    ad_analytics,
    about, 
    contact, 
    privacy, 
    terms,
    verify_identity
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    
    # --- Google & Allauth Authentication URLs ---
    path('accounts/', include('allauth.urls')),
    
    # --- Custom Authentication URLs ---
    path('register/', register, name='register'),
    path('set-role-session/', set_role_session, name='set_role_session'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='core/logout.html'), name='logout'),
    
    # --- Password Change ---
    path('settings/password/', auth_views.PasswordChangeView.as_view(
        template_name='core/change_password.html',
        success_url='/dashboard/'
    ), name='password_change'),
    
    path('accounts/profile/', lambda request: redirect('dashboard')),

    # --- Feature URLs ---
    path('search/', search, name='search'),
    path('dashboard/', user_dashboard, name='dashboard'),
    path('referrals/', referrals_page, name='referrals_page'), 
    path('redeem/', redeem_tokens, name='redeem_tokens'), 
    path('categories/', category_list, name='category_list'),
    path('category/<slug:slug>/', category_detail, name='category_detail'),
    path('item/<slug:slug>/', item_detail, name='item_detail'),
    path('item/<slug:slug>/add-review/', add_review, name='add_review'),
    path('review/delete/<int:review_id>/', delete_review, name='delete_review'),
    path('profile/edit/', edit_profile, name='edit_profile'),
    path('payout/request/', request_payout, name='request_payout'), 
    
    # --- Bank Verification ---
    path('verify-bank/', verify_bank_account, name='verify_bank_account'), 

    # --- Identity Verification ---
    path('verify-identity/', verify_identity, name='verify_identity'),

    # --- Seller Promotion & Subscription URLs ---
    path('promote/request/', promote_request, name='promote_request'),
    path('promote/payment/<int:pk>/', promotion_payment, name='promotion_payment'),
    
    # FIXED: This matches the name "{% url 'verify_promotion_payment' %}" in your template
    path('promote/verify/', verify_promotion_payment, name='verify_promotion_payment'),
    
    path('promote/success/<int:pk>/', payment_success, name='payment_success'),
    path('promote/analytics/', ad_analytics, name='ad_analytics'),
    
    # --- Affiliate Tracking URL ---
    path('buy/<slug:slug>/', buy_item, name='buy_item'),

    # --- Static Pages ---
    path('about/', about, name='about'),
    path('contact/', contact, name='contact'),
    path('privacy/', privacy, name='privacy'),
    path('terms/', terms, name='terms'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)