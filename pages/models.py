"""Database-driven content for the public OIF site."""
from functools import cached_property
from urllib.parse import quote_plus

from django.db import models
from django.utils import timezone
from django.utils.text import slugify


GOOGLE_FONT_CHOICES = (
    ("Inter", "Inter"),
    ("Roboto", "Roboto"),
    ("Open Sans", "Open Sans"),
    ("Lato", "Lato"),
    ("Montserrat", "Montserrat"),
    ("Poppins", "Poppins"),
    ("Source Sans 3", "Source Sans 3"),
    ("Nunito Sans", "Nunito Sans"),
    ("Work Sans", "Work Sans"),
    ("Manrope", "Manrope"),
    ("Raleway", "Raleway"),
    ("Playfair Display", "Playfair Display"),
    ("Lora", "Lora"),
    ("Merriweather", "Merriweather"),
    ("Oswald", "Oswald"),
    ("Cormorant Garamond", "Cormorant Garamond"),
    ("Libre Baskerville", "Libre Baskerville"),
    ("DM Sans", "DM Sans"),
    ("Urbanist", "Urbanist"),
    ("Space Grotesk", "Space Grotesk"),
)


class SiteBranding(models.Model):
    """Singleton project profile, brand media, and shared typography."""
    org_name = models.CharField(
        max_length=160,
        default="Onesimus Impact Foundation",
        blank=True,
        help_text="Official public name of the organization or project.",
    )
    short_name = models.CharField(
        max_length=40,
        default="OIF",
        blank=True,
        help_text="Short label used in compact dashboard and browser contexts.",
    )
    tagline = models.CharField(
        max_length=180,
        default="Equipping the Next Generation of Global Leaders",
        blank=True,
    )
    founded_year = models.CharField(max_length=20, default="2018", blank=True)
    location = models.CharField(max_length=120, default="Accra, Ghana", blank=True)
    contact_email = models.EmailField(default="hello@onesimusimpact.org", blank=True)
    contact_phone = models.CharField(max_length=40, default="+233 XXX XXX XXX", blank=True)
    website_url = models.URLField(blank=True)
    footer_blurb = models.TextField(
        blank=True,
        default=(
            "A youth-led NGO in Accra equipping emerging African leaders through "
            "conferences, mentorship, humanitarian action, and digital infrastructure."
        ),
    )
    logo = models.ImageField(upload_to="branding/", blank=True, null=True)
    logo_mark = models.ImageField(
        upload_to="branding/",
        blank=True,
        null=True,
        help_text="Compact square or circular logo mark used where space is limited.",
    )
    favicon = models.ImageField(upload_to="branding/", blank=True, null=True)
    instagram_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True, help_text="X / Twitter profile URL.")
    youtube_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    title_font = models.CharField(
        max_length=80,
        choices=GOOGLE_FONT_CHOICES,
        default="Inter",
        help_text="Google Font used for headings, display text, and brand marks.",
    )
    body_font = models.CharField(
        max_length=80,
        choices=GOOGLE_FONT_CHOICES,
        default="Inter",
        help_text="Google Font used for paragraphs, tables, forms, and controls.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site branding"
        verbose_name_plural = "Site branding"

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def display_name(self):
        return self.org_name or "Onesimus Impact Foundation"

    @property
    def display_short_name(self):
        return self.short_name or "OIF"

    @property
    def display_tagline(self):
        return self.tagline or "Equipping the Next Generation of Global Leaders"

    @property
    def display_email(self):
        return self.contact_email or "hello@onesimusimpact.org"

    @property
    def display_phone(self):
        return self.contact_phone or "+233 XXX XXX XXX"

    @property
    def display_founded_year(self):
        return self.founded_year or "2018"

    @property
    def display_location(self):
        return self.location or "Accra, Ghana"

    @property
    def google_fonts_url(self):
        families = []
        for font in (self.title_font, self.body_font):
            if font not in families:
                families.append(font)
        query = "&".join(f"family={quote_plus(font)}" for font in families)
        return f"https://fonts.googleapis.com/css2?{query}&display=swap"


class SitePageImages(models.Model):
    """Singleton for decorative/hero photography on public pages that has no
    other CMS-managed home (i.e. isn't already an ImageField on a Program,
    Speaker, TeamMember, Testimonial, GalleryImage, or Event record).

    Every field is optional. Templates fall back to a built-in placeholder
    image until a real photo is uploaded here, so the public site never
    breaks while these are empty.
    """
    home_hero = models.ImageField(
        upload_to="page-images/", blank=True, null=True,
        help_text="Homepage — full-width hero background behind the headline.",
    )
    about_hero = models.ImageField(
        upload_to="page-images/", blank=True, null=True,
        help_text="About OIF — hero photo beside the introduction.",
    )
    about_story = models.ImageField(
        upload_to="page-images/", blank=True, null=True,
        help_text="About OIF — photo beside the \"Our story\" section.",
    )
    programs_hero_main = models.ImageField(
        upload_to="page-images/", blank=True, null=True,
        help_text="Programs — large hero photo.",
    )
    programs_hero_alt1 = models.ImageField(
        upload_to="page-images/", blank=True, null=True,
        help_text="Programs — small hero photo (first).",
    )
    programs_hero_alt2 = models.ImageField(
        upload_to="page-images/", blank=True, null=True,
        help_text="Programs — small hero photo (second).",
    )
    impact_hero = models.ImageField(
        upload_to="page-images/", blank=True, null=True,
        help_text="Impact — hero photo.",
    )
    leadership_hero = models.ImageField(
        upload_to="page-images/", blank=True, null=True,
        help_text="Leadership — hero photo.",
    )
    speakers_hero = models.ImageField(
        upload_to="page-images/", blank=True, null=True,
        help_text="Speakers — hero photo.",
    )
    gallery_hero = models.ImageField(
        upload_to="page-images/", blank=True, null=True,
        help_text="Gallery — hero photo.",
    )
    donate_hero = models.ImageField(
        upload_to="page-images/", blank=True, null=True,
        help_text="Donate (information page) — hero photo.",
    )
    contact_hero = models.ImageField(
        upload_to="page-images/", blank=True, null=True,
        help_text="Contact — hero photo.",
    )
    involved_mentor = models.ImageField(
        upload_to="page-images/", blank=True, null=True,
        help_text="Get Involved — mentor portrait.",
    )
    involved_volunteer = models.ImageField(
        upload_to="page-images/", blank=True, null=True,
        help_text="Get Involved — volunteer portrait.",
    )
    involved_partner = models.ImageField(
        upload_to="page-images/", blank=True, null=True,
        help_text="Get Involved — partner portrait.",
    )
    give_side = models.ImageField(
        upload_to="page-images/", blank=True, null=True,
        help_text="Give (donation checkout) — side photo.",
    )
    apply_side = models.ImageField(
        upload_to="page-images/", blank=True, null=True,
        help_text="Apply (mentor/volunteer/mentee/speaker) — side photo.",
    )
    auth_side = models.ImageField(
        upload_to="page-images/", blank=True, null=True,
        help_text="Login and password reset — side photo.",
    )
    signup_side = models.ImageField(
        upload_to="page-images/", blank=True, null=True,
        help_text="Create account — side photo.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Page imagery"
        verbose_name_plural = "Page imagery"

    def __str__(self):
        return "Public site page imagery"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SitePageCopy(models.Model):
    """Singleton for the editorial "writeups" (hero and section eyebrows,
    headlines, and paragraphs) on public pages that aren't already sourced
    from a Program, Event, Testimonial, or other CMS list record.

    Every field is optional. Templates fall back to the site's built-in
    default copy until a field is filled in here, so the public site never
    breaks or goes blank while these are empty.
    """
    # --- Homepage ----------------------------------------------------------
    home_hero_headline = models.CharField(max_length=300, blank=True)
    home_hero_body = models.TextField(blank=True)
    home_no_event_headline = models.CharField(
        max_length=200, blank=True,
        help_text="Shown instead of a real event when none is upcoming.")
    home_no_event_body = models.TextField(blank=True)
    home_programs_eyebrow = models.CharField(max_length=120, blank=True)
    home_programs_headline = models.CharField(max_length=200, blank=True)
    home_speakers_eyebrow = models.CharField(max_length=120, blank=True)
    home_speakers_headline = models.CharField(max_length=200, blank=True)
    home_cta_eyebrow = models.CharField(max_length=120, blank=True)
    home_cta_headline = models.CharField(max_length=200, blank=True)
    home_cta_body = models.TextField(blank=True)

    # --- About OIF -----------------------------------------------------
    about_hero_headline = models.CharField(max_length=300, blank=True)
    about_hero_body = models.TextField(blank=True)
    about_story_eyebrow = models.CharField(max_length=120, blank=True)
    about_story_headline = models.CharField(max_length=200, blank=True)
    about_story_body1 = models.TextField(blank=True)
    about_story_body2 = models.TextField(blank=True)
    about_vision_body = models.TextField(blank=True)
    about_mission1_body = models.TextField(blank=True)
    about_mission2_body = models.TextField(blank=True)
    about_mission3_body = models.TextField(blank=True)
    about_values_eyebrow = models.CharField(max_length=120, blank=True)
    about_values_headline = models.CharField(max_length=200, blank=True)
    about_values_body = models.TextField(blank=True)
    about_people_eyebrow = models.CharField(max_length=120, blank=True)
    about_people_headline = models.CharField(max_length=200, blank=True)
    about_people_body = models.TextField(blank=True)
    about_cta_eyebrow = models.CharField(max_length=120, blank=True)
    about_cta_headline = models.CharField(max_length=200, blank=True)
    about_cta_body = models.TextField(blank=True)

    # --- Programs ------------------------------------------------------
    programs_hero_eyebrow = models.CharField(max_length=120, blank=True)
    programs_hero_headline = models.CharField(max_length=300, blank=True)
    programs_hero_body = models.TextField(blank=True)
    programs_overview_eyebrow = models.CharField(max_length=120, blank=True)
    programs_overview_headline = models.CharField(max_length=200, blank=True)
    programs_overview_body = models.TextField(blank=True)
    programs_conferences_eyebrow = models.CharField(max_length=120, blank=True)
    programs_conferences_headline = models.CharField(max_length=200, blank=True)
    programs_conferences_body = models.TextField(blank=True)
    programs_mentorship_eyebrow = models.CharField(max_length=120, blank=True)
    programs_mentorship_headline = models.CharField(max_length=200, blank=True)
    programs_mentorship_body = models.TextField(blank=True)
    programs_events_eyebrow = models.CharField(max_length=120, blank=True)
    programs_events_headline = models.CharField(max_length=200, blank=True)
    programs_events_body = models.TextField(blank=True)

    # --- Impact ----------------------------------------------------------
    impact_hero_headline = models.CharField(max_length=300, blank=True)
    impact_hero_body = models.TextField(blank=True)
    impact_lanes_eyebrow = models.CharField(max_length=120, blank=True)
    impact_lanes_headline = models.CharField(max_length=200, blank=True)
    impact_lanes_body = models.TextField(blank=True)

    # --- Get Involved --------------------------------------------------
    involved_hero_headline = models.CharField(max_length=300, blank=True)
    involved_hero_body = models.TextField(blank=True)
    involved_pathways_eyebrow = models.CharField(max_length=120, blank=True)
    involved_pathways_headline = models.CharField(max_length=200, blank=True)
    involved_steps_eyebrow = models.CharField(max_length=120, blank=True)
    involved_steps_headline = models.CharField(max_length=200, blank=True)
    involved_giving_eyebrow = models.CharField(max_length=120, blank=True)
    involved_giving_headline = models.CharField(max_length=200, blank=True)
    involved_giving_body = models.TextField(blank=True)
    involved_partner_eyebrow = models.CharField(max_length=120, blank=True)
    involved_partner_headline = models.CharField(max_length=200, blank=True)
    involved_partner_body = models.TextField(blank=True)

    # --- Leadership ------------------------------------------------------
    leadership_hero_headline = models.CharField(max_length=300, blank=True)
    leadership_hero_body = models.TextField(blank=True)
    leadership_intro_eyebrow = models.CharField(max_length=120, blank=True)
    leadership_intro_headline = models.CharField(max_length=200, blank=True)
    leadership_intro_body = models.TextField(blank=True)

    # --- Speakers ----------------------------------------------------------
    speakers_hero_headline = models.CharField(max_length=300, blank=True)
    speakers_hero_body = models.TextField(blank=True)
    speakers_featured_eyebrow = models.CharField(max_length=120, blank=True)
    speakers_featured_headline = models.CharField(max_length=200, blank=True)
    speakers_archive_eyebrow = models.CharField(max_length=120, blank=True)
    speakers_archive_headline = models.CharField(max_length=200, blank=True)

    # --- Gallery -----------------------------------------------------------
    gallery_hero_headline = models.CharField(max_length=300, blank=True)
    gallery_hero_body = models.TextField(blank=True)

    # --- Donate ------------------------------------------------------------
    donate_hero_headline = models.CharField(max_length=300, blank=True)
    donate_hero_body = models.TextField(blank=True)

    # --- Contact -----------------------------------------------------------
    contact_hero_headline = models.CharField(max_length=300, blank=True)
    contact_hero_body = models.TextField(blank=True)
    contact_details_eyebrow = models.CharField(max_length=120, blank=True)
    contact_details_headline = models.CharField(max_length=200, blank=True)
    contact_form_eyebrow = models.CharField(max_length=120, blank=True)
    contact_form_headline = models.CharField(max_length=200, blank=True)
    contact_form_body = models.TextField(blank=True)
    contact_response_note = models.CharField(
        max_length=200, blank=True,
        help_text="Short response-time expectation shown beside the send button.",
    )
    contact_paths_eyebrow = models.CharField(max_length=120, blank=True)
    contact_paths_headline = models.CharField(max_length=200, blank=True)

    # --- Site-wide footer ------------------------------------------------
    footer_cta_eyebrow = models.CharField(max_length=120, blank=True)
    footer_cta_headline = models.CharField(max_length=200, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Page copy"
        verbose_name_plural = "Page copy"

    def __str__(self):
        return "Public site page copy"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# Grouped (label, [field names]) layout shared by the dashboard edit form,
# the dashboard coverage table, and the Django admin fieldsets.
PAGE_COPY_GROUPS = [
    ("Homepage", [
        "home_hero_headline", "home_hero_body",
        "home_no_event_headline", "home_no_event_body",
        "home_programs_eyebrow", "home_programs_headline",
        "home_speakers_eyebrow", "home_speakers_headline",
        "home_cta_eyebrow", "home_cta_headline", "home_cta_body",
    ]),
    ("About OIF", [
        "about_hero_headline", "about_hero_body",
        "about_story_eyebrow", "about_story_headline",
        "about_story_body1", "about_story_body2",
        "about_vision_body", "about_mission1_body", "about_mission2_body",
        "about_mission3_body",
        "about_values_eyebrow", "about_values_headline", "about_values_body",
        "about_people_eyebrow", "about_people_headline", "about_people_body",
        "about_cta_eyebrow", "about_cta_headline", "about_cta_body",
    ]),
    ("Programs", [
        "programs_hero_eyebrow", "programs_hero_headline", "programs_hero_body",
        "programs_overview_eyebrow", "programs_overview_headline",
        "programs_overview_body", "programs_conferences_eyebrow",
        "programs_conferences_headline", "programs_conferences_body",
        "programs_mentorship_eyebrow", "programs_mentorship_headline",
        "programs_mentorship_body",
        "programs_events_eyebrow", "programs_events_headline",
        "programs_events_body",
    ]),
    ("Impact", [
        "impact_hero_headline", "impact_hero_body",
        "impact_lanes_eyebrow", "impact_lanes_headline", "impact_lanes_body",
    ]),
    ("Get Involved", [
        "involved_hero_headline", "involved_hero_body",
        "involved_pathways_eyebrow", "involved_pathways_headline",
        "involved_steps_eyebrow", "involved_steps_headline",
        "involved_giving_eyebrow", "involved_giving_headline", "involved_giving_body",
        "involved_partner_eyebrow", "involved_partner_headline", "involved_partner_body",
    ]),
    ("Leadership", [
        "leadership_hero_headline", "leadership_hero_body",
        "leadership_intro_eyebrow", "leadership_intro_headline",
        "leadership_intro_body",
    ]),
    ("Speakers", [
        "speakers_hero_headline", "speakers_hero_body",
        "speakers_featured_eyebrow", "speakers_featured_headline",
        "speakers_archive_eyebrow", "speakers_archive_headline",
    ]),
    ("Gallery", ["gallery_hero_headline", "gallery_hero_body"]),
    ("Donate", ["donate_hero_headline", "donate_hero_body"]),
    ("Contact", [
        "contact_hero_headline", "contact_hero_body",
        "contact_details_eyebrow", "contact_details_headline",
        "contact_form_eyebrow", "contact_form_headline", "contact_form_body",
        "contact_response_note",
        "contact_paths_eyebrow", "contact_paths_headline",
    ]),
    ("Site-wide footer", ["footer_cta_eyebrow", "footer_cta_headline"]),
]


class Program(models.Model):
    """A wing/flagship program: The Forge, The Hadassah Project, Humanitarian."""
    class Wing(models.TextChoices):
        FORGE = "FORGE", "The Forge"
        HADASSAH = "HADASSAH", "The Hadassah Project"
        HUMANITARIAN = "HUMANITARIAN", "Humanitarian Wing"
        VIRTUAL = "VIRTUAL", "Virtual Conferences"
        MENTORSHIP = "MENTORSHIP", "Mentorship Programme"

    wing = models.CharField(max_length=20, choices=Wing.choices, unique=True)
    tagline = models.CharField(max_length=160)
    headline = models.CharField(max_length=160)
    description = models.TextField()
    image = models.ImageField(upload_to="programs/", blank=True, null=True)
    accent = models.CharField(max_length=20, default="coffee",
                              help_text="coffee | tan | olive | gold")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.get_wing_display()


class ProgramResource(models.Model):
    """A downloadable resource attached to a program (curriculum, brief, etc.)."""
    program = models.ForeignKey(Program, on_delete=models.CASCADE,
                                related_name="resources")
    title = models.CharField(max_length=160)
    description = models.CharField(max_length=240, blank=True)
    file = models.FileField(upload_to="resources/", blank=True, null=True)
    external_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self):
        return self.title

    @property
    def link(self):
        if self.file:
            return self.file.url
        return self.external_url


class ProgramInitiative(models.Model):
    """A dedicated programme page within one of the three public pillars."""

    class Pillar(models.TextChoices):
        CONFERENCES = "CONFERENCES", "Virtual Conferences"
        MENTORSHIP = "MENTORSHIP", "Mentorship Program"
        EVENTS = "EVENTS", "Events"

    class PageType(models.TextChoices):
        CONFERENCE = "CONFERENCE", "Virtual conference"
        MENTORSHIP = "MENTORSHIP", "Mentorship program"
        OUTREACH = "OUTREACH", "Humanitarian outreach"
        IN_PERSON = "IN_PERSON", "In-person events"

    pillar = models.CharField(max_length=16, choices=Pillar.choices, db_index=True)
    page_type = models.CharField(max_length=16, choices=PageType.choices, db_index=True)
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    eyebrow = models.CharField(max_length=180)
    description = models.TextField()
    frequency_badge = models.CharField(max_length=80, blank=True)
    hero_image = models.ImageField(upload_to="program-initiatives/", blank=True, null=True)
    phase_one_title = models.CharField(max_length=180, blank=True)
    phase_one_intro = models.TextField(blank=True)
    phase_two_title = models.CharField(max_length=180, blank=True)
    phase_two_intro = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["pillar", "order", "title"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:180] or "initiative"
            slug, i = base, 2
            while ProgramInitiative.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ConferenceEdition(models.Model):
    """An upcoming or archived edition on a virtual-conference page."""

    class Status(models.TextChoices):
        UPCOMING = "UPCOMING", "Upcoming conference"
        PAST = "PAST", "Past conference"

    initiative = models.ForeignKey(
        ProgramInitiative, on_delete=models.CASCADE, related_name="conference_editions"
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PAST)
    edition_label = models.CharField(max_length=80, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    event_date = models.DateField(blank=True, null=True)
    flyer = models.ImageField(upload_to="conference-editions/", blank=True, null=True)
    registration_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["status", "order", "-event_date", "name"]

    def __str__(self):
        return f"{self.initiative}: {self.name}"


class ConferenceSpeakerFlyer(models.Model):
    """A speaker/personality image attached to a conference edition (maximum four)."""

    edition = models.ForeignKey(
        ConferenceEdition, on_delete=models.CASCADE, related_name="speaker_flyers"
    )
    image = models.ImageField(upload_to="conference-speakers/")
    caption = models.CharField(max_length=160, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "pk"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.edition_id and self.edition.speaker_flyers.exclude(pk=self.pk).count() >= 4:
            raise ValidationError("A conference edition can have no more than four speaker flyers.")

    def __str__(self):
        return self.caption or f"Speaker flyer for {self.edition.name}"


class MentorshipSession(models.Model):
    initiative = models.ForeignKey(
        ProgramInitiative, on_delete=models.CASCADE, related_name="mentorship_sessions"
    )
    session_number = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=200)
    track_label = models.CharField(
        max_length=120, blank=True,
        help_text="Optional grouping, e.g. Career Development or Entrepreneurship.",
    )
    video_url = models.URLField(
        blank=True,
        help_text="Stored for the future Watch feature; playback is not enabled yet.",
    )
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "session_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["initiative", "session_number"],
                name="unique_initiative_session_number",
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.session_number and not 1 <= self.session_number <= 8:
            raise ValidationError({"session_number": "Session number must be between 1 and 8."})

    def __str__(self):
        return f"{self.initiative} · Session {self.session_number:02d}"


class MentorshipTrack(models.Model):
    initiative = models.ForeignKey(
        ProgramInitiative, on_delete=models.CASCADE, related_name="mentorship_tracks"
    )
    label = models.CharField(max_length=80, blank=True)
    title = models.CharField(max_length=180)
    sessions_count = models.PositiveSmallIntegerField(default=4)
    sessions_label = models.CharField(
        max_length=120,
        blank=True,
        help_text=(
            "Public session summary, e.g. '4 live sessions' or "
            "'4 sessions across weeks 9–12'."
        ),
    )
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self):
        return f"{self.initiative} · {self.title}"

    @property
    def display_sessions_label(self):
        if self.sessions_label:
            return self.sessions_label
        return f"{self.sessions_count} session{'s' if self.sessions_count != 1 else ''}"


class SDGFocus(models.Model):
    initiative = models.ForeignKey(
        ProgramInitiative, on_delete=models.CASCADE, related_name="sdg_focuses"
    )
    sdg_number = models.PositiveSmallIntegerField()
    goal_name = models.CharField(max_length=180)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "sdg_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["initiative", "sdg_number"], name="unique_initiative_sdg"
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.sdg_number and not 1 <= self.sdg_number <= 17:
            raise ValidationError({"sdg_number": "Select a UN SDG number from 1 to 17."})

    def __str__(self):
        return f"SDG {self.sdg_number}: {self.goal_name}"


class InitiativeArchiveEntry(models.Model):
    """A past outreach activity or in-person event displayed as an archive card."""

    initiative = models.ForeignKey(
        ProgramInitiative, on_delete=models.CASCADE, related_name="archive_entries"
    )
    label = models.CharField(max_length=80, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    event_date = models.DateField(blank=True, null=True)
    image = models.ImageField(upload_to="program-archives/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "-event_date", "name"]

    def __str__(self):
        return f"{self.initiative}: {self.name}"


class Speaker(models.Model):
    name = models.CharField(max_length=160)
    role = models.CharField(max_length=240)
    photo = models.ImageField(upload_to="speakers/", blank=True, null=True)
    featured = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class TeamMember(models.Model):
    class Position(models.TextChoices):
        GLOBAL_LEAD = "GLOBAL_LEAD", "Global Lead"
        EXEC_DIRECTOR = "EXEC_DIRECTOR", "Executive Director"
        DIRECTOR = "DIRECTOR", "Director"
        SECRETARY = "SECRETARY", "Company Secretary"

    name = models.CharField(max_length=160)
    position = models.CharField(max_length=20, choices=Position.choices)
    title = models.CharField(max_length=200, blank=True)
    credential = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="team/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.name} — {self.get_position_display()}"


class SiteStat(models.Model):
    """Headline numbers shown on the home page stats strip."""
    label = models.CharField(max_length=80)
    value = models.CharField(max_length=20)
    suffix = models.CharField(max_length=5, blank=True, default="+")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.value}{self.suffix} {self.label}"


class Testimonial(models.Model):
    """A conference or mentorship testimonial shown on the Impact page."""
    class Source(models.TextChoices):
        CONFERENCE = "CONFERENCE", "Conference"
        MENTORSHIP = "MENTORSHIP", "Mentorship"
        OUTREACH = "OUTREACH", "Humanitarian Outreach"

    author = models.CharField(max_length=160)
    author_role = models.CharField(max_length=200, blank=True)
    source = models.CharField(max_length=20, choices=Source.choices,
                              default=Source.CONFERENCE)
    quote = models.TextField()
    photo = models.ImageField(upload_to="testimonials/", blank=True, null=True)
    is_published = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return f"{self.author} ({self.get_source_display()})"


class GalleryImage(models.Model):
    """An image in the public media gallery."""
    caption = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to="gallery/", blank=True, null=True)
    program = models.ForeignKey(Program, null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="gallery")
    is_published = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return self.caption or f"Gallery image #{self.pk}"


class Policy(models.Model):
    """Editable legal / policy page (privacy, terms, donation policy)."""
    class Kind(models.TextChoices):
        PRIVACY = "privacy", "Privacy Policy"
        TERMS = "terms", "Terms of Use"
        DONATION = "donation", "Donation Policy"

    kind = models.CharField(max_length=20, choices=Kind.choices, unique=True)
    title = models.CharField(max_length=160)
    body = models.TextField(help_text="Plain text / simple HTML. Placeholder "
                                       "content until final policy is supplied.")
    is_placeholder = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["kind"]
        verbose_name_plural = "Policies"

    def __str__(self):
        return self.title


class Event(models.Model):
    """A conference, mentorship cohort, or outreach event open for registration."""
    class Kind(models.TextChoices):
        CONFERENCE = "CONFERENCE", "Conference"
        MENTORSHIP = "MENTORSHIP", "Mentorship Cohort"
        OUTREACH = "OUTREACH", "Humanitarian Outreach"
        WORKSHOP = "WORKSHOP", "Workshop / Gathering"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices,
                            default=Kind.CONFERENCE)
    # Legacy link to a Program "wing" page. Retained for backward
    # compatibility with existing records, but the event editor now links
    # events to the active Programs & Initiatives structure via
    # `initiative` below instead.
    program = models.ForeignKey(Program, null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="events")
    initiative = models.ForeignKey(
        ProgramInitiative, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="events",
        help_text="The Programs & Initiatives page this event belongs to.",
    )
    theme = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    summary = models.CharField(
        max_length=260,
        blank=True,
        help_text="Short public summary used on cards and event detail headers.",
    )
    audience = models.TextField(
        blank=True,
        help_text="Who should attend. Use short paragraphs or bullet-style lines.",
    )
    outcomes = models.TextField(
        blank=True,
        help_text="What participants will leave with. Use one outcome per line.",
    )
    agenda = models.TextField(
        blank=True,
        help_text="Public agenda or run of show. Use one agenda item per line.",
    )
    speakers = models.TextField(
        blank=True,
        help_text="Speaker/facilitator list. Use one person or role per line.",
    )
    preparation = models.TextField(
        blank=True,
        help_text="What participants should bring, complete, or know before attending.",
    )
    accessibility = models.TextField(
        blank=True,
        help_text="Accessibility, interpretation, transport, or inclusion notes.",
    )
    flyer = models.ImageField(upload_to="flyers/", blank=True, null=True)
    starts_at = models.DateTimeField()
    location = models.CharField(max_length=160, default="Virtual Conference")
    venue_address = models.CharField(max_length=240, blank=True)
    online_url = models.URLField(blank=True)
    is_virtual = models.BooleanField(default=True)
    capacity = models.PositiveIntegerField(default=0,
                                           help_text="0 = unlimited")
    registration_note = models.TextField(
        blank=True,
        help_text="Public note shown beside the registration form.",
    )
    contact_email = models.EmailField(blank=True)
    registration_open = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-starts_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200]
            slug, i = base, 2
            while Event.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_upcoming(self):
        return self.starts_at >= timezone.now()

    @cached_property
    def registration_count(self):
        return self.registrations.count()

    @cached_property
    def active_registration_count(self):
        # cached_property (not property): seats_left and is_full both read
        # this, and templates often read it again directly - caching avoids
        # firing the same COUNT query repeatedly for one Event instance.
        return self.registrations.exclude(status="CANCELLED").count()

    @property
    def seats_left(self):
        if not self.capacity:
            return None
        return max(self.capacity - self.active_registration_count, 0)

    @property
    def is_full(self):
        return self.capacity and self.active_registration_count >= self.capacity


