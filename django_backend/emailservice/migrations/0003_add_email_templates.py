"""Add email templates for welcome, subscription_update, and subscription_expiry."""
from django.db import migrations


def create_email_templates(apps, schema_editor):
    EmailTemplate = apps.get_model('emailservice', 'EmailTemplate')
    
    # Welcome Email Template
    if not EmailTemplate.objects.filter(key='welcome', locale='en', status='published').exists():
        EmailTemplate.objects.create(
            key='welcome',
            locale='en',
            subject='Welcome to {{ app_name }}! 🎉',
            body_html='''
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #333;">Welcome to {{ app_name }}!</h2>
                <p>Hi {{ first_name }},</p>
                <p>Thank you for signing up! We're excited to have you on board.</p>
                <p>{{ app_name }} helps you manage your daily journals and track your financial transactions effortlessly.</p>
                <h3>Getting Started:</h3>
                <ul>
                    <li>Create your first journal entry</li>
                    <li>Add transactions to track your finances</li>
                    <li>Set up your custom registers</li>
                    <li>Explore subscription plans for advanced features</li>
                </ul>
                <p>If you have any questions, feel free to reach out to our support team.</p>
                <p>Happy journaling! 📝</p>
                <p style="color: #666; font-size: 0.9em;">
                    Best regards,<br>
                    The {{ app_name }} Team
                </p>
            </div>
            ''',
            status='published',
            version=1
        )
    
    # Subscription Update/Warning Email Template
    if not EmailTemplate.objects.filter(key='subscription_update', locale='en', status='published').exists():
        EmailTemplate.objects.create(
            key='subscription_update',
            locale='en',
            subject='⚠️ Your {{ app_name }} Subscription Expires in {{ days_left }} Days',
            body_html='''
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #ff6b35;">Subscription Expiring Soon</h2>
                <p>Hi {{ first_name }},</p>
                <p>This is a reminder that your {{ app_name }} subscription will expire in <strong>{{ days_left }} days</strong> on <strong>{{ expiry_date }}</strong>.</p>
                <p>To continue enjoying uninterrupted access to all premium features, please renew your subscription before it expires.</p>
                <h3>What happens when your subscription expires?</h3>
                <ul>
                    <li>Access to premium features will be restricted</li>
                    <li>Your data remains safe and secure</li>
                    <li>You can renew anytime to restore full access</li>
                </ul>
                <p style="margin-top: 20px;">
                    <a href="#" style="background-color: #ff6b35; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Renew Subscription
                    </a>
                </p>
                <p style="color: #666; font-size: 0.9em; margin-top: 30px;">
                    If you have already renewed, please disregard this email.<br>
                    Questions? Contact our support team.
                </p>
                <p style="color: #666; font-size: 0.9em;">
                    Best regards,<br>
                    The {{ app_name }} Team
                </p>
            </div>
            ''',
            status='published',
            version=1
        )
    
    # Subscription Expiry Email Template
    if not EmailTemplate.objects.filter(key='subscription_expiry', locale='en', status='published').exists():
        EmailTemplate.objects.create(
            key='subscription_expiry',
            locale='en',
            subject='Your {{ app_name }} Subscription Has Expired',
            body_html='''
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #d32f2f;">Subscription Expired</h2>
                <p>Hi {{ first_name }},</p>
                <p>Your {{ app_name }} subscription expired on <strong>{{ expiry_date }}</strong>.</p>
                <p>We hope you enjoyed using our premium features! Your account data is safe, but access to premium features is now limited.</p>
                <h3>Renew to Restore Access:</h3>
                <ul>
                    <li>All premium features</li>
                    <li>Advanced journal management</li>
                    <li>Unlimited transactions</li>
                    <li>Priority support</li>
                </ul>
                <p style="margin-top: 20px;">
                    <a href="#" style="background-color: #d32f2f; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Renew Now
                    </a>
                </p>
                <p style="color: #666; font-size: 0.9em; margin-top: 30px;">
                    Have questions? Our support team is here to help!
                </p>
                <p style="color: #666; font-size: 0.9em;">
                    Thank you for being part of {{ app_name }}!<br>
                    The {{ app_name }} Team
                </p>
            </div>
            ''',
            status='published',
            version=1
        )


def remove_email_templates(apps, schema_editor):
    EmailTemplate = apps.get_model('emailservice', 'EmailTemplate')
    EmailTemplate.objects.filter(key__in=['welcome', 'subscription_update', 'subscription_expiry'], locale='en').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('emailservice', '0002_alter_emailoutbox_id_alter_emailtemplate_id'),
    ]

    operations = [
        migrations.RunPython(create_email_templates, reverse_code=remove_email_templates),
    ]
