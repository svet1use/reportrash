from .settings import *
import os
import dj_database_url

DEBUG = False

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-barangay-waste-secret-key-change-in-production-2024')

ALLOWED_HOSTS = ['*', '.onrender.com', 'localhost', '127.0.0.1']

CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
]

# Add whitenoise for static files
INSTALLED_APPS = ['whitenoise.runserver_nostatic'] + INSTALLED_APPS
MIDDLEWARE = ['whitenoise.middleware.WhiteNoiseMiddleware'] + MIDDLEWARE

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Use PostgreSQL on Render
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(conn_max_age=600, ssl_require=True)
    }

# Security settings for production
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Get API keys from environment (with fallback to default)
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', GROQ_API_KEY)
HIVE_AI_API_KEY = os.environ.get('HIVE_AI_API_KEY', HIVE_AI_API_KEY)