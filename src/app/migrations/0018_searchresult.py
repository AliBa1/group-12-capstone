# Generated by Django 5.1.2 on 2024-11-24 03:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0017_remove_hotel_photo_url_hotel_photo_references"),
    ]

    operations = [
        migrations.CreateModel(
            name="SearchResult",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("additional_data", models.JSONField(blank=True, null=True)),
                ("text", models.TextField(max_length=2500)),
            ],
        ),
    ]
