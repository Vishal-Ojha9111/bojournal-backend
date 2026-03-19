from __future__ import annotations

from typing import Dict, Any

from celery import shared_task, Task
from celery.utils.log import get_task_logger

from .emailer import send_templated_email_with_fallback
from .models import EmailOutbox

logger = get_task_logger(__name__)


class BaseEmailTask(Task):
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 5, 'countdown': 60}
    retry_backoff = True
    retry_backoff_max = 600
    soft_time_limit = 30


@shared_task(bind=True, base=BaseEmailTask)
def send_email_task(self, payload: Dict[str, Any]):
    """Payload keys: key, to, data, locale, from_email, reply_to, smtp_username, smtp_password, use_ssl, outbox_id"""
    key = payload.get('key')
    to = payload.get('to')
    data = payload.get('data') or {}
    locale = payload.get('locale', 'en')
    outbox_id = payload.get('outbox_id')
    smtp_username = payload.get('smtp_username')
    smtp_password = payload.get('smtp_password')
    from_email = payload.get('from_email')
    reply_to = payload.get('reply_to')
    use_ssl = payload.get('use_ssl', False)

    outbox = None
    if outbox_id:
        try:
            outbox = EmailOutbox.objects.get(pk=outbox_id)
        except EmailOutbox.DoesNotExist:
            outbox = None

    try:
        # Update outbox to pending
        if outbox:
            outbox.status = 'pending'
            outbox.attempts += 1
            outbox.save(update_fields=['status', 'attempts', 'updated_at'])

        # Choose primary send function. For critical sends, allow fallback inside emailer
        result = send_templated_email_with_fallback(
            key,
            to,
            data=data,
            locale=locale,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            from_email=from_email,
            reply_to=reply_to,
            use_ssl=use_ssl,
        )

        if outbox:
            outbox.status = 'sent'
            outbox.subject = result.get('rendered_subject', outbox.subject)
            outbox.body_html = result.get('rendered_html', outbox.body_html)
            outbox.body_text = result.get('rendered_text', outbox.body_text)
            outbox.save()

        logger.info('Email sent %s -> %s', key, to)
        return True
    except Exception as exc:
        logger.exception('send_email_task failed for %s -> %s', key, to)
        if outbox:
            outbox.status = 'failed'
            outbox.last_error = str(exc)
            outbox.save()
        raise
