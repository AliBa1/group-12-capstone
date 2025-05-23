# Generated by Django 5.1.2 on 2025-04-21 06:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0037_property_house_rating"),
    ]

    operations = [
        migrations.CreateModel(
            name="Place",
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
                ("place_id", models.CharField(max_length=100, unique=True)),
                ("name", models.CharField(max_length=255)),
                ("type", models.CharField(blank=True, max_length=100)),
                ("photo_references", models.JSONField(blank=True, null=True)),
                ("formatted_address", models.CharField(max_length=255)),
                ("latitude", models.FloatField()),
                ("longitude", models.FloatField()),
                (
                    "google_place_id",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("google_address", models.TextField(blank=True, null=True)),
                ("google_rating", models.FloatField(blank=True, null=True)),
            ],
        ),
    ]
