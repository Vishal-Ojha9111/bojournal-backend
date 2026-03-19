import logging
import redis
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from emailservice.dispatcher import enqueue_email

logger = logging.getLogger(__name__)
User = get_user_model()

REDIS_URL = getattr(settings, 'REDIS_LOCK_URL', getattr(settings, 'CELERY_BROKER_URL', None))
LOCK_KEY = getattr(settings, 'UPDATE_SUBSCRIPTION_LOCK_KEY', 'update_subscription_lock')
LOCK_TIMEOUT = int(getattr(settings, 'UPDATE_SUBSCRIPTION_LOCK_TIMEOUT', 60 * 5))
# days before expiry to warn the user
WARNING_DAYS = int(getattr(settings, 'SUBSCRIPTION_WARNING_DAYS', 3))

def _enqueue_expiry_email(user):
    """
    Send subscription expiry notification email.
    Uses emailservice with high priority (sent in bulk at midnight).
    """
    try:
        enqueue_email(
            key='subscription_expiry',
            to_email=user.email,
            data={
                'first_name': user.first_name,
                'last_name': user.last_name,
                'app_name': 'BO Journal',
                'expiry_date': user.subscription_end_date.strftime('%B %d, %Y') if user.subscription_end_date else 'N/A'
            },
            priority='high',  # High priority for subscription notifications
            locale='en'
        )
        logger.info(f"Enqueued expiry email for user {user.email}")
    except Exception as e:
        logger.exception(f"Failed to enqueue expiry email for user {user.email}: {e}")

def _enqueue_warning_email(user, days_left):
    """
    Send subscription expiry warning email.
    Uses emailservice with high priority.
    """
    try:
        enqueue_email(
            key='subscription_update',
            to_email=user.email,
            data={
                'first_name': user.first_name,
                'last_name': user.last_name,
                'app_name': 'BO Journal',
                'days_left': days_left,
                'expiry_date': user.subscription_end_date.strftime('%B %d, %Y') if user.subscription_end_date else 'N/A'
            },
            priority='high',  # High priority for subscription warnings
            locale='en'
        )
        logger.info(f"Enqueued warning email for user {user.email} ({days_left} days left)")
    except Exception as e:
        logger.exception(f"Failed to enqueue warning email for user {user.email}: {e}")

@shared_task
def update_subscription():
    if not REDIS_URL:
        logger.error("Redis URL not configured for subscription updater; aborting.")
        return

    redis_client = redis.StrictRedis.from_url(REDIS_URL)
    lock = redis_client.lock(LOCK_KEY, timeout=LOCK_TIMEOUT)
    have_lock = lock.acquire(blocking=False)

    if not have_lock:
        logger.info("Another worker is already running update_subscription. Skipping...")
        return

    started = timezone.now()
    total_processed = 0
    total_expired = 0
    total_failed = 0

    try:
        today = timezone.localdate()
        logger.info("Running update_subscription for %s", today)

        # Expire subscriptions: filter in DB
        expiring_users_qs = User.objects.filter(subscription_active=True, subscription_end_date__lt=today)

        for user in expiring_users_qs.select_related():
            total_processed += 1
            try:
                with transaction.atomic():
                    # Double-check in transaction if needed
                    # Use update on model instance to ensure signals fire if any
                    user.subscription_active = False
                    user.save(update_fields=['subscription_active'])
                    total_expired += 1

                # enqueue expiry email (do not block)
                _enqueue_expiry_email(user)
            except Exception:
                total_failed += 1
                logger.exception("Failed to expire subscription for user_id=%s", user.id)
                continue

        # Warning emails: users whose end_date == today + WARNING_DAYS
        if WARNING_DAYS > 0:
            warn_date = today + timezone.timedelta(days=WARNING_DAYS)
            warn_qs = User.objects.filter(subscription_active=True, subscription_end_date=warn_date)
            for user in warn_qs:
                try:
                    _enqueue_warning_email(user, WARNING_DAYS)
                except Exception:
                    logger.exception("Failed to enqueue warning email for user_id=%s", user.id)

        duration = timezone.now() - started
        logger.info("update_subscription completed: processed=%s expired=%s failed=%s duration=%s",
                    total_processed, total_expired, total_failed, duration)

    finally:
        try:
            if have_lock:
                lock.release()
        except Exception:
            logger.exception("Failed to release lock %s", LOCK_KEY)