class EventContributor(models.Model):
    """A speaker, facilitator, or supporting voice attached to one event."""

    class ContributionType(models.TextChoices):
        KEYNOTE = "KEYNOTE", "Keynote speaker"
        SPEAKER = "SPEAKER", "Speaker"
        FACILITATOR = "FACILITATOR", "Facilitator"
        PANELIST = "PANELIST", "Panelist"
        MODERATOR = "MODERATOR", "Moderator"
        HOST = "HOST", "Host / MC"
        MENTOR = "MENTOR", "Mentor"
        GUEST = "GUEST", "Special guest"
        OTHER = "OTHER", "Other contributor"

    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="contributors"
    )
    name = models.CharField(max_length=160)
    contribution_type = models.CharField(
        max_length=16,
        choices=ContributionType.choices,
        default=ContributionType.SPEAKER,
    )
    role_title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Public professional title or role, such as Founder or Leadership Coach.",
    )
    organisation = models.CharField(max_length=200, blank=True)
    topic = models.CharField(
        max_length=240,
        blank=True,
        help_text="Optional talk, panel, workshop, or session topic.",
    )
    bio = models.TextField(
        blank=True,
        help_text="A concise public biography relevant to this event.",
    )
    photo = models.ImageField(
        upload_to="event-contributors/", blank=True, null=True
    )
    photo_alt_text = models.CharField(
        max_length=200,
        blank=True,
        help_text="Describe the photo for screen-reader users; defaults to the person's name.",
    )
    profile_url = models.URLField(
        blank=True,
        help_text="Optional public profile, organisation, or LinkedIn URL.",
    )
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(
        default=True,
        help_text="Published profiles appear on the public event page.",
    )

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} — {self.get_contribution_type_display()}"
