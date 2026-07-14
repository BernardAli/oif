from django.db import migrations


def seed_site_branding(apps, schema_editor):
    SiteBranding = apps.get_model("pages", "SiteBranding")
    SiteBranding.objects.get_or_create(
        pk=1,
        defaults={
            "org_name": "Onesimus Impact Foundation",
            "short_name": "OIF",
            "tagline": "Equipping the Next Generation of Global Leaders",
            "founded_year": "2018",
            "location": "Accra, Ghana",
            "contact_email": "hello@onesimusimpact.org",
            "contact_phone": "+233 XXX XXX XXX",
            "website_url": "",
            "footer_blurb": (
                "A youth-led NGO in Accra equipping emerging African leaders "
                "through conferences, mentorship, humanitarian action, and "
                "digital infrastructure."
            ),
            "instagram_url": "",
            "linkedin_url": "",
            "twitter_url": "",
            "youtube_url": "",
            "facebook_url": "",
            "title_font": "DM Sans",
            "body_font": "Roboto",
        },
    )


class Migration(migrations.Migration):
    dependencies = [("pages", "0005_sitebranding_contact_email_and_more")]

    operations = [migrations.RunPython(seed_site_branding, migrations.RunPython.noop)]
