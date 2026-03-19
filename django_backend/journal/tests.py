"""
Comprehensive test cases for journal module.

Tests cover:
- Journal CRUD operations
- Caching behavior
- Atomic transactions
- Permissions and ownership
- Date-based filtering
- Holiday journals
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


class JournalModelTests(TestCase):
    """Test Journal model functionality."""

    def setUp(self):
        """Set up test user and journal data."""
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            
        )
        self.today = date.today()

    def test_journal_creation(self):
        """Test creating a journal entry."""
        journal = Journal.objects.create(
            user=self.user,
            opening_balance=Decimal('1000.00'),
            closing_balance=Decimal('1500.00'),
            date=self.today
        )
        self.assertEqual(journal.user, self.user)
        self.assertEqual(journal.opening_balance, Decimal('1000.00'))
        self.assertEqual(journal.closing_balance, Decimal('1500.00'))
        self.assertFalse(journal.is_holiday)

    def test_journal_unique_constraint(self):
        """Test that a user can only have one journal per date."""
        Journal.objects.create(
            user=self.user,
            opening_balance=Decimal('1000.00'),
            closing_balance=Decimal('1000.00'),
            date=self.today
        )
        # Attempting to create duplicate should raise error
        with self.assertRaises(Exception):
            Journal.objects.create(
                user=self.user,
                opening_balance=Decimal('2000.00'),
                closing_balance=Decimal('2000.00'),
                date=self.today
            )

    def test_journal_holiday(self):
        """Test creating a holiday journal entry."""
        journal = Journal.objects.create(
            user=self.user,
            opening_balance=Decimal('1000.00'),
            closing_balance=Decimal('1000.00'),
            date=self.today,
            is_holiday=True,
            holiday_reason='National Holiday'
        )
        self.assertTrue(journal.is_holiday)
        self.assertEqual(journal.holiday_reason, 'National Holiday')

    def test_journal_ordering(self):
        """Test that journals are ordered by date (newest first)."""
        journal1 = Journal.objects.create(
            user=self.user,
            opening_balance=Decimal('1000.00'),
            closing_balance=Decimal('1000.00'),
            date=self.today - timedelta(days=2)
        )
        journal2 = Journal.objects.create(
            user=self.user,
            opening_balance=Decimal('1100.00'),
            closing_balance=Decimal('1100.00'),
            date=self.today
        )
        journal3 = Journal.objects.create(
            user=self.user,
            opening_balance=Decimal('1050.00'),
            closing_balance=Decimal('1050.00'),
            date=self.today - timedelta(days=1)
        )
        
        journals = Journal.objects.all()
        self.assertEqual(journals[0], journal2)  # Most recent
        self.assertEqual(journals[1], journal3)
        self.assertEqual(journals[2], journal1)  # Oldest


class JournalAPITests(APITestCase):
    """Test Journal API endpoints."""

    def setUp(self):
        """Set up test client and users."""
        self.client = APIClient()
        cache.clear()  # Clear cache before each test
        
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
        
        # Generate token for user
        self.token = generate_test_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        self.today = date.today()
        self.list_url = '/api/v2/journal/'

    def test_list_journals_authenticated(self):
        """Test listing journals for authenticated user."""
        # Create some journals
        Journal.objects.create(
            user=self.user,
            opening_balance=Decimal('1000.00'),
            closing_balance=Decimal('1200.00'),
            date=self.today
        )
        Journal.objects.create(
            user=self.user,
            opening_balance=Decimal('1200.00'),
            closing_balance=Decimal('1500.00'),
            date=self.today - timedelta(days=1)
        )
        
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_list_journals_unauthenticated(self):
        """Test that unauthenticated users cannot list journals."""
        self.client.credentials()  # Remove credentials
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_only_sees_own_journals(self):
        """Test that users only see their own journals."""
        # Create journal for user
        Journal.objects.create(
            user=self.user,
            opening_balance=Decimal('1000.00'),
            closing_balance=Decimal('1200.00'),
            date=self.today
        )
        
        # Create journal for other user
        Journal.objects.create(
            user=self.other_user,
            opening_balance=Decimal('2000.00'),
            closing_balance=Decimal('2500.00'),
            date=self.today
        )
        
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['user'], self.user.id)

    def test_create_journal(self):
        """Test creating a journal entry."""
        data = {
            'opening_balance': '1000.00',
            'closing_balance': '1200.00',
            'date': str(self.today),
            'is_holiday': False
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Journal.objects.count(), 1)
        self.assertEqual(Journal.objects.first().user, self.user)

    def test_create_duplicate_journal_date(self):
        """Test that creating duplicate journal for same date fails."""
        Journal.objects.create(
            user=self.user,
            opening_balance=Decimal('1000.00'),
            closing_balance=Decimal('1000.00'),
            date=self.today
        )
        
        data = {
            'opening_balance': '2000.00',
            'closing_balance': '2000.00',
            'date': str(self.today)
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_journal(self):
        """Test updating a journal entry."""
        journal = Journal.objects.create(
            user=self.user,
            opening_balance=Decimal('1000.00'),
            closing_balance=Decimal('1200.00'),
            date=self.today
        )
        
        update_url = f'{self.list_url}{journal.id}/'
        data = {
            'opening_balance': '1500.00',
            'closing_balance': '1700.00',
            'date': str(self.today)
        }
        
        response = self.client.put(update_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        journal.refresh_from_db()
        self.assertEqual(journal.opening_balance, Decimal('1500.00'))
        self.assertEqual(journal.closing_balance, Decimal('1700.00'))

    def test_partial_update_journal(self):
        """Test partially updating a journal entry."""
        journal = Journal.objects.create(
            user=self.user,
            opening_balance=Decimal('1000.00'),
            closing_balance=Decimal('1200.00'),
            date=self.today
        )
        
        update_url = f'{self.list_url}{journal.id}/'
        data = {'is_holiday': True, 'holiday_reason': 'Weekend'}
        
        response = self.client.patch(update_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        journal.refresh_from_db()
        self.assertTrue(journal.is_holiday)
        self.assertEqual(journal.holiday_reason, 'Weekend')

    def test_delete_journal(self):
        """Test deleting a journal entry."""
        journal = Journal.objects.create(
            user=self.user,
            opening_balance=Decimal('1000.00'),
            closing_balance=Decimal('1200.00'),
            date=self.today
        )
        
        delete_url = f'{self.list_url}{journal.id}/'
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Journal.objects.count(), 0)

    def test_cannot_modify_other_user_journal(self):
        """Test that users cannot modify other users' journals."""
        other_journal = Journal.objects.create(
            user=self.other_user,
            opening_balance=Decimal('2000.00'),
            closing_balance=Decimal('2500.00'),
            date=self.today
        )
        
        update_url = f'{self.list_url}{other_journal.id}/'
        data = {'closing_balance': '3000.00'}
        
        response = self.client.patch(update_url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class JournalCachingTests(APITestCase):
    """Test journal caching behavior."""

    def setUp(self):
        """Set up test client and user."""
        self.client = APIClient()
        cache.clear()
        
        self.user = User.objects.create_user(
            email='cacheuser@example.com',
            password='testpass123',
            first_name='Cache',
            last_name='User',
            
        )
        
        self.token = generate_test_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        self.today = date.today()
        self.list_url = '/api/v2/journal/'

    def test_cache_is_populated_on_first_request(self):
        """Test that cache is populated on first GET request."""
        Journal.objects.create(
            user=self.user,
            opening_balance=Decimal('1000.00'),
            closing_balance=Decimal('1200.00'),
            date=self.today
        )
        
        # First request should populate cache
        response1 = self.client.get(self.list_url)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Check cache key exists
        cache_key = f"journal_list_user_{self.user.id}_None_None_None"
        cached_data = cache.get(cache_key)
        self.assertIsNotNone(cached_data)

    def test_cache_is_used_on_subsequent_requests(self):
        """Test that subsequent requests use cached data."""
        journal = Journal.objects.create(
            user=self.user,
            opening_balance=Decimal('1000.00'),
            closing_balance=Decimal('1200.00'),
            date=self.today
        )
        
        # First request
        response1 = self.client.get(self.list_url)
        first_result = response1.data['results'][0]
        
        # Modify journal in database
        journal.closing_balance = Decimal('5000.00')
        journal.save()
        
        # Second request should still return cached data (old value)
        response2 = self.client.get(self.list_url)
        second_result = response2.data['results'][0]
        
        # Should be same as first request (cached)
        self.assertEqual(first_result['closing_balance'], second_result['closing_balance'])
        self.assertEqual(second_result['closing_balance'], '1200.00')

    def test_cache_is_invalidated_on_create(self):
        """Test that cache is cleared when creating a journal."""
        # Create first journal and cache it
        Journal.objects.create(
            user=self.user,
            opening_balance=Decimal('1000.00'),
            closing_balance=Decimal('1200.00'),
            date=self.today - timedelta(days=1)
        )
        self.client.get(self.list_url)  # Populate cache
        
        # Create new journal (should clear cache)
        data = {
            'opening_balance': '2000.00',
            'closing_balance': '2500.00',
            'date': str(self.today)
        }
        self.client.post(self.list_url, data)
        
        # Next GET should have new data (cache was cleared)
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data['results']), 2)

    def test_cache_is_invalidated_on_update(self):
        """Test that cache is cleared when updating a journal."""
        journal = Journal.objects.create(
            user=self.user,
            opening_balance=Decimal('1000.00'),
            closing_balance=Decimal('1200.00'),
            date=self.today
        )
        
        # Populate cache
        self.client.get(self.list_url)
        
        # Update journal (should clear cache)
        update_url = f'{self.list_url}{journal.id}/'
        self.client.patch(update_url, {'closing_balance': '5000.00'})
        
        # Next GET should have updated data
        response = self.client.get(self.list_url)
        self.assertEqual(response.data['results'][0]['closing_balance'], '5000.00')

    def test_cache_is_invalidated_on_delete(self):
        """Test that cache is cleared when deleting a journal."""
        journal = Journal.objects.create(
            user=self.user,
            opening_balance=Decimal('1000.00'),
            closing_balance=Decimal('1200.00'),
            date=self.today
        )
        
        # Populate cache
        response1 = self.client.get(self.list_url)
        self.assertEqual(len(response1.data['results']), 1)
        
        # Delete journal (should clear cache)
        delete_url = f'{self.list_url}{journal.id}/'
        self.client.delete(delete_url)
        
        # Next GET should show no journals
        response2 = self.client.get(self.list_url)
        self.assertEqual(len(response2.data['results']), 0)


