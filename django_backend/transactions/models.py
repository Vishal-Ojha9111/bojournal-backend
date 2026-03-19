from django.db import models

# Create your models here.

class Transaction(models.Model):
    TRANSACTION_TYPE = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]
    
    user = models.ForeignKey('authapp.User', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPE) 
    date = models.DateField()
    register = models.ForeignKey('registers.Register', on_delete=models.CASCADE, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    image_keys = models.JSONField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'date'], name='transaction_user_date_idx'),
            models.Index(fields=['user', 'transaction_type'], name='transaction_user_type_idx'),
            models.Index(fields=['register', 'date'], name='transaction_register_date_idx'),
            models.Index(fields=['date', '-created_at'], name='transaction_date_created_idx'),
        ]
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.transaction_type} - {self.amount}"
