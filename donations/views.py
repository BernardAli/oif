import uuid
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

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

            if not paystack.is_configured():
                _mark_success(donation)
                messages.success(request, "Demo payment recorded successfully.")
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
    if not paystack.is_configured():
        _mark_success(donation)
        messages.success(request, "Demo payment confirmed.")
        return redirect("donations:status", reference=donation.reference)

    try:
        data = paystack.verify_transaction(reference)
    except paystack.PaystackError as exc:
        messages.error(request, str(exc))
        return redirect("donations:status", reference=donation.reference)

    if data.get("status") == "success":
        _mark_success(donation)
        messages.success(request, "Thank you! Your donation has been confirmed.")
    else:
        donation.status = Donation.Status.FAILED
        donation.save(update_fields=["status"])
        messages.error(request, "Payment could not be confirmed.")
    return redirect("donations:status", reference=donation.reference)


def status(request, reference):
    donation = get_object_or_404(Donation, reference=reference)
    return render(request, "donations/status.html", {"donation": donation})
