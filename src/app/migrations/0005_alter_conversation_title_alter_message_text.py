# Generated by Django 5.1.2 on 2024-11-03 18:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0004_alter_conversation_user"),
    ]

    operations = [
        migrations.AlterField(
            model_name="conversation",
            name="title",
            field=models.CharField(max_length=60, unique=True),
        ),
        migrations.AlterField(
            model_name="message",
            name="text",
            field=models.TextField(max_length=2500),
        ),
    ]