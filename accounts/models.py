"""Custom user model with role-based access for OIF.

The role structure implements Schedule B of the OIF–Allgift development
agreement. Every contract role is represented; each role maps to a set of
capabilities that views and templates consult (the single source of truth
for role compliance).
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    # --- Governance / administration ------------------------------------
    ADMIN = "ADMIN", "Super Administrator"
    GLOBAL_LEAD = "GLOBAL_LEAD", "Global Lead"
    EXEC_DIRECTOR = "EXEC_DIRECTOR", "Executive Director"
    DIRECTOR = "DIRECTOR", "Director / Staff"
    # --- Functional directors ------------------------------------------
    DIR_PROGRAMS = "DIR_PROGRAMS", "Director of Programmes"
    DIR_OPS = "DIR_OPS", "Director of Operations & Volunteer Engagement"
    DIR_COMMS = "DIR_COMMS", "Director of Communications, Media & Digital"
    DIR_PARTNERSHIPS = "DIR_PARTNERSHIPS", "Director of Partnerships & Resource Mobilisation"
    # --- Managers / editors --------------------------------------------
    FINANCE = "FINANCE", "Finance / Donations Manager"
    CONTENT_EDITOR = "CONTENT_EDITOR", "Content Editor"
    EVENT_MANAGER = "EVENT_MANAGER", "Event Manager"
    # --- Programme participants ----------------------------------------
    MENTOR = "MENTOR", "Mentor"
    VOLUNTEER = "VOLUNTEER", "Volunteer"
    # --- Public accounts -----------------------------------------------
    APPLICANT = "APPLICANT", "Applicant"
    DONOR = "DONOR", "Donor"
    MEMBER = "MEMBER", "Member"


# Capability vocabulary. Views/templates check these — never the raw role —
# so permissions can be tuned per Schedule B without touching business logic.
CAP_ORG_ANALYTICS = "view_org_analytics"
CAP_MANAGE_USERS = "manage_users"
CAP_MANAGE_MEMBERS = "manage_members"
CAP_MANAGE_EVENTS = "manage_events"
CAP_MANAGE_DONATIONS = "manage_donations"
CAP_VIEW_DONATIONS = "view_donations"
CAP_MANAGE_APPLICATIONS = "manage_applications"
CAP_MANAGE_MENTORSHIP = "manage_mentorship"
CAP_VIEW_MENTEES = "view_mentees"
CAP_VIEW_ASSIGNMENTS = "view_assignments"
CAP_MANAGE_CONTENT = "manage_content"
CAP_MANAGE_MEDIA = "manage_media"
CAP_MANAGE_SPEAKERS = "manage_speakers"
CAP_MANAGE_TESTIMONIALS = "manage_testimonials"
CAP_MANAGE_CONTACT = "manage_contact"
CAP_MANAGE_PARTNERS = "manage_partners"
CAP_VIEW_PARTNERS = "view_partners"
CAP_APPROVE_CONTENT = "approve_content"
CAP_CONFIGURE = "configure_integrations"
CAP_SEND_MESSAGES = "send_messages"
CAP_VIEW_MESSAGE_REPORTS = "view_message_reports"
CAP_VIEW_AUDIT = "view_audit"
CAP_REGISTER_EVENTS = "register_events"
CAP_GIVE = "give_donations"

# Capabilities available to every authenticated account.
BASE_CAPS = {CAP_REGISTER_EVENTS, CAP_GIVE}

# The full set (Super Administrator).
ALL_CAPS = {
    CAP_ORG_ANALYTICS, CAP_MANAGE_USERS, CAP_MANAGE_MEMBERS, CAP_MANAGE_EVENTS,
    CAP_MANAGE_DONATIONS, CAP_VIEW_DONATIONS, CAP_MANAGE_APPLICATIONS,
    CAP_MANAGE_MENTORSHIP, CAP_VIEW_MENTEES, CAP_VIEW_ASSIGNMENTS,
    CAP_MANAGE_CONTENT, CAP_MANAGE_MEDIA, CAP_MANAGE_SPEAKERS,
    CAP_MANAGE_TESTIMONIALS, CAP_MANAGE_CONTACT, CAP_MANAGE_PARTNERS,
    CAP_VIEW_PARTNERS, CAP_APPROVE_CONTENT, CAP_CONFIGURE, CAP_SEND_MESSAGES,
    CAP_VIEW_MESSAGE_REPORTS, CAP_VIEW_AUDIT,
} | BASE_CAPS

# Capabilities that mark an account as internal staff (dashboard admin areas).
STAFF_CAPS = {
    CAP_ORG_ANALYTICS, CAP_MANAGE_MEMBERS, CAP_MANAGE_EVENTS,
    CAP_MANAGE_DONATIONS, CAP_MANAGE_APPLICATIONS, CAP_MANAGE_MENTORSHIP,
    CAP_MANAGE_CONTENT, CAP_MANAGE_MEDIA, CAP_MANAGE_SPEAKERS,
    CAP_MANAGE_TESTIMONIALS, CAP_MANAGE_CONTACT, CAP_MANAGE_PARTNERS,
    CAP_VIEW_DONATIONS, CAP_VIEW_PARTNERS, CAP_APPROVE_CONTENT,
    CAP_SEND_MESSAGES, CAP_VIEW_MESSAGE_REPORTS,
}

ROLE_CAPABILITIES = {
    Role.ADMIN: set(ALL_CAPS),
    Role.GLOBAL_LEAD: {
        CAP_ORG_ANALYTICS, CAP_VIEW_DONATIONS, CAP_VIEW_PARTNERS,
        CAP_APPROVE_CONTENT, CAP_VIEW_MESSAGE_REPORTS, CAP_VIEW_AUDIT,
    } | BASE_CAPS,
    Role.EXEC_DIRECTOR: {
        CAP_ORG_ANALYTICS, CAP_MANAGE_MEMBERS, CAP_MANAGE_EVENTS,
        CAP_MANAGE_APPLICATIONS, CAP_MANAGE_MENTORSHIP, CAP_VIEW_MENTEES,
        CAP_VIEW_DONATIONS, CAP_MANAGE_CONTENT, CAP_APPROVE_CONTENT,
        CAP_VIEW_PARTNERS, CAP_MANAGE_CONTACT, CAP_SEND_MESSAGES,
        CAP_VIEW_MESSAGE_REPORTS, CAP_VIEW_AUDIT,
    } | BASE_CAPS,
    # Backwards-compatible general "Director / Staff" role — broad operations.
    Role.DIRECTOR: {
        CAP_ORG_ANALYTICS, CAP_MANAGE_MEMBERS, CAP_MANAGE_EVENTS,
        CAP_VIEW_DONATIONS, CAP_MANAGE_APPLICATIONS, CAP_MANAGE_MENTORSHIP,
        CAP_VIEW_MENTEES, CAP_MANAGE_CONTENT, CAP_MANAGE_CONTACT,
        CAP_VIEW_PARTNERS, CAP_APPROVE_CONTENT, CAP_SEND_MESSAGES,
        CAP_VIEW_MESSAGE_REPORTS,
    } | BASE_CAPS,
    Role.DIR_PROGRAMS: {
        CAP_ORG_ANALYTICS, CAP_MANAGE_EVENTS, CAP_MANAGE_MENTORSHIP,
        CAP_VIEW_MENTEES, CAP_MANAGE_CONTENT, CAP_MANAGE_MEDIA,
        CAP_SEND_MESSAGES, CAP_VIEW_MESSAGE_REPORTS,
    } | BASE_CAPS,
    Role.DIR_OPS: {
        CAP_ORG_ANALYTICS, CAP_MANAGE_MEMBERS, CAP_MANAGE_APPLICATIONS,
        CAP_VIEW_ASSIGNMENTS, CAP_VIEW_MENTEES, CAP_MANAGE_CONTACT,
    } | BASE_CAPS,
    Role.DIR_COMMS: {
        CAP_MANAGE_CONTENT, CAP_MANAGE_MEDIA, CAP_MANAGE_SPEAKERS,
        CAP_MANAGE_TESTIMONIALS, CAP_SEND_MESSAGES, CAP_VIEW_MESSAGE_REPORTS,
    } | BASE_CAPS,
    Role.DIR_PARTNERSHIPS: {
        CAP_ORG_ANALYTICS, CAP_VIEW_PARTNERS, CAP_MANAGE_PARTNERS,
        CAP_VIEW_DONATIONS, CAP_MANAGE_CONTACT, CAP_SEND_MESSAGES,
        CAP_VIEW_MESSAGE_REPORTS,
    } | BASE_CAPS,
    Role.FINANCE: {
        CAP_MANAGE_DONATIONS, CAP_VIEW_DONATIONS,
    } | BASE_CAPS,
    Role.CONTENT_EDITOR: {
        CAP_MANAGE_CONTENT, CAP_MANAGE_MEDIA, CAP_MANAGE_SPEAKERS,
        CAP_MANAGE_TESTIMONIALS, CAP_SEND_MESSAGES, CAP_VIEW_MESSAGE_REPORTS,
    } | BASE_CAPS,
    Role.EVENT_MANAGER: {
        CAP_MANAGE_EVENTS, CAP_SEND_MESSAGES, CAP_VIEW_MESSAGE_REPORTS,
    } | BASE_CAPS,
    Role.MENTOR: {
        CAP_VIEW_MENTEES, CAP_VIEW_ASSIGNMENTS,
    } | BASE_CAPS,
    Role.VOLUNTEER: {
        CAP_VIEW_ASSIGNMENTS,
    } | BASE_CAPS,
    Role.APPLICANT: set(BASE_CAPS),
    Role.DONOR: set(BASE_CAPS),
    Role.MEMBER: set(BASE_CAPS),
}


class User(AbstractUser):
    """A single account model serving public members and internal staff."""

    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.MEMBER, db_index=True
    )
    phone = models.CharField(max_length=32, blank=True)
    bio = models.TextField(blank=True)
    title = models.CharField(
        max_length=120, blank=True, help_text="Professional title or program role."
    )
    location = models.CharField(max_length=120, blank=True, default="Accra, Ghana")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_public_profile = models.BooleanField(default=False)
    marketing_opt_in = models.BooleanField(
        default=False, help_text="Consented to newsletters / updates."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return self.get_full_name() or self.username

    # --- role helpers -----------------------------------------------------
    @property
    def capabilities(self):
        if self.is_superuser:
            return set(ALL_CAPS)
        return ROLE_CAPABILITIES.get(self.role, set(BASE_CAPS))

    def can(self, capability):
        """True if the user's role grants the given capability."""
        if self.is_superuser:
            return True
        return capability in self.capabilities

    @property
    def is_staff_role(self):
        if self.is_superuser:
            return True
        return bool(self.capabilities & STAFF_CAPS)

    @property
    def role_badge(self):
        return self.get_role_display()
