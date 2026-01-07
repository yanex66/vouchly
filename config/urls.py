from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

# Import all custom views
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
    edit_profile,
    buy_item,
    request_payout,
    about, 
    contact, 
    privacy, 
    terms
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    
    # --- Google & Allauth Authentication URLs ---
    # This include provides the callback and login logic for Google
    path('accounts/', include('allauth.urls')),
    
    # --- Custom Authentication URLs ---
    path('register/', register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='core/logout.html'), name='logout'),
    
    # --- Password Change ---
    path('settings/password/', auth_views.PasswordChangeView.as_view(
        template_name='core/change_password.html',
        success_url='/dashboard/'
    ), name='password_change'),
    
    # Redirects any default allauth profile hits to your custom dashboard
    path('accounts/profile/', lambda request: redirect('dashboard')),

    # --- Feature URLs ---
    path('search/', search, name='search'),
    path('dashboard/', user_dashboard, name='dashboard'),
    path('referrals/', referrals_page, name='referrals'),
    path('redeem/', redeem_tokens, name='redeem_tokens'), 
    path('categories/', category_list, name='category_list'),
    path('category/<slug:slug>/', category_detail, name='category_detail'),
    path('item/<slug:slug>/', item_detail, name='item_detail'),
    path('item/<slug:slug>/add-review/', add_review, name='add_review'),
    path('review/delete/<int:review_id>/', delete_review, name='delete_review'),
    path('profile/edit/', edit_profile, name='edit_profile'),
    path('payout/request/', request_payout, name='request_payout'), 
    path('buy/<slug:slug>/', buy_item, name='buy_item'),
    
    # --- Static Pages ---
    path('about/', about, name='about'),
    path('contact/', contact, name='contact'),
    path('privacy/', privacy, name='privacy'),
    path('terms/', terms, name='terms'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)