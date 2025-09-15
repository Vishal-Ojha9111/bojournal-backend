from django.contrib import admin
from .models import User, ReferralCode
# Register your models here.

admin.site.register(User)
admin.site.register(ReferralCode)

class UserAdmin(admin.ModelAdmin):
    list_display = ['code', 'is_active', 'created_at', 'expires_at', 'max_uses', 'times_used']
    search_fields = ['code']
    list_filter = ['is_active']