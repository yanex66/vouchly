from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

# Import all your custom views
from core.views import (
    home, 
    item_detail, 
    add_review, 
    search, 
    user_dashboard, 
    delete_review, 
    category_list, 
    category_detail, 
    register,
    edit_profile,
    buy_item,
    request_payout,
    about,   # <--- Added
    contact, # <--- Added
    privacy, # <--- Added
    terms    # <--- Added
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    
    # --- Authentication URLs ---
    path('register/', register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='core/logout.html'), name='logout'),
    
    # FIX for "Page not found /accounts/profile/" error
    path('accounts/profile/', lambda request: redirect('dashboard')),

    # --- Feature URLs ---
    path('search/', search, name='search'),
    path('dashboard/', user_dashboard, name='dashboard'),
    path('categories/', category_list, name='category_list'),
    path('category/<slug:slug>/', category_detail, name='category_detail'),
    path('item/<slug:slug>/', item_detail, name='item_detail'),
    path('item/<slug:slug>/add-review/', add_review, name='add_review'),
    path('review/delete/<int:review_id>/', delete_review, name='delete_review'),
    path('profile/edit/', edit_profile, name='edit_profile'),
    path('payout/request/', request_payout, name='request_payout'),
    path('buy/<slug:slug>/', buy_item, name='buy_item'),

    # --- Static Pages (Fixes the NoReverseMatch Error) ---
    path('about/', about, name='about'),
    path('contact/', contact, name='contact'),
    path('privacy/', privacy, name='privacy'),
    path('terms/', terms, name='terms'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)