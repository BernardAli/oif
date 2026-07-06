import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings


PAYSTACK_BASE_URL = "https://api.paystack.co"


class PaystackError(Exception):
    pass


def is_configured():
    return bool(settings.PAYSTACK_SECRET_KEY)


def _request(path, method="GET", payload=None):
    if not settings.PAYSTACK_SECRET_KEY:
        raise PaystackError("Paystack secret key is not configured.")
    body = None
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
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
