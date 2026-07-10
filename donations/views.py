import uuid
import json
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import DonationForm
from .models import Donation
from . import paystack
from oif_site import notify


def _mark_success(donation):
    """Mark a donation successful and email a receipt once (Section 7.6)."""
    donation.status = Donation.Status.SUCCESS
    if not donation.receipt_sent and notify.send_donation_receipt(donation):
        donation.receipt_sent = True
        donation.save(update_fields=["status", "receipt_sent"])
    else:
        donation.save(update_fields=["status"])
    try:
        from dashboard.accounting import post_donation
        post_donation(donation)
    except Exception:
        # Payment confirmation must remain available even if accounting setup
        # needs administrative attention; reconciliation reports expose gaps.
        pass


def _remember_donation_reference(request, reference):
    references = request.session.get("donation_references", [])
    if reference not in references:
        references.append(reference)
    request.session["donation_references"] = references[-20:]


def _payment_matches_donation(donation, data):
    try:
        paid_amount = int(data.get("amount"))
    except (TypeError, ValueError):
        return False

    metadata = data.get("metadata") or {}
    metadata_donation_id = metadata.get("donation_id")
    if metadata_donation_id and str(metadata_donation_id) != str(donation.pk):
        return False

    return (
        data.get("reference") == donation.reference
        and paid_amount == int(donation.amount * 100)
        and str(data.get("currency", "")).upper() == donation.currency.upper()
    )


def _can_view_status(request, donation):
    if donation.reference in request.session.get("donation_references", []):
        return True
    if not request.user.is_authenticated:
        return False
    return donation.donor_id == request.user.pk or request.user.can("view_donations")


def give(request):
    """Start a donation. Uses Paystack when configured, demo-success otherwise."""
    if request.method == "POST":
        form = DonationForm(request.POST, user=request.user)
        if form.is_valid():
            donation = form.save(commit=False)
            if request.user.is_authenticated:
                donation.donor = request.user
            donation.reference = "OIF-" + uuid.uuid4().hex[:12].upper()
            donation.status = Donation.Status.PENDING
            donation.save()
            _remember_donation_reference(request, donation.reference)

            if not paystack.is_configured() and paystack.demo_mode():
                _mark_success(donation)
                messages.success(request, "Demo payment recorded successfully.")
                return redirect("donations:status", reference=donation.reference)
            if not paystack.is_configured():
                donation.status = Donation.Status.FAILED
                donation.save(update_fields=["status"])
                messages.error(
                    request,
                    "Online giving is temporarily unavailable. Please try again later.",
                )
                return redirect("donations:status", reference=donation.reference)

            try:
                data = paystack.initialize_transaction(
                    amount=donation.amount,
                    email=donation.donor_email,
                    reference=donation.reference,
                    callback_url=request.build_absolute_uri(reverse("donations:callback")),
                    currency=donation.currency,
                    metadata={
                        "donor_name": donation.donor_name,
                        "campaign": donation.campaign,
                        "donation_id": donation.pk,
                    },
                )
            except paystack.PaystackError as exc:
                donation.status = Donation.Status.FAILED
                donation.save(update_fields=["status"])
                messages.error(request, str(exc))
                return redirect("donations:status", reference=donation.reference)

            return redirect(data["authorization_url"])
    else:
        form = DonationForm(user=request.user)
    return render(request, "donations/give.html", {
        "form": form,
        "paystack_configured": paystack.is_configured(),
    })


def callback(request):
    reference = request.GET.get("reference") or request.GET.get("trxref")
    if not reference:
        messages.error(request, "Payment reference was missing.")
        return redirect("donations:give")
    donation = get_object_or_404(Donation, reference=reference)
    _remember_donation_reference(request, donation.reference)
    if not paystack.is_configured() and paystack.demo_mode():
        _mark_success(donation)
        messages.success(request, "Demo payment confirmed.")
        return redirect("donations:status", reference=donation.reference)
    if not paystack.is_configured():
        messages.error(request, "Online giving is not configured.")
        return redirect("donations:status", reference=donation.reference)

    try:
        data = paystack.verify_transaction(reference)
    except paystack.PaystackError as exc:
        messages.error(request, str(exc))
        return redirect("donations:status", reference=donation.reference)

    if data.get("status") == "success" and _payment_matches_donation(donation, data):
        _mark_success(donation)
        messages.success(request, "Thank you! Your donation has been confirmed.")
    elif data.get("status") == "success":
        messages.error(
            request,
            "Payment verification returned details that do not match this donation.",
        )
    else:
        donation.status = Donation.Status.FAILED
        donation.save(update_fields=["status"])
        messages.error(request, "Payment could not be confirmed.")
    return redirect("donations:status", reference=donation.reference)


def status(request, reference):
    donation = get_object_or_404(Donation, reference=reference)
    if not _can_view_status(request, donation):
        raise PermissionDenied("You cannot view this donation receipt.")
    return render(request, "donations/status.html", {"donation": donation})


@csrf_exempt
@require_POST
def webhook(request):
    """Idempotently reconcile Paystack charge events without a browser callback."""
    if not paystack.valid_webhook_signature(
        request.body, request.headers.get("x-paystack-signature", "")
    ):
        return HttpResponseBadRequest("Invalid signature")
    try:
        event = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return HttpResponseBadRequest("Invalid payload")
    if event.get("event") != "charge.success":
        return HttpResponse(status=204)
    data = event.get("data") or {}
    reference = data.get("reference")
    donation = Donation.objects.filter(reference=reference).first()
    if donation and _payment_matches_donation(donation, data):
        _mark_success(donation)
    return HttpResponse(status=200)
