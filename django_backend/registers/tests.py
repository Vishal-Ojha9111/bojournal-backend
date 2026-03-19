"""
Comprehensive test cases for registers module.

Tests cover:
- Register CRUD operations
- Caching behavior
- Atomic transactions
- Permissions and ownership
- Unique constraint validation
- Debit/Credit flag validation
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
from registers.models import Register


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


class RegisterModelTests(TestCase):
    """Test Register model functionality."""

    def setUp(self):
        """Set up test user and register data."""
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            
        )

    def test_register_creation(self):
        """Test creating a register."""
        register = Register.objects.create(
            user=self.user,
            name='Cash',
            description='Cash account',
            debit=True,
            credit=False
        )
        self.assertEqual(register.user, self.user)
        self.assertEqual(register.name, 'Cash')
        self.assertTrue(register.debit)
        self.assertFalse(register.credit)

    def test_register_unique_constraint(self):
        """Test that user cannot have duplicate register names."""
        Register.objects.create(
            user=self.user,
            name='Bank',
            debit=True,
            credit=True
        )
        
        # Attempting to create duplicate should raise error
        with self.assertRaises(Exception):
            Register.objects.create(
                user=self.user,
                name='Bank',
                debit=False,
                credit=True
            )

    def test_register_both_flags(self):
        """Test creating register with both debit and credit flags."""
        register = Register.objects.create(
            user=self.user,
            name='Bank Account',
            debit=True,
            credit=True
        )
        self.assertTrue(register.debit)
        self.assertTrue(register.credit)

    def test_register_ordering(self):
        """Test that registers are ordered by created_at (newest first)."""
        register1 = Register.objects.create(
            user=self.user,
            name='Cash',
            debit=True
        )
        register2 = Register.objects.create(
            user=self.user,
            name='Bank',
            debit=True,
            credit=True
        )
        register3 = Register.objects.create(
            user=self.user,
            name='Credit Card',
            credit=True
        )
        
        registers = Register.objects.all()
        self.assertEqual(registers[0], register3)  # Most recent
        self.assertEqual(registers[1], register2)
        self.assertEqual(registers[2], register1)  # Oldest


class RegisterAPITests(APITestCase):
    """Test Register API endpoints."""

    def setUp(self):
        """Set up test client and users."""
        self.client = APIClient()
        cache.clear()
        
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            
        )
        
        self.other_user = User.objects.create_user(
            email='otheruser@example.com',
            password='testpass123',
            first_name='Other',
            last_name='User',
            
        )
        
        self.token = generate_test_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        self.list_url = '/api/v2/registers/'

    def test_list_registers_authenticated(self):
        """Test listing registers for authenticated user."""
        Register.objects.create(user=self.user, name='Cash', debit=True)
        Register.objects.create(user=self.user, name='Bank', debit=True, credit=True)
        
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_list_registers_unauthenticated(self):
        """Test that unauthenticated users cannot list registers."""
        self.client.credentials()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_only_sees_own_registers(self):
        """Test that users only see their own registers."""
        Register.objects.create(user=self.user, name='Cash', debit=True)
        Register.objects.create(user=self.other_user, name='Bank', debit=True)
        
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['user'], self.user.id)

    def test_create_register(self):
        """Test creating a register."""
        data = {
            'name': 'Cash',
            'description': 'Cash account',
            'debit': True,
            'credit': False
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Register.objects.count(), 1)
        self.assertEqual(Register.objects.first().user, self.user)

    def test_create_duplicate_register_name(self):
        """Test that creating duplicate register name fails."""
        Register.objects.create(user=self.user, name='Bank', debit=True)
        
        data = {'name': 'Bank', 'debit': False, 'credit': True}
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_register_with_both_flags(self):
        """Test creating register with both debit and credit."""
        data = {
            'name': 'Bank Account',
            'debit': True,
            'credit': True
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        register = Register.objects.first()
        self.assertTrue(register.debit)
        self.assertTrue(register.credit)

    def test_update_register(self):
        """Test updating a register."""
        register = Register.objects.create(
            user=self.user,
            name='Cash',
            debit=True,
            credit=False
        )
        
        update_url = f'{self.list_url}{register.id}/'
        data = {
            'name': 'Cash',
            'description': 'Updated cash account',
            'debit': True,
            'credit': True
        }
        
        response = self.client.put(update_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        register.refresh_from_db()
        self.assertEqual(register.description, 'Updated cash account')
        self.assertTrue(register.credit)

    def test_partial_update_register(self):
        """Test partially updating a register."""
        register = Register.objects.create(
            user=self.user,
            name='Bank',
            debit=True,
            credit=False
        )
        
        update_url = f'{self.list_url}{register.id}/'
        data = {'credit': True}
        
        response = self.client.patch(update_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        register.refresh_from_db()
        self.assertTrue(register.credit)

    def test_delete_register(self):
        """Test deleting a register."""
        register = Register.objects.create(
            user=self.user,
            name='Old Account',
            debit=True
        )
        
        delete_url = f'{self.list_url}{register.id}/'
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Register.objects.count(), 0)

    def test_cannot_modify_other_user_register(self):
        """Test that users cannot modify other users' registers."""
        other_register = Register.objects.create(
            user=self.other_user,
            name='Other Bank',
            debit=True
        )
        
        update_url = f'{self.list_url}{other_register.id}/'
        data = {'description': 'Hacked'}
        
        response = self.client.patch(update_url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class RegisterCachingTests(APITestCase):
    """Test register caching behavior."""

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
        
        self.list_url = '/api/v2/registers/'

    def test_cache_is_populated_on_first_request(self):
        """Test that cache is populated on first GET request."""
        Register.objects.create(user=self.user, name='Cash', debit=True)
        
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check cache key exists
        cache_key = f"register_list_user_{self.user.id}"
        cached_ids = cache.get(cache_key)
        self.assertIsNotNone(cached_ids)

    def test_cache_is_invalidated_on_create(self):
        """Test that cache is cleared when creating a register."""
        Register.objects.create(user=self.user, name='Cash', debit=True)
        self.client.get(self.list_url)  # Populate cache
        
        data = {'name': 'Bank', 'debit': True, 'credit': True}
        self.client.post(self.list_url, data)
        
        # Next GET should have new data
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data['results']), 2)

    def test_cache_is_invalidated_on_update(self):
        """Test that cache is cleared when updating a register."""
        register = Register.objects.create(
            user=self.user,
            name='Cash',
            debit=True
        )
        
        self.client.get(self.list_url)  # Populate cache
        
        # Update register
        update_url = f'{self.list_url}{register.id}/'
        self.client.patch(update_url, {'credit': True})
        
        # Next GET should have updated data
        response = self.client.get(self.list_url)
        result = response.data['results'][0]
        self.assertTrue(result['credit'])

    def test_cache_is_invalidated_on_delete(self):
        """Test that cache is cleared when deleting a register."""
        register = Register.objects.create(
            user=self.user,
            name='Cash',
            debit=True
        )
        
        response1 = self.client.get(self.list_url)
        self.assertEqual(len(response1.data['results']), 1)
        
        # Delete register
        delete_url = f'{self.list_url}{register.id}/'
        self.client.delete(delete_url)
        
        # Next GET should show no registers
        response2 = self.client.get(self.list_url)
        self.assertEqual(len(response2.data['results']), 0)


