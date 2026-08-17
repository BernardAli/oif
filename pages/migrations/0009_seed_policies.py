from django.db import migrations


POLICY_SPECS = [
    ("privacy", "Privacy Policy",
     "Onesimus Impact Foundation collects only the personal data needed "
     "to deliver our programmes — such as your name, contact details and "
     "application information.\n\nWe act as the data controller for this "
     "information and process it in line with the Data Protection Act, "
     "2012 (Act 843) of Ghana.\n\nThis is placeholder text to be replaced "
     "with the Foundation's final, legally reviewed privacy notice."),
    ("terms", "Terms of Use",
     "By using this website you agree to use it lawfully and to respect "
     "the intellectual property of the Onesimus Impact Foundation.\n\n"
     "This is placeholder text to be replaced with the Foundation's final "
     "terms of use."),
    ("donation", "Donation Policy",
     "Donations to the Onesimus Impact Foundation support conferences, "
     "mentorship and humanitarian work. Gifts are processed securely "
     "through Paystack (mobile money and card) or by bank transfer.\n\n"
     "Donations are generally non-refundable except where a transaction "
     "was made in error.\n\nThis is placeholder text to be replaced with "
     "the Foundation's final donation policy."),
]


def seed_policies(apps, schema_editor):
    """Guarantee /policy/privacy/, /policy/terms/, and /policy/donation/
    always resolve, even on a fresh database, instead of 404ing until an
    admin manually creates them from Site CMS -> Policies."""
    Policy = apps.get_model("pages", "Policy")
    for kind, title, body in POLICY_SPECS:
        Policy.objects.get_or_create(
            kind=kind, defaults={"title": title, "body": body, "is_placeholder": True},
        )


class Migration(migrations.Migration):
    dependencies = [("pages", "0008_sitepagecopy")]

    operations = [migrations.RunPython(seed_policies, migrations.RunPython.noop)]
