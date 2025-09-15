from django.urls import path
from .views import JournalViewSet

urlpatterns = [
    path('', JournalViewSet.as_view({'get': 'list', 'post': 'create', 'patch':'update'}), name='journal'),
]