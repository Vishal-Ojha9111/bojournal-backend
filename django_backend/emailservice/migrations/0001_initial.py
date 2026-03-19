"""Initial migration for emailservice app.

Creates EmailTemplate and EmailOutbox models.
"""
from django.db import migrations, models
import django.utils.timezone


def create_defaults(apps, schema_editor):
    EmailTemplate = apps.get_model('emailservice', 'EmailTemplate')
    # Seed a minimal OTP template if not present
    if not EmailTemplate.objects.filter(key='otp', locale='en', status='published').exists():
        EmailTemplate.objects.create(
            key='otp',
            locale='en',
            subject='Your {{ app_name }} verification code',
            body_html='<p>Your OTP is <strong>{{ otp }}</strong>. It is valid for 5 minutes.</p>',
            status='published',
            version=1
        )


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='EmailTemplate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=100, db_index=True)),
                ('locale', models.CharField(default='en', max_length=10)),
                ('subject', models.CharField(max_length=255)),
                ('body_html', models.TextField()),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('published', 'Published')], default='published', max_length=10)),
                ('version', models.PositiveIntegerField(default=1)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'unique_together': {('key', 'locale', 'version')}, 'ordering': ['-updated_at']},
        ),
        migrations.CreateModel(
            name='EmailOutbox',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=100, db_index=True)),
                ('to_email', models.EmailField(max_length=254)),
                ('subject', models.CharField(max_length=255)),
                ('body_html', models.TextField()),
                ('body_text', models.TextField(blank=True, null=True)),
                ('meta', models.JSONField(default=dict, blank=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed')], default='pending', max_length=10, db_index=True)),
                ('attempts', models.PositiveIntegerField(default=0)),
                ('last_error', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'indexes': [models.Index(fields=['status', 'created_at'], name='emailoutbox_status_created_idx')]},
        ),
        migrations.RunPython(create_defaults, reverse_code=migrations.RunPython.noop),
    ]
