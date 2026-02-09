from .default import *  # noqa


DEBUG = True

INSTALLED_APPS.extend([])  # noqa: F405


INTERNAL_IPS = [
    "127.0.0.1",
]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:5173",
]

# More permissive CSRF settings for dev
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_SAMESITE = "Lax"

# Disable CSRF for API endpoints during development
CORS_ALLOW_ALL_ORIGINS = True
# CSRF_TRUSTED_ORIGINS = ['http://localhost:5173', 'http://127.0.0.1:5173']

# # Or use django-cors-headers for better CORS handling
# INSTALLED_APPS += ['corsheaders']
# MIDDLEWARE.insert(0, 'corsheaders.middleware.CorsMiddleware')

CSRF_COOKIE_HTTPONLY = False  # Allow JS to read it in development mode
