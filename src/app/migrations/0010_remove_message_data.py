# Generated by Django 5.1.2 on 2024-11-10 07:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0009_message_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='message',
            name='data',
        ),
    ]