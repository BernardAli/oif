"""Django settings for the Onesimus Impact Foundation (OIF) site."""
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # pragma: no cover
    pass

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-key-change-me-in-production-0v1f-onesimus",
)
DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("1", "true", "yes")
ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0,testserver"
)
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS.split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
    # Local apps
    "accounts",
    "pages",
    "engagement",
    "donations",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "oif_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "pages.context_processors.site_globals",
            ],
        },
    },
]

WSGI_APPLICATION = "oif_site.wsgi.application"

# --- Database -------------------------------------------------------------
# MySQL is selected when MYSQL_DATABASE is configured. DATABASE_URL remains
# supported for managed deployments; SQLite is only the credential-free local
# fallback used by tests and first-time setup.
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL:
    import dj_database_url
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
elif os.environ.get("MYSQL_DATABASE"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.environ["MYSQL_DATABASE"],
            "USER": os.environ.get("MYSQL_USER", "root"),
            "PASSWORD": os.environ.get("MYSQL_PASSWORD", ""),
            "HOST": os.environ.get("MYSQL_HOST", "127.0.0.1"),
            "PORT": os.environ.get("MYSQL_PORT", "3306"),
            "CONN_MAX_AGE": int(os.environ.get("MYSQL_CONN_MAX_AGE", "300")),
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": {
                "charset": "utf8mb4",
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
    if os.environ.get("MYSQL_TEST_DATABASE"):
        DATABASES["default"]["TEST"] = {"NAME": os.environ["MYSQL_TEST_DATABASE"]}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
# Ghana observes UTC year-round. Using UTC avoids MySQL's optional named-zone
# table dependency while preserving the exact local date and time in Accra.
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "pages:home"

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY", "")
PAYSTACK_PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY", "")
PAYSTACK_TIMEOUT_SECONDS = int(os.environ.get("PAYSTACK_TIMEOUT_SECONDS", "15"))
PAYSTACK_DEMO_MODE = os.environ.get(
    "PAYSTACK_DEMO_MODE", "True" if DEBUG else "False"
).lower() in ("1", "true", "yes")

# --- Email / transactional notifications ---------------------------------
# Defaults to the console backend so the project runs with no credentials.
# For production set EMAIL_HOST_* (Gmail SMTP, Brevo, Mailgun, SendGrid, SES,
# PythonAnywhere, etc.) and EMAIL_BACKEND to the SMTP backend.
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True").lower() in ("1", "true", "yes")
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "Onesimus Impact Foundation <hello@onesimusimpact.org>"
)
# Internal inbox that receives new-enquiry / new-application notifications.
OIF_NOTIFY_EMAIL = os.environ.get("OIF_NOTIFY_EMAIL", "hello@onesimusimpact.org")

# --- Media upload safety --------------------------------------------------
# 5 MB cap on in-memory uploads; larger files stream to a temp file.
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# --- Production security ---------------------------------------------------
# Activated automatically whenever DEBUG is off (Section 11 / 12).
if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get(
        "SECURE_SSL_REDIRECT", "True").lower() in ("1", "true", "yes")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    X_FRAME_OPTIONS = "DENY"
    CSRF_TRUSTED_ORIGINS = [
        o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o
    ]
