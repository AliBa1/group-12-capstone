# Generated by Django 5.1.2 on 2024-11-12 08:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0014_hotel_google_address_hotel_google_place_id_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='hotel',
            name='photo_url',
        ),
        migrations.AddField(
            model_name='hotel',
            name='photo_urls',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
