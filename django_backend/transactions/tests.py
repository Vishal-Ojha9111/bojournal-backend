"""
Comprehensive test cases for transactions module.

Tests cover:
- Transaction CRUD operations
- Atomic transactions with journal updates
- Permissions and ownership
- Transaction type validation (debit/credit)
- Register relationship
- Date-based filtering
- Image key storage
"""

import jwt
from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from datetime import date, timedelta

from authapp.models import User
from transactions.models import Transaction
from registers.models import Register
from journal.models import Journal


def generate_test_token(user):
    """Helper function to generate JWT token for testing."""
    now = timezone.now()
    exp = now + timedelta(days=3)
    payload = {
        'user_id': user.id,
        'email': user.email,
        'iat': int(now.timestamp()),
        'exp': int(exp.timestamp()),
        'type': 'access'
    }
    secret = settings.JWT_SECRET if hasattr(settings, 'JWT_SECRET') else 'test_secret'
    token = jwt.encode(payload, secret, algorithm='HS256')
    return token


class TransactionModelTests(TestCase):
    """Test Transaction model functionality."""

    def setUp(self):
        """Set up test user, register, and transaction data."""
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            
        )
        
        self.register = Register.objects.create(
            user=self.user,
            name='Cash',
            debit=True,
            credit=True
        )
        
        self.today = date.today()

    def test_transaction_creation_debit(self):
        """Test creating a debit transaction."""
        transaction = Transaction.objects.create(
            user=self.user,
            amount=Decimal('500.00'),
            transaction_type='debit',
            date=self.today,
            register=self.register,
            description='Test expense'
        )
        self.assertEqual(transaction.user, self.user)
        self.assertEqual(transaction.amount, Decimal('500.00'))
        self.assertEqual(transaction.transaction_type, 'debit')
        self.assertEqual(transaction.register, self.register)

    def test_transaction_creation_credit(self):
        """Test creating a credit transaction."""
        transaction = Transaction.objects.create(
            user=self.user,
            amount=Decimal('1000.00'),
            transaction_type='credit',
            date=self.today,
            register=self.register,
            description='Test income'
        )
        self.assertEqual(transaction.transaction_type, 'credit')
        self.assertEqual(transaction.amount, Decimal('1000.00'))

    def test_transaction_with_image_keys(self):
        """Test transaction with image keys."""
        image_keys = ['transactions/receipt1.jpg', 'transactions/receipt2.jpg']
        transaction = Transaction.objects.create(
            user=self.user,
            amount=Decimal('250.00'),
            transaction_type='debit',
            date=self.today,
            register=self.register,
            image_keys=image_keys
        )
        self.assertEqual(transaction.image_keys, image_keys)

    def test_transaction_ordering(self):
        """Test that transactions are ordered by date and created_at."""
        trans1 = Transaction.objects.create(
            user=self.user,
            amount=Decimal('100.00'),
            transaction_type='debit',
            date=self.today - timedelta(days=2),
            register=self.register
        )
        trans2 = Transaction.objects.create(
            user=self.user,
            amount=Decimal('200.00'),
            transaction_type='credit',
            date=self.today,
            register=self.register
        )
        trans3 = Transaction.objects.create(
            user=self.user,
            amount=Decimal('150.00'),
            transaction_type='debit',
            date=self.today - timedelta(days=1),
            register=self.register
        )
        
        transactions = Transaction.objects.all()
        self.assertEqual(transactions[0], trans2)  # Most recent date
        self.assertEqual(transactions[1], trans3)
        self.assertEqual(transactions[2], trans1)  # Oldest date


