from django.contrib import admin
from .models import EmailTemplate, EmailOutbox


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('key', 'locale', 'version', 'status', 'updated_at')
    list_filter = ('key', 'locale', 'status')
    search_fields = ('key', 'subject', 'body_html')
    ordering = ('-updated_at',)

    def save_model(self, request, obj, form, change):
        """Ensure only one published template per (key, locale) by demoting others."""
        if obj.status == 'published':
            EmailTemplate.objects.filter(key=obj.key, locale=obj.locale, status='published').exclude(pk=obj.pk).update(status='draft')
        super().save_model(request, obj, form, change)


@admin.register(EmailOutbox)
class EmailOutboxAdmin(admin.ModelAdmin):
    list_display = ('id', 'key', 'to_email', 'status', 'attempts', 'created_at')
    list_filter = ('status', 'key')
    search_fields = ('to_email', 'subject', 'body_text')
    readonly_fields = ('created_at', 'updated_at')

