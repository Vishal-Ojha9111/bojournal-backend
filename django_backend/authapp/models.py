from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone
from decimal import Decimal

class CustomUserManager(BaseUserManager):

    def create_user(self, email, password=None, first_name="", last_name="", verified=False, otp_verification=False, register_types=[], first_opening_balance=Decimal(0.00), first_opening_balance_date=None, **extra_fields):
        if not email:
            raise ValueError('The Email field is required')
        
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            verified=verified,
            otp_verification=otp_verification,
            register_types=register_types,
            first_opening_balance=Decimal(0.00),
            first_opening_balance_date=first_opening_balance_date,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, first_name="", last_name="", **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')

        return self.create_user(email, password, first_name, last_name, **extra_fields)


class ReferralCode(models.Model):
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    times_used = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.code

    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        if self.max_uses and self.times_used >= self.max_uses:
            return False
        return True

        
class User(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    verified = models.BooleanField(default=False)
    otp_verification = models.BooleanField(default=False)
    register_types = models.JSONField(default=list, blank=True)
    first_opening_balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal(0.00))
    first_opening_balance_date = models.DateField(null=True, blank=True)
    referral_code = models.OneToOneField(ReferralCode, null=True, blank=True, on_delete=models.SET_NULL)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager()

    def __str__(self):
        return self.email

