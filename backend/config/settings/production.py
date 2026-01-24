from .base import *
import os
from dotenv import load_dotenv

# ============================================================================
# LOAD ENV VARIABLES
# ============================================================================
env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# ============================================================================
# PRODUCTION SECURITY SETTINGS
# ============================================================================
DEBUG = False
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# ============================================================================
# CSRF SETTINGS FOR PRODUCTION
# ============================================================================
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.getenv(
    'CSRF_TRUSTED_ORIGINS', '').split(',') if origin.strip()]
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'

# ============================================================================
# SESSION CONFIGURATION
# ============================================================================
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# ============================================================================
# HTTPS SECURITY SETTINGS (Adjusted for NPM/Cloudflare)
# ============================================================================
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ============================================================================
# STATIC & MEDIA FILES FOR PRODUCTION
# ============================================================================
STATIC_URL = '/static/'
STATIC_ROOT = '/home/backend/django/staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = '/home/backend/django/mediafiles'

# Ensure directories exist
os.makedirs(MEDIA_ROOT, exist_ok=True)
os.makedirs(STATIC_ROOT, exist_ok=True)

# ============================================================================
# DATABASE CONFIGURATION FOR PRODUCTION
# ============================================================================
DATABASES = {
    'default': {
        'ENGINE': 'django_prometheus.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB'),
        'USER': os.getenv('POSTGRES_USER'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'HOST': os.getenv('POSTGRES_HOST'),
        'PORT': os.getenv('POSTGRES_PORT'),
        'OPTIONS': {
            'connect_timeout': 30,
            'sslmode': 'prefer',
        },
        'CONN_MAX_AGE': 60,
    }
}
# ============================================================================
# FILE UPLOAD SETTINGS
# ============================================================================
# Increased to handle 5MB files + Django overhead
FILE_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024  # 6MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024  # 6MB
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# ============================================================================
# ENHANCED LOGGING CONFIGURATION
# ============================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/home/backend/django/logs/prop-ferry.log',
            'formatter': 'simple',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/home/backend/django/logs/errors.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
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
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file', 'console'],
            'level': 'ERROR',
            'propagate': False,
        }
    },
}

# ============================================================================
# REST FRAMEWORK SETTINGS FOR PRODUCTION
# ============================================================================
REST_FRAMEWORK.update({
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'contact': '20/hour',
    },

    'DEFAULT_PAGINATION_CLASS': None,
})

# ============================================================================
# OPTIONAL SETTINGS
# ============================================================================
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
ADMIN_URL = os.getenv('ADMIN_URL')
HEALTH_CHECK_ENABLED = True

# ============================================================================
# PROMETHEUS MONITORING CONFIGURATION
# ============================================================================
PROMETHEUS_EXPORT_MIGRATIONS = False
PROMETHEUS_LATENCY_BUCKETS = (
    0.008, 0.016, 0.032, 0.064, 0.128, 0.256, 0.512, 1.024, 2.048, 4.096, 8.192, 16.384, float(
        'inf')
)
