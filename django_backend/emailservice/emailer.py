"""Email rendering and SMTP sending utilities.

This module provides send_templated_email and an optional fallback hook.
All secrets are read from environment variables when enqueueing or calling send.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
import os
from email.message import EmailMessage
from typing import Dict, Any, Optional

from jinja2 import Environment, StrictUndefined, select_autoescape
from bs4 import BeautifulSoup
from django.conf import settings
from .models import EmailTemplate

logger = logging.getLogger(__name__)


def _get_template(key: str, locale: str = 'en') -> EmailTemplate:
    # Try exact locale, fallback to 'en'
    tmpl = EmailTemplate.objects.filter(key=key, locale=locale, status='published').order_by('-version').first()
    if tmpl:
        return tmpl
    tmpl = EmailTemplate.objects.filter(key=key, locale='en', status='published').order_by('-version').first()
    if not tmpl:
        raise LookupError(f"Published template not found for key={key}, locale={locale}")
    return tmpl


def _render(template_str: str, data: Dict[str, Any]) -> str:
    env = Environment(undefined=StrictUndefined, autoescape=select_autoescape(['html', 'xml']))
    tpl = env.from_string(template_str)
    return tpl.render(**(data or {}))


def _html_to_text(html: str) -> str:
    # Use BeautifulSoup to generate readable plaintext
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(separator='\n')
    lines = [l.strip() for l in text.splitlines()]
    return '\n'.join([l for l in lines if l])


def send_templated_email(
    template_key: str,
    to_email: str,
    data: Optional[Dict[str, Any]] = None,
    locale: str = 'en',
    smtp_username: Optional[str] = None,
    smtp_password: Optional[str] = None,
    from_email: Optional[str] = None,
    reply_to: Optional[str] = None,
    use_ssl: bool = False,
    timeout: int = 20,
) -> Dict[str, Any]:
    """Render a template and send via SMTP (Namecheap Private Email defaults).

    Returns a dict: {sent: bool, template_version: int, locale_used: str}
    Raises LookupError on missing template or UndefinedError for missing variables.
    Raises RuntimeError on SMTP misconfiguration or send failure.
    """
    tmpl = _get_template(template_key, locale)
    rendered_subject = _render(tmpl.subject, data or {})
    rendered_html = _render(tmpl.body_html, data or {})
    rendered_text = _html_to_text(rendered_html)

    # Determine SMTP credentials from params or env
    smtp_user = smtp_username or os.getenv('SMTP_USERNAME') or getattr(settings, 'EMAIL_HOST_USER', None)
    smtp_pass = smtp_password or os.getenv('SMTP_PASSWORD') or getattr(settings, 'EMAIL_HOST_PASSWORD', None)
    if not smtp_user or not smtp_pass:
        raise RuntimeError('SMTP credentials not provided via args or environment')

    host = os.getenv('SMTP_HOST', 'mail.privateemail.com')
    port = int(os.getenv('SMTP_PORT', os.getenv('EMAIL_PORT', '587')))

    from_addr = from_email or os.getenv('EMAIL_FROM') or getattr(settings, 'DEFAULT_FROM_EMAIL', smtp_user)

    msg = EmailMessage()
    msg['Subject'] = rendered_subject
    msg['From'] = from_addr
    msg['To'] = to_email
    if reply_to:
        msg['Reply-To'] = reply_to
    msg.set_content(rendered_text)
    msg.add_alternative(rendered_html, subtype='html')

    try:
        if use_ssl or port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=context, timeout=timeout) as server:
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
    except Exception as e:
        logger.exception('SMTP send failed')
        raise

    return {
        'sent': True,
        'template_version': tmpl.version,
        'locale_used': tmpl.locale,
        'rendered_subject': rendered_subject,
        'rendered_html': rendered_html,
        'rendered_text': rendered_text,
    }


def send_templated_email_with_fallback(*args, **kwargs):
    """Attempt primary send, on failure try fallback if configured. For critical sends only."""
    try:
        return send_templated_email(*args, **kwargs)
    except Exception:
        # Try fallback via SendGrid SMTP if API key present
        sg_api_key = os.getenv('SG_API_KEY')
        if not sg_api_key:
            raise
        # Fallback: use SendGrid SMTP relay settings if available in env
        fallback_user = os.getenv('SG_SMTP_USER')
        fallback_pass = os.getenv('SG_SMTP_PASS') or sg_api_key
        kwargs['smtp_username'] = fallback_user
        kwargs['smtp_password'] = fallback_pass
        logger.info('Falling back to SendGrid SMTP relay')
        return send_templated_email(*args, **kwargs)
