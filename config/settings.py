import os
from pathlib import Path
import environ
import dj_database_url

# --- 1. INITIALIZATION & ENV LOAD ---
env = environ.Env(DEBUG=(bool, False))
BASE_DIR = Path(__file__).resolve().parent.parent

# Read .env file locally, but Render will use its dashboard variables
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False) 
GEMINI_API_KEY = env('GEMINI_API_KEY', default='')

# UPDATED: Added Render domain to prevent Bad Request (400)
ALLOWED_HOSTS = [
    'www.vouchly.store', 
    'vouchly.store', 
    'vouchly-5w0g.onrender.com',  # Your specific Render URL
    'localhost', 
    '127.0.0.1'
]

# UPDATED: Added Render domain for secure form submissions
CSRF_TRUSTED_ORIGINS = [
    'https://www.vouchly.store',
    'https://vouchly.store',
    'https://vouchly-5w0g.onrender.com'
]

# --- 2. APPS ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'core',
    'django.contrib.humanize',
]

SITE_ID = 1

# --- 3. MIDDLEWARE ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # For static files on Render
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'config.urls'

# --- 4. TEMPLATES ---
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.pending_orders_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# --- 5. DATABASE ---
# Connects to Render PostgreSQL via the DATABASE_URL environment variable
DATABASES = {
    'default': dj_database_url.config(
        default=env('DATABASE_URL', default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# --- 6. STATIC & MEDIA ---
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# WhiteNoise storage optimized for Render/Production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# --- 7. EMAIL SETTINGS ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_PASS', default='')
DEFAULT_FROM_EMAIL = f"Vouchly <{env('EMAIL_USER', default='')}>"

# --- 8. AUTHENTICATION & ALLAUTH ---
AUTHENTICATION_BACKENDS = [
    'core.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True 
ACCOUNT_EMAIL_VERIFICATION = 'none' 
SOCIALACCOUNT_ADAPTER = 'core.adapters.MySocialAccountAdapter'

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'OAUTH_PKCE_ENABLED': True,
    }
}

LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'home'
LOGIN_URL = 'login'
SOCIALACCOUNT_LOGIN_ON_GET = True
# --- 9. SECURITY & VAULT ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SECURE_VAULT_ROOT = os.path.join(BASE_DIR, 'secure_vault')

if not os.path.exists(SECURE_VAULT_ROOT):
    os.makedirs(SECURE_VAULT_ROOT)

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# --- 10. PAYMENT GATEWAY ---
PAYSTACK_PUBLIC_KEY = env('PAYSTACK_PUBLIC_KEY', default='')
PAYSTACK_SECRET_KEY = env('PAYSTACK_SECRET_KEY', default='')

FLUTTERWAVE_PUBLIC_KEY = env('FLWPUBK_TEST', default='') 
FLUTTERWAVE_SECRET_KEY = env('FLWSECK_TEST', default='')
FLUTTERWAVE_ENCRYPTION_KEY = env('FLUTTERWAVE_ENCRYPTION_KEY', default='')

MINIMUM_WITHDRAWAL_AMOUNT = 1000