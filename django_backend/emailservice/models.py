from __future__ import annotations

from django.db import models
from django.utils import timezone

class EmailTemplate(models.Model):
    STATUS_CHOICES = (('draft', 'Draft'), ('published', 'Published'))

    key = models.CharField(max_length=100, db_index=True)
    locale = models.CharField(max_length=10, default='en')
    subject = models.CharField(max_length=255)
    body_html = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='published')
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('key', 'locale', 'version'),)
        ordering = ['-updated_at']

    def __str__(self) -> str:
        return f"{self.key}@{self.locale} v{self.version} ({self.status})"


class EmailOutbox(models.Model):
    STATUS = (('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed'))

    key = models.CharField(max_length=100, db_index=True)
    to_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body_html = models.TextField()
    body_text = models.TextField(blank=True, null=True)
    meta = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default='pending', db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['status', 'created_at'], name='emailoutbox_status_created_idx'),
        ]

    def __str__(self) -> str:
        return f"Outbox {self.id} {self.key} -> {self.to_email} ({self.status})"
