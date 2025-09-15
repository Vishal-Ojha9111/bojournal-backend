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
    register = models.CharField(max_length=100, blank=False) 
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    image_keys = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} - {self.transaction_type} - {self.amount}"
    
