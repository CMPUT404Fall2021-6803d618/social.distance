# Generated by Django 3.2.9 on 2021-11-26 01:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authors', '0023_auto_20211125_0601'),
    ]

    operations = [
        migrations.AddField(
            model_name='author',
            name='profile_image',
            field=models.URLField(blank=True, max_length=500),
        ),
    ]
