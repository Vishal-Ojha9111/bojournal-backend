from rest_framework.routers import DefaultRouter
from .views import TransactionsListView, PresignedURLView, CleanupViewSet
from django.urls import path

router = DefaultRouter()
router.register(r'', TransactionsListView, basename='transactions')
urlpatterns = [
    path('presign/', PresignedURLView.as_view(), name='presign'),
    path('cleanup/', CleanupViewSet.as_view(), name='cleanup')
] + router.urls

