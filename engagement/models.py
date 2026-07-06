"""Member engagement + inbound enquiries.

Covers event registrations, mentor/volunteer/mentee/speaker applications,
mentorship enrollments, contact enquiries, partner/sponsor interest, and
newsletter sign-ups (Sections 5.1.5, 5.1.7, 6 of the agreement).
"""
from django.conf import settings
from django.db import models


class EventRegistration(models.Model):
    class Status(models.TextChoices):
        REGISTERED = "REGISTERED", "Registered"
        ATTENDED = "ATTENDED", "Attended"
        CANCELLED = "CANCELLED", "Cancelled"

    class AttendanceMode(models.TextChoices):
        IN_PERSON = "IN_PERSON", "In person"
        VIRTUAL = "VIRTUAL", "Virtual"
        EITHER = "EITHER", "Either / flexible"

    event = models.ForeignKey("pages.Event", on_delete=models.CASCADE,
                              related_name="registrations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="registrations")
    status = models.CharField(max_length=12, choices=Status.choices,
                              default=Status.REGISTERED)
    attendance_mode = models.CharField(
        max_length=12, choices=AttendanceMode.choices,
        default=AttendanceMode.EITHER,
    )
    organisation = models.CharField(max_length=160, blank=True)
    role_title = models.CharField(max_length=160, blank=True)
    accessibility_needs = models.TextField(blank=True)
    dietary_needs = models.TextField(blank=True)
    question = models.TextField(blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("event", "user")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} → {self.event}"


class Application(models.Model):
    """Mentor / volunteer / mentee / speaker application submitted by a member."""
    class Kind(models.TextChoices):
        MENTOR = "MENTOR", "Mentor"
        VOLUNTEER = "VOLUNTEER", "Volunteer"
        MENTEE = "MENTEE", "Mentee"
        SPEAKER = "SPEAKER", "Speaker"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Not selected"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="applications")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    status = models.CharField(max_length=12, choices=Status.choices,
                              default=Status.PENDING, db_index=True)
    area_of_interest = models.CharField(max_length=160, blank=True)
    motivation = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL,
                                    related_name="reviewed_applications")
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_kind_display()} application — {self.user}"


class MentorshipEnrollment(models.Model):
    """Links a mentee (member) to a mentor for a cohort, with progress tracking."""
    class Phase(models.TextChoices):
        PHASE1 = "PHASE1", "Phase 1 — Recorded Sessions"
        PHASE2 = "PHASE2", "Phase 2 — Live Sessions"
        COMPLETE = "COMPLETE", "Completed"

    mentee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name="mentorships_as_mentee")
    mentor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                               on_delete=models.SET_NULL,
                               related_name="mentorships_as_mentor")
    program = models.ForeignKey("pages.Program", null=True, blank=True,
                                on_delete=models.SET_NULL)
    cohort = models.CharField(max_length=120, blank=True,
                              help_text="Cohort label, e.g. 'Forge — Spring 2026'.")
    phase = models.CharField(max_length=12, choices=Phase.choices,
                             default=Phase.PHASE1)
    sessions_completed = models.PositiveIntegerField(default=0)
    sessions_total = models.PositiveIntegerField(default=12)  # 8 recorded + 4 live
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.mentee} ⟶ {self.mentor or 'unassigned'}"

    @property
    def progress_pct(self):
        if not self.sessions_total:
            return 0
        return round(self.sessions_completed / self.sessions_total * 100)


class ContactMessage(models.Model):
    """A public contact-form enquiry (Section 5.1.7 / 6.1)."""
    class Status(models.TextChoices):
        NEW = "NEW", "New"
        READ = "READ", "Read"
        RESOLVED = "RESOLVED", "Resolved"

    name = models.CharField(max_length=160)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices,
                              default=Status.NEW, db_index=True)
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL,
                                   related_name="handled_messages")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.subject or 'Enquiry'}"


class PartnerEnquiry(models.Model):
    """A partner / sponsor interest submission (Section 5.1.5 / 5.3.7)."""
    class Kind(models.TextChoices):
        PARTNER = "PARTNER", "Partner"
        SPONSOR = "SPONSOR", "Sponsor"
        DONOR = "DONOR", "Institutional Donor"

    class Status(models.TextChoices):
        NEW = "NEW", "New"
        IN_REVIEW = "IN_REVIEW", "In review"
        ENGAGED = "ENGAGED", "Engaged"
        CLOSED = "CLOSED", "Closed"

    organisation = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=160)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    kind = models.CharField(max_length=12, choices=Kind.choices,
                            default=Kind.PARTNER)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices,
                              default=Status.NEW, db_index=True)
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL,
                                   related_name="handled_enquiries")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Partner enquiries"

    def __str__(self):
        return f"{self.organisation} ({self.get_kind_display()})"


class NewsletterSubscriber(models.Model):
    """A newsletter / mailing-list sign-up (Section 6.8)."""
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=160, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
