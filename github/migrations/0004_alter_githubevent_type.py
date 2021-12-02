# Generated by Django 3.2.8 on 2021-12-02 01:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('github', '0003_alter_githubevent_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='githubevent',
            name='type',
            field=models.CharField(choices=[('PushEvent', 'Push Event'), ('CreateEvent', 'Create Event'), ('DeleteEvent', 'Delete Event'), ('WatchEvent', 'Watch Event'), ('ForkEvent', 'Fork Event')], max_length=30),
        ),
    ]
