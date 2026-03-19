from django.db import models

# Create your models here.


class Order(models.Model):
    user = models.ForeignKey('authapp.user', on_delete=models.CASCADE, related_name='orders')
    plan = models.ForeignKey('payment.Plan', on_delete=models.CASCADE, related_name='orders')
    order_id = models.CharField(max_length=100, unique=True, null=False, blank=False)
    amount = models.IntegerField(null=False, blank=False)
    status = models.CharField(max_length=50, null=False, blank=False)
    currency = models.CharField(max_length=10, default='INR')
    attempts = models.IntegerField(default=0)
    expired = models.BooleanField(default=False)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.order_id} - {self.user.email} - {self.amount} - {self.status}"
    
    class Meta:
        # Ensure a deterministic ordering so pagination yields consistent results
        ordering = ['-created_at', 'id']


class Plan(models.Model):
    name = models.CharField(max_length=100, unique=True)
    plan_id = models.CharField(max_length=100, unique=True)
    price = models.IntegerField()
    duration_days = models.IntegerField()
    duration_months = models.IntegerField()
    duration_years = models.IntegerField()
    savings = models.IntegerField(default=0)
    active = models.BooleanField(default=False)
    limited = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.plan_id} - {self.price}"