# Generated by Django 3.2.7 on 2021-10-04 02:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0002_add_visibility'),
    ]

    operations = [
        migrations.AlterField(
            model_name='post',
            name='published',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
