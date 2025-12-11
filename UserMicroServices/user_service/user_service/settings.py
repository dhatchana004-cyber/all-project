"""
Django settings for user_service project.
"""

import os
from pathlib import Path
import environ

# -----------------------------
# BASE DIRECTORY
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------
# ENVIRONMENT VARIABLES
# -----------------------------
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY', default='django-insecure-default-key')
DEBUG = True

# -----------------------------
# ALLOWED HOSTS
# -----------------------------
ALLOWED_HOSTS = [
    'konstruct.world',
    '.konstruct.world',
    '101.53.133.132',
    'localhost',
    '127.0.0.1',
    '192.168.1.28',
    '192.168.1.11',
    '192.168.1.12',
    '192.168.1.30',
    '192.168.16.214',
    '192.168.23.214',
    '192.168.29.168',
    '192.168.29.171',
    '192.168.29.239',
    '192.168.29.63',
    '192.168.29.79',
    '192.168.78.214',
    '192.168.78.48',
    '192.168.0.200',
    '192.168.0.201',
    '192.168.0.203',
    '192.168.0.204',
    '*'
]

# -----------------------------
# APPLICATIONS
# -----------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # 3rd Party
    'rest_framework',
    'corsheaders',

    # Local Apps
    'accounts',
]

# -----------------------------
# MIDDLEWARE
# -----------------------------
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# -----------------------------
# CORS SETTINGS
# -----------------------------
local = "192.168.29.79"
CORS_ALLOWED_ORIGINS = [
    f"http://{local}:8000",
    f"http://{local}:8001",
    f"http://{local}:8002",
    f"http://{local}:8003",
    "http://localhost:3000",
    "https://konstruct.world",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8001",
    "http://127.0.0.1:8002",
    "http://127.0.0.1:8003",
]

# -----------------------------
# AUTHENTICATION
# -----------------------------
AUTH_USER_MODEL = 'accounts.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

# -----------------------------
# URLS & WSGI
# -----------------------------
ROOT_URLCONF = 'user_service.urls'
WSGI_APPLICATION = 'user_service.wsgi.application'

# -----------------------------
# TEMPLATES
# -----------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# -----------------------------
# DATABASE
# -----------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
        'timeout': 20,  # Wait up to 20 seconds before giving up on a locked database
}

    }
    
}

# -----------------------------
# PASSWORD VALIDATION
# -----------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# -----------------------------
# LANGUAGE & TIME
# -----------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# -----------------------------
# STATIC & MEDIA
# -----------------------------
STATIC_URL = '/users/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# -----------------------------
# EMAIL CONFIGURATION
# -----------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'vasisayed09421@gmail.com'
EMAIL_HOST_PASSWORD = 'txjx rdgj arvc gtkh'

# -----------------------------
# OTHER SETTINGS
# -----------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
APPEND_SLASH = False