from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0012_align_programs_writeup"),
    ]

    operations = [
        migrations.CreateModel(
            name="EventContributor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("contribution_type", models.CharField(choices=[("KEYNOTE", "Keynote speaker"), ("SPEAKER", "Speaker"), ("FACILITATOR", "Facilitator"), ("PANELIST", "Panelist"), ("MODERATOR", "Moderator"), ("HOST", "Host / MC"), ("MENTOR", "Mentor"), ("GUEST", "Special guest"), ("OTHER", "Other contributor")], default="SPEAKER", max_length=16)),
                ("role_title", models.CharField(blank=True, help_text="Public professional title or role, such as Founder or Leadership Coach.", max_length=200)),
                ("organisation", models.CharField(blank=True, max_length=200)),
                ("topic", models.CharField(blank=True, help_text="Optional talk, panel, workshop, or session topic.", max_length=240)),
                ("bio", models.TextField(blank=True, help_text="A concise public biography relevant to this event.")),
                ("photo", models.ImageField(blank=True, null=True, upload_to="event-contributors/")),
                ("photo_alt_text", models.CharField(blank=True, help_text="Describe the photo for screen-reader users; defaults to the person's name.", max_length=200)),
                ("profile_url", models.URLField(blank=True, help_text="Optional public profile, organisation, or LinkedIn URL.")),
                ("order", models.PositiveIntegerField(default=0)),
                ("is_published", models.BooleanField(default=True, help_text="Published profiles appear on the public event page.")),
                ("event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="contributors", to="pages.event")),
            ],
            options={"ordering": ["order", "name"]},
        ),
    ]
