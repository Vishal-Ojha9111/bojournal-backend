from django.urls import path
from .views import RegisterViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'', RegisterViewSet, basename='register')
urlpatterns = router.urls