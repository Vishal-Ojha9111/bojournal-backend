from django.contrib import admin
from .models import Order, Plan

# Register your models here.

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'plan', 'amount', 'status', 'currency', 'created_at')
    search_fields = ('order_id', 'user__email', 'plan__name')
    list_filter = ('status', 'currency', 'created_at')
    ordering = ('-created_at',)

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan_id', 'price', 'duration_days', 'duration_months', 'duration_years')
    search_fields = ('name', 'plan_id')
    ordering = ('price',)
