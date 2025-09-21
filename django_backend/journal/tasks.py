import redis
import time
from celery import shared_task
from django.conf import settings
from journal.models import Journal
from django.utils import timezone

@shared_task
def create_daily_journals():
    redis_client = redis.StrictRedis.from_url(settings.CELERY_BROKER_URL)

    lock = redis_client.lock("create_daily_journals_lock", timeout=60*5)  # 5 min lock
    have_lock = lock.acquire(blocking=False)

    if not have_lock:
        print("Another worker is already running create_daily_journals. Skipping...")
        return

    try:
        today = timezone.localdate()
        print(f"Running daily journal creation for {today}...")
        print("Creating daily journals...")
        # your journal creation logic
        from django.contrib.auth import get_user_model
        User = get_user_model()

        for user in User.objects.all():
            last_journal = Journal.objects.filter(user=user).order_by("-date").first()
            closing_balance = last_journal.closing_balance if last_journal else user.first_opening_balance
            if(last_journal is None):
                continue
            while last_journal.date < today:
                if (last_journal.date + timezone.timedelta(days=1)).weekday() == 6:
                    last_journal = Journal.objects.create(
                        user=user,
                        date=last_journal.date + timezone.timedelta(days=1),
                        opening_balance=closing_balance,
                        closing_balance=closing_balance,
                        is_holiday=True,
                        holiday_reason="Sunday"
                    )
                    continue
                last_journal = Journal.objects.create(
                    user=user,
                    date=last_journal.date + timezone.timedelta(days=1),
                    opening_balance=closing_balance,
                    closing_balance=closing_balance,
                )
                closing_balance = last_journal.closing_balance

        print("Daily journals created successfully ✅")

    finally:
        lock.release()
