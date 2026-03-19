import logging
import datetime
from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.db.models import OuterRef, Subquery
import redis

from django.contrib.auth import get_user_model
from journal.models import Journal

logger = logging.getLogger(__name__)
User = get_user_model()

# Config
LOCK_KEY = getattr(settings, 'JOURNAL_DAILY_LOCK_KEY', 'create_daily_journals_lock')
LOCK_TIMEOUT = int(getattr(settings, 'JOURNAL_DAILY_LOCK_TIMEOUT', 60 * 5))
MAX_DAYS_PER_USER = int(getattr(settings, 'JOURNAL_MAX_DAYS_SYNC', 100))  # avoid huge synchronous gaps
REDIS_URL = getattr(settings, 'REDIS_LOCK_URL', getattr(settings, 'CELERY_BROKER_URL', None))


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def create_daily_journals(self):
    if not REDIS_URL:
        logger.error("No Redis URL configured for journal creation lock.")
        return

    redis_client = redis.StrictRedis.from_url(REDIS_URL)
    lock = redis_client.lock(LOCK_KEY, timeout=LOCK_TIMEOUT)
    have_lock = lock.acquire(blocking=False)

    if not have_lock:
        logger.info("create_daily_journals: another worker holds the lock; skipping this run.")
        return

    started_at = timezone.now()
    created_total = 0
    failed_total = 0
    try:
        today = timezone.localdate()
        logger.info("create_daily_journals: started for %s", today)

        # Annotate users with last journal date (subquery)
        last_journal_subq = Journal.objects.filter(user=OuterRef('pk'), date__lt=today).order_by('-date').values('date')[:1]
        users = User.objects.filter(subscription_active=True).annotate(last_journal_date=Subquery(last_journal_subq))

        for user in users:
            try:
                if not user.last_journal_date:
                    # No previous journal; skip (initial creation should be handled elsewhere)
                    continue

                # compute how many days to create, enforce max limit
                last_date = user.last_journal_date
                days_to_create = (today - last_date).days
                if days_to_create <= 0:
                    continue
                if days_to_create > MAX_DAYS_PER_USER:
                    logger.warning("User %s needs %s days creation; limiting to %s and scheduling backfill.",
                                   user.id, days_to_create, MAX_DAYS_PER_USER)
                    # Optionally schedule a backfill task and skip or limit here
                    days_to_create = MAX_DAYS_PER_USER

                # gather new Journal objects for bulk create
                to_create = []
                closing_balance = Journal.objects.filter(user=user, date=last_date).values_list('closing_balance', flat=True).first()
                if closing_balance is None:
                    closing_balance = user.first_opening_balance or 0

                current_date = last_date
                for _ in range(days_to_create):
                    next_date = current_date + datetime.timedelta(days=1)
                    # build Journal instance
                    if next_date.weekday() == 6:
                        j = Journal(user=user, date=next_date, opening_balance=closing_balance,
                                    closing_balance=closing_balance, is_holiday=True, holiday_reason="Sunday")
                    else:
                        j = Journal(user=user, date=next_date, opening_balance=closing_balance, closing_balance=closing_balance)
                    to_create.append(j)
                    current_date = next_date

                # persist in a transaction with batch size for optimal performance
                with transaction.atomic():
                    Journal.objects.bulk_create(to_create, batch_size=1000)
                created_total += len(to_create)
            except Exception as e:
                failed_total += 1
                logger.exception("Failed creating journals for user %s: %s", user.id, e)
                # continue with next user

        duration = timezone.now() - started_at
        logger.info("create_daily_journals: finished. created=%s, failed=%s, duration=%s", created_total, failed_total, duration)
    finally:
        try:
            lock.release()
        except Exception:
            logger.exception("Failed to release lock %s", LOCK_KEY)
