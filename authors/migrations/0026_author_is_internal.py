# Generated by Django 3.2.7 on 2021-11-30 04:02

from django.db import migrations, models

def migrate_internal_users(apps, schema_editor):
    Author = apps.get_model('authors', 'Author')
    for author in Author.objects.all():
        if 'http' in author.id:
            author.is_internal = False
        else:
            author.is_internal = True
        author.save()

class Migration(migrations.Migration):

    dependencies = [
        ('authors', '0025_alter_author_profile_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='author',
            name='is_internal',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(migrate_internal_users),
    ]