from django.urls import path
from .views import HolidayView

urlpatterns = [
    path('', HolidayView.as_view(), name='holiday-handler'),
]