# Generated by Django 5.1.2 on 2024-11-24 04:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0018_searchresult"),
    ]

    operations = [
        migrations.DeleteModel(
            name="SearchResult",
        ),
    ]