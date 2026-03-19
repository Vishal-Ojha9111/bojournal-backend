import datetime
import logging
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone
from journal.models import Journal
from transactions.models import Transaction
from transactions.serializers import TransactionSerializer

logger = logging.getLogger(__name__)
DEC_ZERO = Decimal("0.00")


def _sum_transactions(user, for_date):
    agg = Transaction.objects.filter(user=user, date=for_date).aggregate(
        total_credit=Sum('amount', filter=Q(transaction_type='credit')),
        total_debit=Sum('amount', filter=Q(transaction_type='debit'))
    )
    credit = agg.get('total_credit') or DEC_ZERO
    debit = agg.get('total_debit') or DEC_ZERO
    return Decimal(credit), Decimal(debit)


def update_journal_for_date(user, start_date):
    """
    Recalculate journals from start_date up to today.
    Uses DB aggregation, select_for_update, and is wrapped in a transaction to avoid races.
    """
    today = timezone.localdate()
    if start_date > today:
        return

    # make date list once
    dates = []
    d = start_date
    while d <= today:
        dates.append(d)
        d += datetime.timedelta(days=1)

    if not dates:
        return

    with transaction.atomic():
        # lock existing journals in the range to prevent concurrent mutation
        existing_qs = Journal.objects.filter(user=user, date__in=dates).select_for_update().order_by('date')
        existing_map = {j.date: j for j in existing_qs}

        # Find previous non-holiday closing:
        prev_date = start_date - datetime.timedelta(days=1)
        prev_closing = None
        any_journal_found = Journal.objects.filter(user=user).exists()
        if not any_journal_found:
            prev_closing = user.first_opening_balance or DEC_ZERO
        else:
            # iterate backward until non-holiday journal found or until no journal exists earlier
            while True:
                prev_j = Journal.objects.filter(user=user, date=prev_date).first()
                if not prev_j:
                    # if we've walked back past any journal, fall back to user's first_opening_balance
                    prev_closing = user.first_opening_balance or DEC_ZERO
                    break
                if not prev_j.is_holiday:
                    prev_closing = prev_j.closing_balance
                    break
                prev_date -= datetime.timedelta(days=1)

        # iterate forward, create missing journals if needed and update balances
        for current in dates:
            journal = existing_map.get(current)
            if not journal:
                # create missing journal (respect Sunday holiday rule)
                if current.weekday() == 6:
                    journal = Journal.objects.create(user=user, date=current, opening_balance=prev_closing,
                                                     closing_balance=prev_closing, is_holiday=True, holiday_reason="Sunday")
                else:
                    journal = Journal.objects.create(user=user, date=current, opening_balance=prev_closing,
                                                     closing_balance=prev_closing)
                existing_map[current] = journal

            # if holiday, closing = opening (no transactions apply)
            if journal.is_holiday:
                prev_closing = journal.closing_balance
                continue

            total_credit, total_debit = _sum_transactions(user, current)

            # Your clarified formula:
            # net_balance = opening_balance + total incoming (credit)
            # closing = net_balance - total outgoing (debit)
            opening = Decimal(journal.opening_balance or prev_closing)
            net_balance = opening + total_credit
            closing = net_balance - total_debit

            # minimize writes
            changed = False
            if journal.opening_balance != opening:
                journal.opening_balance = opening
                changed = True
            if journal.closing_balance != closing:
                journal.closing_balance = closing
                changed = True
            if changed:
                journal.save()

            prev_closing = closing


def create_journal_from_date(user, start_date, opening_balance):
    """
    Create journals from start_date to today. Use bulk_create and prefetch existing dates.
    Consider moving to background job for large ranges.
    """
    today = timezone.localdate()
    if start_date > today:
        return {"status": False, "message": "Cannot create journal for future dates."}

    # Convert opening_balance to Decimal if needed (caller should do this)
    opening_dec = Decimal(opening_balance)

    existing_dates = set(Journal.objects.filter(user=user, date__range=[start_date, today]).values_list('date', flat=True))
    to_create = []
    d = start_date
    while d <= today:
        if d in existing_dates:
            d += datetime.timedelta(days=1)
            continue
        if d.weekday() == 6:
            to_create.append(Journal(user=user, date=d, opening_balance=opening_dec,
                                     closing_balance=opening_dec, is_holiday=True, holiday_reason="Sunday"))
        else:
            to_create.append(Journal(user=user, date=d, opening_balance=opening_dec, closing_balance=opening_dec))
        d += datetime.timedelta(days=1)

    if to_create:
        Journal.objects.bulk_create(to_create)

    journals = list(Journal.objects.filter(user=user, date__range=[start_date, today]).order_by('date'))
    return {"status": True, "message": f"{len(journals)} journal entries present from {start_date} to {today}.", "journals": journals}


def get_full_journal_data(journals_qs, user):
    """
    Efficiently build response for journals:
     - bulk fetch transactions for all relevant dates
     - group transactions by (date, register_name, transaction_type)
     - serialize transactions once
    """
    today = timezone.localdate()
    journals = journals_qs.order_by('date')

    # get user registers
    register_types = list(user.register.all())
    debit_regs = [r.name for r in register_types if r.debit]
    credit_regs = [r.name for r in register_types if r.credit]

    dates = [j.date for j in journals if j.date <= today and not j.is_holiday]
    tx_list = []
    if dates:
        tx_list = list(Transaction.objects.filter(user=user, date__in=dates).select_related('register').order_by('date'))

    # bulk serialize
    serialized_map = {}
    if tx_list:
        serialized = TransactionSerializer(tx_list, many=True).data
        for tx_obj, ser in zip(tx_list, serialized):
            serialized_map[tx_obj.id] = ser

    # group and sum totals
    grouped = {}
    totals_by_date = {}
    for tx in tx_list:
        grouped.setdefault(tx.date, {}).setdefault((tx.register.name, tx.transaction_type), []).append(tx)
        totals_by_date.setdefault(tx.date, {'debit': DEC_ZERO, 'credit': DEC_ZERO})
        if tx.transaction_type == 'debit':
            totals_by_date[tx.date]['debit'] += Decimal(tx.amount)
        else:
            totals_by_date[tx.date]['credit'] += Decimal(tx.amount)

    resp = {'journal': []}
    for journal in journals:
        if journal.date > today:
            break
        if journal.is_holiday:
            resp['journal'].append({"is_holiday": True, "holiday_reason": journal.holiday_reason, "date": journal.date})
            continue

        date_group = grouped.get(journal.date, {})
        total_debit = totals_by_date.get(journal.date, {}).get('debit', DEC_ZERO)
        total_credit = totals_by_date.get(journal.date, {}).get('credit', DEC_ZERO)

        debits_map = {name: [] for name in debit_regs}
        credits_map = {name: [] for name in credit_regs}

        for (reg_name, ttype), txs in date_group.items():
            for tx in txs:
                ser = serialized_map.get(tx.id)
                if ttype == 'debit':
                    debits_map.setdefault(reg_name, []).append(ser)
                else:
                    credits_map.setdefault(reg_name, []).append(ser)

        opening = Decimal(journal.opening_balance or DEC_ZERO)
        net_balance = opening + total_credit       # per your clarification
        closing = net_balance - total_debit

        journal_data = {
            "date": journal.date,
            "opening_balance": opening,
            "debits": debits_map,
            "credits": credits_map,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "net_balance": net_balance,
            "closing_balance": closing,
        }
        resp['journal'].append(journal_data)

    return resp



