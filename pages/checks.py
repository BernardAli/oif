"""Deployment checks for configuration that is safe in development only."""
from django.conf import settings
from django.core.checks import Error, Tags, Warning, register


@register(Tags.security, deploy=True)
def production_configuration_check(app_configs, **kwargs):
    issues = []
    cms_paystack_enabled = False
    cms_demo_mode = False
    try:
        from dashboard.models import IntegrationSettings
        integration = IntegrationSettings.objects.filter(pk=1).first()
        if integration and integration.paystack_use_cms_configuration:
            cms_paystack_enabled = bool(
                integration.paystack_enabled and integration.paystack_secret_key
            )
            cms_demo_mode = integration.paystack_demo_mode
    except Exception:
        pass
    if settings.DEBUG:
        issues.append(Warning(
            "DEBUG is enabled.",
            hint="Set DJANGO_DEBUG=False before deploying.",
            id="oif.W001",
        ))
    if "django-insecure-dev-key" in settings.SECRET_KEY:
        issues.append(Error(
            "The development SECRET_KEY is still in use.",
            hint="Set DJANGO_SECRET_KEY to a long, random production secret.",
            id="oif.E001",
        ))
    if not settings.DEBUG and (settings.PAYSTACK_DEMO_MODE or cms_demo_mode):
        issues.append(Error(
            "Paystack demo-success mode is enabled in production.",
            hint="Set PAYSTACK_DEMO_MODE=False.",
            id="oif.E002",
        ))
    if not settings.DEBUG and not settings.PAYSTACK_SECRET_KEY and not cms_paystack_enabled:
        issues.append(Warning(
            "Paystack is not configured; online donations will be unavailable.",
            hint="Set PAYSTACK_SECRET_KEY or clearly disable online giving.",
            id="oif.W002",
        ))
    if not settings.DEBUG and settings.EMAIL_BACKEND.endswith("console.EmailBackend"):
        issues.append(Warning(
            "The console email backend is active in production.",
            hint="Configure a transactional SMTP backend.",
            id="oif.W003",
        ))
    return issues
