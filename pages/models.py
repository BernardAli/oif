"""Database-driven content for the public OIF site."""
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
    program = models.ForeignKey(Program, null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="events")
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

    @property
    def registration_count(self):
        return self.registrations.count()

    @property
    def active_registration_count(self):
        return self.registrations.exclude(status="CANCELLED").count()

    @property
    def seats_left(self):
        if not self.capacity:
            return None
        return max(self.capacity - self.active_registration_count, 0)

    @property
    def is_full(self):
        return self.capacity and self.active_registration_count >= self.capacity
