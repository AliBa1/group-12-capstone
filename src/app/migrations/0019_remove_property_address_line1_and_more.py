# Generated by Django 5.1.2 on 2024-12-04 04:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0018_listingagent_listingoffice_property_propertyhistory'),
    ]

    operations = [

        migrations.AlterField(
            model_name='property',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