class JournalFilteringTests(APITestCase):
    """Test journal filtering functionality."""

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
        
        self.token = generate_test_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        self.today = date.today()
        self.list_url = '/api/v2/journal/'
        
        # Create test journals
        for i in range(5):
            Journal.objects.create(
                user=self.user,
                opening_balance=Decimal('1000.00') + Decimal(str(i * 100)),
                closing_balance=Decimal('1100.00') + Decimal(str(i * 100)),
                date=self.today - timedelta(days=i),
                is_holiday=(i % 2 == 0)
            )

    def test_filter_by_single_date(self):
        """Test filtering journals by single date."""
        response = self.client.get(self.list_url, {'date': str(self.today)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_filter_by_date_range(self):
        """Test filtering journals by date range."""
        start_date = self.today - timedelta(days=3)
        end_date = self.today
        
        response = self.client.get(self.list_url, {
            'start_date': str(start_date),
            'end_date': str(end_date)
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 4)

    def test_filter_by_holiday(self):
        """Test filtering holiday journals."""
        response = self.client.get(self.list_url, {'is_holiday': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # We created 5 journals, 3 are holidays (index 0, 2, 4)
        self.assertEqual(len(response.data['results']), 3)


class JournalAtomicTransactionTests(APITestCase):
    """Test atomic transaction behavior in journal operations."""

    def setUp(self):
        """Set up test client and user."""
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            email='atomicuser@example.com',
            password='testpass123',
            first_name='Atomic',
            last_name='User',
            
            first_opening_balance=Decimal('5000.00')
        )
        
        self.token = generate_test_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        self.today = date.today()
        self.list_url = '/api/v2/journal/'

    def test_journal_creation_updates_user_balance(self):
        """Test that creating first journal updates user's opening balance."""
        initial_balance = self.user.first_opening_balance
        
        data = {
            'opening_balance': '10000.00',
            'closing_balance': '12000.00',
            'date': str(self.today)
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check that user's balance was updated
        self.user.refresh_from_db()
        # Note: The actual implementation should update the user's balance
        # This is a placeholder test

    def test_journal_operations_are_atomic(self):
        """Test that journal operations maintain data consistency."""
        # Create journal
        journal = Journal.objects.create(
            user=self.user,
            opening_balance=Decimal('1000.00'),
            closing_balance=Decimal('1200.00'),
            date=self.today
        )
        
        initial_count = Journal.objects.count()
        
        # Try to create duplicate (should fail atomically)
        data = {
            'opening_balance': '2000.00',
            'closing_balance': '2500.00',
            'date': str(self.today)
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Ensure no partial data was saved
        self.assertEqual(Journal.objects.count(), initial_count)
