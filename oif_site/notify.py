"""Lightweight transactional-email helpers.

Every send is best-effort: a mail failure must never break the web request
that triggered it (Section 4.6 / 5.1.5 / 7.6 of the agreement). With the
default console backend the messages simply print to the server log.
"""
import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _send(subject, body, recipients):
    recipients = [r for r in recipients if r]
    if not recipients:
        return False
    try:
        delivered = send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )
        return delivered > 0
    except Exception:  # pragma: no cover - defensive
        logger.exception("Failed to send notification email")
        return False


def notify_team(subject, body):
    """Send an internal notification to the OIF inbox."""
    return _send(f"[OIF] {subject}", body, [settings.OIF_NOTIFY_EMAIL])


def notify_person(subject, body, email):
    """Send a confirmation / receipt to a member or donor."""
    return _send(subject, body, [email])


# --- Ready-made messages --------------------------------------------------
def send_application_received(application):
    who = application.user.get_full_name() or application.user.username
    notify_team(
        f"New {application.get_kind_display()} application",
        f"{who} submitted a {application.get_kind_display()} application.\n"
        f"Area of interest: {application.area_of_interest or 'n/a'}\n\n"
        f"{application.motivation}",
    )
    notify_person(
        "We received your application — Onesimus Impact Foundation",
        f"Hello {who},\n\nThank you for applying to serve as a "
        f"{application.get_kind_display()} with the Onesimus Impact Foundation. "
        "Our team will review your application and be in touch.\n\n— OIF",
        application.user.email,
    )


def send_contact_received(message):
    notify_team(
        f"New enquiry: {message.subject or 'General'}",
        f"From: {message.name} <{message.email}> {message.phone}\n\n"
        f"{message.message}",
    )
    notify_person(
        "We received your message — Onesimus Impact Foundation",
        f"Hello {message.name},\n\nThank you for reaching out to the Onesimus "
        "Impact Foundation. We have received your message and will respond "
        "soon.\n\n— OIF",
        message.email,
    )


def send_partner_received(enquiry):
    notify_team(
        f"New {enquiry.get_kind_display()} enquiry: {enquiry.organisation}",
        f"Organisation: {enquiry.organisation}\n"
        f"Contact: {enquiry.contact_name} <{enquiry.email}> {enquiry.phone}\n\n"
        f"{enquiry.message}",
    )
    notify_person(
        "Thank you for your interest — Onesimus Impact Foundation",
        f"Hello {enquiry.contact_name},\n\nThank you for your interest in "
        f"partnering with the Onesimus Impact Foundation. Our partnerships team "
        "will be in touch.\n\n— OIF",
        enquiry.email,
    )


def send_donation_receipt(donation):
    if not donation.donor_email:
        return False
    return notify_person(
        "Your donation receipt — Onesimus Impact Foundation",
        f"Hello {donation.donor_name or 'friend'},\n\n"
        f"Thank you for your generous gift of {donation.currency} "
        f"{donation.amount:.2f} to the {donation.campaign}.\n"
        f"Reference: {donation.reference}\n"
        f"Channel: {donation.get_channel_display()}\n\n"
        "Your support equips the next generation of leaders. God bless you.\n\n— OIF",
        donation.donor_email,
    )
