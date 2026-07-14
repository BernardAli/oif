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


def _recipient_name(user):
    return user.first_name or user.get_full_name() or user.username


def send_account_registered(user, login_url, password_reset_url):
    """Send account access details without ever transmitting a password."""
    if not user.email:
        return False
    name = _recipient_name(user)
    return notify_person(
        "Your Onesimus Impact Foundation account is ready",
        f"Dear {name},\n\n"
        "Welcome to the Onesimus Impact Foundation. Your member account has "
        "been created successfully.\n\n"
        f"Username: {user.username}\n"
        f"Sign in: {login_url}\n\n"
        "For your security, passwords are never included in email. If you "
        "forget yours, you can set a new password here:\n"
        f"{password_reset_url}\n\n"
        "From your account, you can register for events, submit applications, "
        "manage your profile, and review your engagement with OIF.\n\n"
        "Kind regards,\nOnesimus Impact Foundation",
        user.email,
    )


def send_event_registration_confirmation(registration, event_url, calendar_url):
    """Confirm a new or renewed registration with the essential logistics."""
    email = registration.attendee_email
    if not email:
        return False
    event = registration.event
    name = registration.attendee_name
    starts_at = event.starts_at.strftime("%A, %d %B %Y at %H:%M %Z")
    location = event.venue_address or event.location
    return notify_person(
        f"Registration confirmed: {event.title}",
        f"Dear {name},\n\n"
        f"Your registration for {event.title} has been confirmed.\n\n"
        f"Date and time: {starts_at}\n"
        f"Location: {location}\n"
        f"Attendance: {registration.get_attendance_mode_display()}\n"
        f"Registration status: {registration.get_status_display()}\n\n"
        f"Event details: {event_url}\n"
        f"Add to calendar: {calendar_url}\n\n"
        "Please keep this email for your records. Any event updates will be "
        "shared using the contact details on your account.\n\n"
        "Kind regards,\nOnesimus Impact Foundation",
        email,
    )


def send_application_decision(application, dashboard_url):
    """Notify an applicant when staff records a final decision."""
    user = application.user
    if not user.email:
        return False
    name = _recipient_name(user)
    if application.status == application.Status.APPROVED:
        subject = f"Your {application.get_kind_display()} application has been accepted"
        decision = (
            f"We are pleased to confirm that your application to participate as "
            f"a {application.get_kind_display()} has been accepted. Welcome to "
            "the Onesimus Impact Foundation community. Our team will contact "
            "you with the next steps."
        )
    else:
        subject = f"Update on your {application.get_kind_display()} application"
        decision = (
            f"Thank you for your interest in serving as a "
            f"{application.get_kind_display()}. After careful review, we are "
            "unable to progress your application at this time. We appreciate "
            "the time and thought you invested."
        )
    return notify_person(
        subject,
        f"Dear {name},\n\n{decision}\n\n"
        f"You can review your application status here: {dashboard_url}\n\n"
        "Kind regards,\nOnesimus Impact Foundation",
        user.email,
    )


def send_membership_accepted(user, login_url):
    """Welcome a user when staff explicitly accepts or activates membership."""
    if not user.email:
        return False
    name = _recipient_name(user)
    return notify_person(
        "Your OIF membership has been accepted",
        f"Dear {name},\n\n"
        "We are pleased to confirm that your membership with the Onesimus "
        "Impact Foundation has been accepted. You can now access your member "
        "account and participate in the opportunities available to you.\n\n"
        f"Username: {user.username}\n"
        f"Sign in: {login_url}\n\n"
        "We look forward to your involvement in the OIF community.\n\n"
        "Kind regards,\nOnesimus Impact Foundation",
        user.email,
    )


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
