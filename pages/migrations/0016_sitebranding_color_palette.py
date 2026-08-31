from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("pages", "0015_event_initiative")]

    operations = [
        migrations.AddField(
            model_name="sitebranding",
            name="color_palette",
            field=models.CharField(
                choices=[
                    ("heritage", "Heritage Coffee"),
                    ("forest", "Forest & Gold"),
                    ("navy", "Navy & Gold"),
                    ("burgundy", "Burgundy & Sand"),
                    ("teal", "Teal & Copper"),
                    ("royal", "Royal Purple & Gold"),
                    ("sunrise", "Sunrise & Charcoal"),
                    ("ocean", "Ocean & Coral"),
                    ("sage", "Sage & Terracotta"),
                    ("midnight", "Midnight & Cyan"),
                    ("plum", "Plum & Rose"),
                    ("emerald", "Emerald & Ivory"),
                    ("slate", "Slate & Amber"),
                    ("cocoa", "Cocoa & Blush"),
                    ("azure", "Azure & Lime"),
                    ("oif_deliverables", "OIF Deliverables"),
                    ("onesimus_logo", "Onesimus Navy & Gold"),
                ],
                default="heritage",
                help_text="Coordinated colors used across the public website and dashboard.",
                max_length=24,
            ),
        ),
    ]
