"""
URL configuration for django_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API v2 endpoints (current version)
    path('api/v2/auth/', include('authapp.urls')),
    path('api/v2/transactions/', include('transactions.urls')),
    path('api/v2/journal/', include('journal.urls')),
    path('api/v2/holiday/', include('holiday.urls')),
    path('api/v2/registers/', include('registers.urls')),
    path('api/v2/payment/', include('payment.urls')),
    path('api/v2/emailservice/', include('emailservice.urls')),
    
    # Legacy v1 endpoints (for backward compatibility)
    path('api/auth/', include('authapp.urls')),
    path('api/transactions/', include('transactions.urls')),
    path('api/journal/', include('journal.urls')),
    path('api/holiday/', include('holiday.urls')),
    path('api/registers/', include('registers.urls')),
    path('api/payment/', include('payment.urls')),
    path('api/emailservice/', include('emailservice.urls')),
]
