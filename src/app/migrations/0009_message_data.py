# Generated by Django 5.1.2 on 2024-11-10 07:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0008_merge_20241109_1203'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='data',
            field=models.JSONField(blank=True, null=True),
        ),
    ]