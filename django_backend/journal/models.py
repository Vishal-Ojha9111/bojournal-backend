from django.db import models

# Create your models here.

class Journal(models.Model):
    user = models.ForeignKey('authapp.User', on_delete=models.CASCADE)
    opening_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, blank=False)
    closing_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, blank=False)
    is_holiday = models.BooleanField(default=False)
    holiday_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    date = models.DateField()
    

    def __str__(self):
        return f"{self.user.email} - {self.opening_balance} - {self.date} - {self.closing_balance}"
