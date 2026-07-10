import json
import hashlib
import hmac
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings


PAYSTACK_BASE_URL = "https://api.paystack.co"


class PaystackError(Exception):
    pass


def configuration():
    """Prefer CMS settings, while retaining environment-variable fallback."""
    try:
        from dashboard.models import IntegrationSettings
        config = IntegrationSettings.load()
        if not config.paystack_use_cms_configuration:
            return {
                "enabled": bool(settings.PAYSTACK_SECRET_KEY),
                "secret_key": settings.PAYSTACK_SECRET_KEY,
                "public_key": settings.PAYSTACK_PUBLIC_KEY,
                "webhook_secret": settings.PAYSTACK_SECRET_KEY,
                "demo_mode": settings.PAYSTACK_DEMO_MODE,
            }
        return {
            "enabled": config.paystack_enabled,
            "secret_key": config.paystack_secret_key or settings.PAYSTACK_SECRET_KEY,
            "public_key": config.paystack_public_key or settings.PAYSTACK_PUBLIC_KEY,
            "webhook_secret": config.paystack_webhook_secret or config.paystack_secret_key or settings.PAYSTACK_SECRET_KEY,
            "demo_mode": config.paystack_demo_mode,
        }
    except Exception:
        return {
            "enabled": bool(settings.PAYSTACK_SECRET_KEY),
            "secret_key": settings.PAYSTACK_SECRET_KEY,
            "public_key": settings.PAYSTACK_PUBLIC_KEY,
            "webhook_secret": settings.PAYSTACK_SECRET_KEY,
            "demo_mode": settings.PAYSTACK_DEMO_MODE,
        }


def is_configured():
    config = configuration()
    return bool(config["enabled"] and config["secret_key"])


def demo_mode():
    return bool(configuration()["demo_mode"])


def valid_webhook_signature(raw_body, signature):
    config = configuration()
    secret = config["webhook_secret"]
    if not config["enabled"] or not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)


def _request(path, method="GET", payload=None):
    secret_key = configuration()["secret_key"]
    if not secret_key:
        raise PaystackError("Paystack secret key is not configured.")
    body = None
    headers = {"Authorization": f"Bearer {secret_key}"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(f"{PAYSTACK_BASE_URL}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=settings.PAYSTACK_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8"))
        except Exception:
            detail = {"message": str(exc)}
        raise PaystackError(detail.get("message", "Paystack request failed.")) from exc
    except (TimeoutError, URLError) as exc:
        raise PaystackError("Could not reach Paystack. Please try again.") from exc


def initialize_transaction(*, amount, email, reference, callback_url, currency, metadata):
    payload = {
        "amount": str(int(amount * 100)),
        "email": email,
        "reference": reference,
        "callback_url": callback_url,
        "currency": currency,
        "metadata": metadata,
    }
    response = _request("/transaction/initialize", method="POST", payload=payload)
    if not response.get("status"):
        raise PaystackError(response.get("message", "Could not initialize payment."))
    return response["data"]


def verify_transaction(reference):
    safe_reference = quote(reference, safe="")
    response = _request(f"/transaction/verify/{safe_reference}")
    if not response.get("status"):
        raise PaystackError(response.get("message", "Could not verify payment."))
    return response["data"]
