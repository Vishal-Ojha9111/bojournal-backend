import logging
from typing import Dict, Any, Optional

from .models import EmailOutbox
from .tasks import send_email_task

logger = logging.getLogger(__name__)


# Priority Queue Mapping:
# - critical: OTP emails (immediate, user is waiting)
# - high: Subscription updates (important, time-sensitive)
# - low: Welcome emails (informational, can wait)
PRIORITY_QUEUE = {
    'critical': 'critical',  # OTP emails - highest priority
    'high': 'high',          # Subscription updates - medium priority
    'low': 'low'             # Welcome emails - lowest priority
}


def enqueue_email(
    key: str,
    to_email: str,
    data: Optional[Dict[str, Any]] = None,
    locale: str = 'en',
    priority: str = 'low',  # Default to lowest priority
    smtp_username: Optional[str] = None,
    smtp_password: Optional[str] = None,
    from_email: Optional[str] = None,
    reply_to: Optional[str] = None,
    use_ssl: bool = False,
    use_outbox: bool = True,
) -> EmailOutbox:
    """Create an outbox record and enqueue a Celery task to send the email.

    Returns the created EmailOutbox instance.
    """
    outbox = None
    if use_outbox:
        outbox = EmailOutbox.objects.create(
            key=key,
            to_email=to_email,
            subject='(pending)',
            body_html='',
            body_text='',
            meta={'locale': locale},
        )

    payload = {
        'key': key,
        'to': to_email,
        'data': data or {},
        'locale': locale,
        'from_email': from_email,
        'reply_to': reply_to,
        'smtp_username': smtp_username,
        'smtp_password': smtp_password,
        'use_ssl': use_ssl,
        'outbox_id': outbox.id if outbox is not None else None,
    }

    queue = PRIORITY_QUEUE.get(priority, 'low')  # Default to low priority if invalid
    send_email_task.apply_async((payload,), queue=queue)
    logger.info('Enqueued email %s to %s on %s queue', key, to_email, queue)
    return outbox
