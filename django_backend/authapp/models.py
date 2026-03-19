from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import timedelta

class CustomUserManager(BaseUserManager):

    def create_user(self, email, password=None, first_name="", last_name="", otp_verification=False, first_opening_balance_date=None, **extra_fields):
        if not email:
            raise ValueError('The Email field is required')
        
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            otp_verification=otp_verification,
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
    discount_percentage= models.PositiveBigIntegerField(default=0)

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
    first_name = models.CharField(max_length=150, blank=False)
    last_name = models.CharField(max_length=150, blank=False)
    email = models.EmailField(unique=True, blank=False)
    profile_picture_key = models.JSONField(null=True, blank=True)
    otp_verification = models.BooleanField(default=False)
    first_opening_balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal(0.00))
    first_opening_balance_date = models.DateField(null=True, blank=True)
    referral_code = models.OneToOneField(ReferralCode, null=True, blank=True, on_delete=models.SET_NULL)
    referral_code_used = models.BooleanField(default=False)
    subscription_active = models.BooleanField(default=False)
    subscription_start_date = models.DateField(null=True, blank=True)
    subscription_end_date = models.DateField(null=True, blank=True)
    subscription_plan = models.ForeignKey('payment.Plan', null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager()

    def __str__(self):
        return self.email


class SignupPending(models.Model):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    password_hash = models.CharField(max_length=128)
    referral_code = models.CharField(max_length=20, null=True, blank=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return self.expires_at and self.expires_at < timezone.now()

    @classmethod
    def create_pending(cls, email, first_name, last_name, raw_password, referral_code=None, ttl_seconds=300, otp=None):
        # remove existing pending for this email
        cls.objects.filter(email=email.lower()).delete()
        password_hash = make_password(raw_password)
        if otp is None:
            import random
            otp = str(random.randint(100000, 999999))
        expires = timezone.now() + timedelta(seconds=ttl_seconds)
        return cls.objects.create(
            email=email.lower(),
            first_name=first_name,
            last_name=last_name,
            password_hash=password_hash,
            referral_code=referral_code,
            otp=str(otp),
            expires_at=expires
        )