class RegisterFilteringTests(APITestCase):
    """Test register filtering functionality."""

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
        
        self.list_url = '/api/v2/registers/'
        
        # Create test registers
        Register.objects.create(user=self.user, name='Cash', debit=True, credit=False)
        Register.objects.create(user=self.user, name='Bank', debit=True, credit=True)
        Register.objects.create(user=self.user, name='Credit Card', debit=False, credit=True)
        Register.objects.create(user=self.user, name='Loan', debit=False, credit=False)

    def test_filter_by_debit(self):
        """Test filtering registers by debit flag."""
        response = self.client.get(self.list_url, {'debit': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)  # Cash and Bank

    def test_filter_by_credit(self):
        """Test filtering registers by credit flag."""
        response = self.client.get(self.list_url, {'credit': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)  # Bank and Credit Card

    def test_filter_by_name_contains(self):
        """Test filtering registers by name search."""
        response = self.client.get(self.list_url, {'name__icontains': 'cash'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class RegisterAtomicTransactionTests(APITestCase):
    """Test atomic transaction behavior in register operations."""

    def setUp(self):
        """Set up test client and user."""
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            email='atomicuser@example.com',
            password='testpass123',
            first_name='Atomic',
            last_name='User',
            
        )
        
        self.token = generate_test_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        self.list_url = '/api/v2/registers/'

    def test_register_operations_are_atomic(self):
        """Test that register operations maintain data consistency."""
        Register.objects.create(user=self.user, name='Bank', debit=True)
        
        initial_count = Register.objects.count()
        
        # Try to create duplicate (should fail atomically)
        data = {'name': 'Bank', 'debit': False, 'credit': True}
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Ensure no partial data was saved
        self.assertEqual(Register.objects.count(), initial_count)

    def test_update_with_duplicate_name_fails(self):
        """Test that updating to duplicate name fails atomically."""
        register1 = Register.objects.create(user=self.user, name='Cash', debit=True)
        register2 = Register.objects.create(user=self.user, name='Bank', debit=True)
        
        update_url = f'{self.list_url}{register2.id}/'
        data = {'name': 'Cash', 'debit': True}  # Try to change to existing name
        
        response = self.client.put(update_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Ensure register2 name wasn't changed
        register2.refresh_from_db()
        self.assertEqual(register2.name, 'Bank')


class RegisterValidationTests(APITestCase):
    """Test register validation rules."""

    def setUp(self):
        """Set up test client and user."""
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            email='validuser@example.com',
            password='testpass123',
            first_name='Valid',
            last_name='User',
            
        )
        
        self.token = generate_test_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        self.list_url = '/api/v2/registers/'

    def test_register_name_required(self):
        """Test that register name is required."""
        data = {'debit': True}
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_default_flags(self):
        """Test default values for debit/credit flags."""
        data = {'name': 'Test Register'}
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        register = Register.objects.first()
        self.assertFalse(register.debit)
        self.assertFalse(register.credit)

    def test_register_empty_name_fails(self):
        """Test that empty register name fails."""
        data = {'name': '', 'debit': True}
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
