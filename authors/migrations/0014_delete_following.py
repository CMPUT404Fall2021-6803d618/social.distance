# Generated by Django 3.2.7 on 2021-10-17 05:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('authors', '0013_auto_20211017_0513'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Following',
        ),
    ]