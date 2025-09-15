import datetime
from django.utils import timezone
from journal.models import Journal
from transactions.models import Transaction
from decimal import Decimal
from transactions.serializers import TransactionSerializer
from authapp.models import User


def update_journal_for_date(user, date):
    today = timezone.localtime().date()

    def get_transaction_totals(user, for_date):
        transactions = Transaction.objects.filter(user=user, date=for_date)

        totals = {
            'credit': Decimal("0.00"),
            'debit': Decimal("0.00"),
        }

        for tx in transactions:
            if tx.transaction_type == 'credit':
                totals["credit"] += tx.amount
            elif tx.transaction_type == 'debit':
                totals["debit"] += tx.amount

        return totals

    def update_journal_entry(user, journal_date, opening_balance):
        totals = get_transaction_totals(user, journal_date)
        net = totals['credit'] - totals['debit']
        closing = opening_balance + net

        journal = Journal.objects.get(user=user, date=journal_date)

        journal.opening_balance = opening_balance
        journal.closing_balance = closing
        journal.save()

        return closing
    
    def get_prev_closing_not_holiday(date):
        prev_date = date - datetime.timedelta(days=1)
        journal = Journal.objects.filter(user=user,date=prev_date).first()
        if not journal:
            return user.first_opening_balance

        if journal and journal.is_holiday:
            date -= datetime.timedelta(days=1)
            return get_prev_closing_not_holiday(date)
        elif journal:
            return journal.closing_balance
        

    current_date = date
    prev_closing = None

    while current_date <= today:
        if not prev_closing:
            prev_closing = get_prev_closing_not_holiday(date=current_date)

        prev_closing = update_journal_entry(user, current_date, prev_closing)

        current_date += datetime.timedelta(days=1)


def create_journal_from_date(user, date, opening_balance):
    today = timezone.localtime().date()

    if date > today:
        return {
            "status": False,
            "message": "Cannot create journal for future dates."
        }

    journal_entries = []
    current_date = date

    while current_date <= today:
        # Skip Sundays
        if current_date.weekday() == 6:
            journal = Journal.objects.create(
                user=user,
                date=current_date,
                opening_balance=opening_balance,
                closing_balance=opening_balance,
                is_holiday=True,
                holiday_reason="Sunday"
            )
            journal_entries.append(journal)
            current_date += datetime.timedelta(days=1)
            continue

        if Journal.objects.filter(user=user, date=current_date, is_holiday=True).exists():
            current_date += datetime.timedelta(days=1)
            continue

        # Avoid duplicates
        if not Journal.objects.filter(user=user, date=current_date).exists():
            journal = Journal.objects.create(
                user=user,
                date=current_date,
                opening_balance=opening_balance,
                closing_balance=opening_balance,
            )
            journal_entries.append(journal)

        current_date += datetime.timedelta(days=1)

    return {
        "status": True,
        "message": f"{len(journal_entries)} journal entries created from {date} to {today}.",
        "journals": journal_entries
    }


def get_full_journal_data(journals, user):
    response_data = {"journal":[]}

    for journal in journals:
        if journal.date > timezone.localtime().date():
            break
        if journal.is_holiday:
            journal_data = {
                "is_holiday":True,
                "holiday_reason":journal.holiday_reason,
                "date": journal.date,
            }
            response_data['journal'].append(journal_data)
            continue
   
        journal_data = {
            "date": journal.date,
            "opening_balance": journal.opening_balance,
            "debits": {reg_type:[] for reg_type in user.register_types},
            "credits": {reg_type:[] for reg_type in user.register_types},
            "total_debit": 0,
            "total_credit": 0,
            "closing_balance": journal.closing_balance,
        }

        transactions = Transaction.objects.filter(user=user, date=journal.date)

        for reg_type in user.register_types:
            for tx in transactions:
                if tx.register == reg_type:
                    serialized_tx = TransactionSerializer(tx).data
                    if tx.transaction_type == 'debit':
                        journal_data["debits"][reg_type].append(serialized_tx)
                        journal_data["total_debit"] += tx.amount
                    elif tx.transaction_type == 'credit':
                        journal_data["credits"][reg_type].append(serialized_tx)
                        journal_data["total_credit"] += tx.amount
        journal_data['net_balance'] = journal_data['opening_balance'] + journal_data['total_credit']

        journal_data["closing_balance"] = journal_data['net_balance'] - journal_data['total_debit']

        response_data['journal'].append(journal_data)
            

    return response_data



