import os
from pathlib import Path
import environ
import dj_database_url

# --- 1. INITIALIZATION & ENV LOAD ---
env = environ.Env(DEBUG=(bool, False))

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# FIX: Explicitly load the .env file from the root directory
env_file = BASE_DIR / '.env'

if env_file.exists():
    environ.Env.read_env(env_file)
    # Optional: Print to console to confirm it loaded (remove in production)
    print(f"✅ Loaded .env file from: {env_file}")
else:
    print(f"❌ WARNING: .env file NOT found at: {env_file}")

SECRET_KEY = env('SECRET_KEY', default='django-insecure-default-key')
DEBUG = env.bool('DEBUG', default=False) 
GEMINI_API_KEY = env('GEMINI_API_KEY', default='')

ALLOWED_HOSTS = [
    'www.vouchly.store', 
    'vouchly.store', 
    'vouchly-5w0g.onrender.com',
    'localhost', 
    '127.0.0.1'
]

CSRF_TRUSTED_ORIGINS = [
    'https://www.vouchly.store',
    'https://vouchly.store',
    'https://vouchly-5w0g.onrender.com'
]

# --- 2. APPS ---
INSTALLED_APPS = [
    'cloudinary_storage', # Must be above staticfiles
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary', 
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'django.contrib.humanize',
    'core.apps.CoreConfig',
]

SITE_ID = 1

# --- 3. MIDDLEWARE ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Essential for Render
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
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
            os.path.join(BASE_DIR, 'core', 'templates'), # Explicitly add the core templates path
        ],
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
DATABASES = {
    'default': dj_database_url.config(
        default=env('DATABASE_URL', default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# --- 6. STATIC & MEDIA ---
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.StaticFilesStorage",
    },
}

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
STATICFILES_STORAGE = 'whitenoise.storage.StaticFilesStorage'

WHITENOISE_USE_FINDERS = True

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': env('CLOUDINARY_NAME', default=''),
    'API_KEY': env('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': env('CLOUDINARY_API_SECRET', default=''),
    'SECURE': True, 
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- 7. EMAIL SETTINGS ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_PASS', default='')
DEFAULT_FROM_EMAIL = f"Vouchly <{env('EMAIL_USER', default='')}>"

# --- 8. TERMII SMS SETTINGS ---
TERMII_API_KEY = env('TERMII_API_KEY', default='')
TERMII_SENDER_ID = env('TERMII_SENDER_ID', default='Vouchly')
TERMII_BASE_URL = env('TERMII_BASE_URL', default='https://api.ng.termii.com')

# --- 9. AUTHENTICATION ---
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

# --- 10. SECURITY & PRODUCTION SETTINGS ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SECURE_VAULT_ROOT = os.path.join(BASE_DIR, 'secure_vault')

if not os.path.exists(SECURE_VAULT_ROOT):
    os.makedirs(SECURE_VAULT_ROOT)

# Production SSL Enforcement
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True # Force HTTPS
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000 # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# --- 11. PAYMENTS ---
PAYSTACK_PUBLIC_KEY = env('PAYSTACK_PUBLIC_KEY', default='')
PAYSTACK_SECRET_KEY = env('PAYSTACK_SECRET_KEY', default='')

FLUTTERWAVE_PUBLIC_KEY = env('FLUTTERWAVE_PUBLIC_KEY', default='') 
FLUTTERWAVE_SECRET_KEY = env('FLUTTERWAVE_SECRET_KEY', default='')
FLUTTERWAVE_ENCRYPTION_KEY = env('FLUTTERWAVE_ENCRYPTION_KEY', default='')

MINIMUM_WITHDRAWAL_AMOUNT = 1000

# --- 12. AFFILIATE SYSTEM SETTINGS ---
DEFAULT_AFFILIATE_COMMISSION = 10  # This represents 10%
REFERRAL_LINK_PARAM = 'ref'        # The URL part like ?ref=yanex66