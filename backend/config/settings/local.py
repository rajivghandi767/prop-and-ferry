from .base import *
import os
from config.utils import is_service_available

# ============================================================================
# DEVELOPMENT SETTINGS
# ============================================================================
DEBUG = True
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-development-key-fallback')
ALLOWED_HOSTS = os.getenv(
    'ALLOWED_HOSTS', 'localhost,127.0.0.1,prop-ferry-backend').split(',')

# ============================================================================
# DEVELOPMENT-SPECIFIC APPS AND MIDDLEWARE
# ============================================================================
INSTALLED_APPS += ['corsheaders']
MIDDLEWARE.insert(2, 'corsheaders.middleware.CorsMiddleware')

# ============================================================================
# CORS SETTINGS FOR DEVELOPMENT
# ============================================================================
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4000",
    "http://127.0.0.1:4000",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False

# ============================================================================
# CSRF SETTINGS FOR DEVELOPMENT
# ============================================================================
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4000",
    "http://127.0.0.1:4000",
]

CSRF_COOKIE_SECURE = False
CSRF_USE_SESSIONS = False

# ============================================================================
# SESSION SETTINGS FOR DEVELOPMENT
# ============================================================================
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_HTTPONLY = True

# ============================================================================
# DATABASE FOR DEVELOPMENT
# ============================================================================
POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_PORT = os.getenv('POSTGRES_PORT')

if is_service_available(POSTGRES_HOST, POSTGRES_PORT):
    print(f"✅ Connected to Postgres at {POSTGRES_HOST}:{POSTGRES_PORT}")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB'),
            'USER': os.getenv('POSTGRES_USER'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
            'HOST': POSTGRES_HOST,
            'PORT': POSTGRES_PORT,
        }
    }
else:
    print("⚠️ Postgres unreachable. Falling back to SQLite.")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ============================================================================
# STATIC & MEDIA FILES FOR DEVELOPMENT
# ============================================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'

# ============================================================================
# NOTIFICATION SETTINGS FOR DEVELOPMENT
# ============================================================================
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

# ============================================================================
# DEVELOPMENT LOGGING
# ============================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'contacts': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ============================================================================
# SECURITY SETTINGS FOR DEVELOPMENT
# ============================================================================
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# ============================================================================
# REST FRAMEWORK DEVELOPMENT SETTINGS
# ============================================================================
REST_FRAMEWORK.update({
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],

    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {},
})

# ============================================================================
# AMADEUS SETTINGS FOR DEVELOPMENT
# ============================================================================
AMADEUS_API_KEY = os.getenv('AMADEUS_API_KEY')
AMADEUS_API_SECRET = os.getenv('AMADEUS_API_SECRET')
