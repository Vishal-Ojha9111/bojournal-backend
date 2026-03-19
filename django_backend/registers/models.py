from django.db import models

# Create your models here.


class Register(models.Model):
    user = models.ForeignKey('authapp.user', on_delete=models.CASCADE, related_name='register')
    name = models.CharField(max_length=255, null=False, blank=False)
    description = models.CharField(default='', blank=True, null=True)
    debit = models.BooleanField(default=False)
    credit = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'name'], name='register_user_name_idx'),
            models.Index(fields=['user', 'debit'], name='register_user_debit_idx'),
            models.Index(fields=['user', 'credit'], name='register_user_credit_idx'),
        ]
        # Ensure a deterministic ordering so pagination yields consistent results
        ordering = ['-created_at', 'id']
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'], name='unique_user_register_name')
        ]

    def __str__(self):
        return f"{self.name} - {self.user.email} - {self.debit} - {self.credit}"