class TransactionAPITests(APITestCase):
    """Test Transaction API endpoints."""

    def setUp(self):
        """Set up test client and users."""
        self.client = APIClient()
        cache.clear()
        
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            
            first_opening_balance=Decimal('5000.00')
        )
        
        self.other_user = User.objects.create_user(
            email='otheruser@example.com',
            password='testpass123',
            first_name='Other',
            last_name='User',
            
            first_opening_balance=Decimal('3000.00')
        )
        
        self.register = Register.objects.create(
            user=self.user,
            name='Cash',
            debit=True,
            credit=True
        )
        
        self.other_register = Register.objects.create(
            user=self.other_user,
            name='Bank',
            debit=True,
            credit=True
        )
        
        self.token = generate_test_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        self.today = date.today()
        self.list_url = '/api/v2/transactions/'

    def test_list_transactions_authenticated(self):
        """Test listing transactions for authenticated user."""
        Transaction.objects.create(
            user=self.user,
            amount=Decimal('500.00'),
            transaction_type='debit',
            date=self.today,
            register=self.register
        )
        Transaction.objects.create(
            user=self.user,
            amount=Decimal('1000.00'),
            transaction_type='credit',
            date=self.today,
            register=self.register
        )
        
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_list_transactions_unauthenticated(self):
        """Test that unauthenticated users cannot list transactions."""
        self.client.credentials()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_only_sees_own_transactions(self):
        """Test that users only see their own transactions."""
        Transaction.objects.create(
            user=self.user,
            amount=Decimal('500.00'),
            transaction_type='debit',
            date=self.today,
            register=self.register
        )
        Transaction.objects.create(
            user=self.other_user,
            amount=Decimal('1000.00'),
            transaction_type='credit',
            date=self.today,
            register=self.other_register
        )
        
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['user'], self.user.id)

    def test_create_debit_transaction(self):
        """Test creating a debit transaction."""
        data = {
            'amount': '500.00',
            'transaction_type': 'debit',
            'date': str(self.today),
            'register': self.register.id,
            'description': 'Grocery shopping'
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Transaction.objects.count(), 1)
        
        transaction = Transaction.objects.first()
        self.assertEqual(transaction.user, self.user)
        self.assertEqual(transaction.transaction_type, 'debit')

    def test_create_credit_transaction(self):
        """Test creating a credit transaction."""
        data = {
            'amount': '2000.00',
            'transaction_type': 'credit',
            'date': str(self.today),
            'register': self.register.id,
            'description': 'Salary'
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        transaction = Transaction.objects.first()
        self.assertEqual(transaction.transaction_type, 'credit')

    def test_create_transaction_with_images(self):
        """Test creating transaction with image keys."""
        data = {
            'amount': '350.00',
            'transaction_type': 'debit',
            'date': str(self.today),
            'register': self.register.id,
            'image_keys': ['transactions/receipt1.jpg']
        }
        
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        transaction = Transaction.objects.first()
        self.assertIsNotNone(transaction.image_keys)
        self.assertEqual(len(transaction.image_keys), 1)

    def test_create_transaction_invalid_type(self):
        """Test that invalid transaction type fails."""
        data = {
            'amount': '500.00',
            'transaction_type': 'invalid',
            'date': str(self.today),
            'register': self.register.id
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_transaction_negative_amount(self):
        """Test that negative amount fails."""
        data = {
            'amount': '-500.00',
            'transaction_type': 'debit',
            'date': str(self.today),
            'register': self.register.id
        }
        
        response = self.client.post(self.list_url, data)
        # Should fail validation
        self.assertNotEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_transaction(self):
        """Test updating a transaction."""
        transaction = Transaction.objects.create(
            user=self.user,
            amount=Decimal('500.00'),
            transaction_type='debit',
            date=self.today,
            register=self.register
        )
        
        update_url = f'{self.list_url}{transaction.id}/'
        data = {
            'amount': '750.00',
            'transaction_type': 'debit',
            'date': str(self.today),
            'register': self.register.id,
            'description': 'Updated description'
        }
        
        response = self.client.put(update_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        transaction.refresh_from_db()
        self.assertEqual(transaction.amount, Decimal('750.00'))
        self.assertEqual(transaction.description, 'Updated description')

    def test_partial_update_transaction(self):
        """Test partially updating a transaction."""
        transaction = Transaction.objects.create(
            user=self.user,
            amount=Decimal('500.00'),
            transaction_type='debit',
            date=self.today,
            register=self.register
        )
        
        update_url = f'{self.list_url}{transaction.id}/'
        data = {'description': 'Partial update'}
        
        response = self.client.patch(update_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        transaction.refresh_from_db()
        self.assertEqual(transaction.description, 'Partial update')

    def test_delete_transaction(self):
        """Test deleting a transaction."""
        transaction = Transaction.objects.create(
            user=self.user,
            amount=Decimal('500.00'),
            transaction_type='debit',
            date=self.today,
            register=self.register
        )
        
        delete_url = f'{self.list_url}{transaction.id}/'
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_cannot_modify_other_user_transaction(self):
        """Test that users cannot modify other users' transactions."""
        other_transaction = Transaction.objects.create(
            user=self.other_user,
            amount=Decimal('1000.00'),
            transaction_type='credit',
            date=self.today,
            register=self.other_register
        )
        
        update_url = f'{self.list_url}{other_transaction.id}/'
        data = {'amount': '5000.00'}
        
        response = self.client.patch(update_url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_use_other_user_register(self):
        """Test that user cannot create transaction with another user's register."""
        data = {
            'amount': '500.00',
            'transaction_type': 'debit',
            'date': str(self.today),
            'register': self.other_register.id
        }
        
        response = self.client.post(self.list_url, data)
        # Should fail validation or permission check
        self.assertNotEqual(response.status_code, status.HTTP_201_CREATED)


class TransactionFilteringTests(APITestCase):
    """Test transaction filtering functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        cache.clear()
        
        self.user = User.objects.create_user(
            email='filteruser@example.com',
            password='testpass123',
            first_name='Filter',
            last_name='User',
            
        )
        
        self.register1 = Register.objects.create(
            user=self.user,
            name='Cash',
            debit=True,
            credit=True
        )
        
        self.register2 = Register.objects.create(
            user=self.user,
            name='Bank',
            debit=True,
            credit=True
        )
        
        self.token = generate_test_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        self.today = date.today()
        self.list_url = '/api/v2/transactions/'
        
        # Create test transactions
        for i in range(5):
            Transaction.objects.create(
                user=self.user,
                amount=Decimal('100.00') * (i + 1),
                transaction_type='debit' if i % 2 == 0 else 'credit',
                date=self.today - timedelta(days=i),
                register=self.register1 if i < 3 else self.register2
            )

    def test_filter_by_date(self):
        """Test filtering transactions by single date."""
        response = self.client.get(self.list_url, {'date': str(self.today)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_filter_by_date_range(self):
        """Test filtering transactions by date range."""
        start_date = self.today - timedelta(days=3)
        end_date = self.today
        
        response = self.client.get(self.list_url, {
            'start_date': str(start_date),
            'end_date': str(end_date)
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 4)

    def test_filter_by_transaction_type_debit(self):
        """Test filtering by debit transactions."""
        response = self.client.get(self.list_url, {'transaction_type': 'debit'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # We created 5 transactions, 3 are debits (index 0, 2, 4)
        self.assertEqual(len(response.data['results']), 3)

    def test_filter_by_transaction_type_credit(self):
        """Test filtering by credit transactions."""
        response = self.client.get(self.list_url, {'transaction_type': 'credit'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # We created 5 transactions, 2 are credits (index 1, 3)
        self.assertEqual(len(response.data['results']), 2)

    def test_filter_by_register(self):
        """Test filtering by register."""
        response = self.client.get(self.list_url, {'register': self.register1.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # First 3 transactions use register1
        self.assertEqual(len(response.data['results']), 3)


class TransactionJournalIntegrationTests(APITestCase):
    """Test transaction and journal integration."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            email='journaluser@example.com',
            password='testpass123',
            first_name='Journal',
            last_name='User',
            
            first_opening_balance=Decimal('10000.00')
        )
        
        self.register = Register.objects.create(
            user=self.user,
            name='Cash',
            debit=True,
            credit=True
        )
        
        self.token = generate_test_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        self.today = date.today()
        self.list_url = '/api/v2/transactions/'
        
        # Create journal for today
        self.journal = Journal.objects.create(
            user=self.user,
            opening_balance=Decimal('10000.00'),
            closing_balance=Decimal('10000.00'),
            date=self.today
        )

    def test_creating_debit_transaction_updates_journal(self):
        """Test that creating a debit transaction updates journal closing balance."""
        initial_closing = self.journal.closing_balance
        
        data = {
            'amount': '500.00',
            'transaction_type': 'debit',
            'date': str(self.today),
            'register': self.register.id
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.journal.refresh_from_db()
        # Debit should decrease closing balance
        expected_closing = initial_closing - Decimal('500.00')
        self.assertEqual(self.journal.closing_balance, expected_closing)

    def test_creating_credit_transaction_updates_journal(self):
        """Test that creating a credit transaction updates journal closing balance."""
        initial_closing = self.journal.closing_balance
        
        data = {
            'amount': '2000.00',
            'transaction_type': 'credit',
            'date': str(self.today),
            'register': self.register.id
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.journal.refresh_from_db()
        # Credit should increase closing balance
        expected_closing = initial_closing + Decimal('2000.00')
        self.assertEqual(self.journal.closing_balance, expected_closing)

    def test_updating_transaction_updates_journal(self):
        """Test that updating a transaction adjusts journal balance."""
        # Create initial transaction
        transaction = Transaction.objects.create(
            user=self.user,
            amount=Decimal('500.00'),
            transaction_type='debit',
            date=self.today,
            register=self.register
        )
        
        self.journal.closing_balance = Decimal('9500.00')  # After initial debit
        self.journal.save()
        
        # Update transaction amount
        update_url = f'{self.list_url}{transaction.id}/'
        data = {
            'amount': '1000.00',  # Changed from 500 to 1000
            'transaction_type': 'debit',
            'date': str(self.today),
            'register': self.register.id
        }
        
        response = self.client.put(update_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.journal.refresh_from_db()
        # Should reflect the change: 10000 - 1000 = 9000
        self.assertEqual(self.journal.closing_balance, Decimal('9000.00'))

    def test_deleting_transaction_updates_journal(self):
        """Test that deleting a transaction adjusts journal balance."""
        # Create transaction
        transaction = Transaction.objects.create(
            user=self.user,
            amount=Decimal('500.00'),
            transaction_type='debit',
            date=self.today,
            register=self.register
        )
        
        self.journal.closing_balance = Decimal('9500.00')
        self.journal.save()
        
        # Delete transaction
        delete_url = f'{self.list_url}{transaction.id}/'
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        self.journal.refresh_from_db()
        # Balance should be restored: 9500 + 500 = 10000
        self.assertEqual(self.journal.closing_balance, Decimal('10000.00'))


class TransactionAtomicTests(APITestCase):
    """Test atomic transaction behavior."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            email='atomicuser@example.com',
            password='testpass123',
            first_name='Atomic',
            last_name='User',
            
            first_opening_balance=Decimal('5000.00')
        )
        
        self.register = Register.objects.create(
            user=self.user,
            name='Cash',
            debit=True,
            credit=True
        )
        
        self.token = generate_test_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        self.today = date.today()
        self.list_url = '/api/v2/transactions/'
        
        self.journal = Journal.objects.create(
            user=self.user,
            opening_balance=Decimal('5000.00'),
            closing_balance=Decimal('5000.00'),
            date=self.today
        )

    def test_transaction_and_journal_update_are_atomic(self):
        """Test that transaction creation and journal update happen atomically."""
        initial_journal_balance = self.journal.closing_balance
        initial_transaction_count = Transaction.objects.count()
        
        data = {
            'amount': '1000.00',
            'transaction_type': 'debit',
            'date': str(self.today),
            'register': self.register.id
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Both transaction and journal should be updated
        self.assertEqual(Transaction.objects.count(), initial_transaction_count + 1)
        
        self.journal.refresh_from_db()
        self.assertEqual(
            self.journal.closing_balance,
            initial_journal_balance - Decimal('1000.00')
        )
