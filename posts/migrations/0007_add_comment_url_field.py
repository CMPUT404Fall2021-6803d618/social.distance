# Generated by Django 3.2.7 on 2021-10-10 18:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0006_alter_comment_published_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='url',
            field=models.URLField(default='nothing', editable=False),
            preserve_default=False,
        ),
    ]