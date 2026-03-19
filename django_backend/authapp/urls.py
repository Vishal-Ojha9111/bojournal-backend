from django.urls import path
from .views import SignupView, VerifyOTPView, ResetPasswordView, UpdatePasswordView, LoginView, AuthCheckView, LogoutView, RefreshTokenView, GetCSRFToken, UpdateUserView, ProfilePictureURLView, HealthCheckView

urlpatterns = [
    path('signup', SignupView.as_view(), name='signup'),
    path('verifyotp', VerifyOTPView.as_view(), name='verifyotp'),
    path('resetpassword', ResetPasswordView.as_view(), name='reset-password'),
    path('updatepassword', UpdatePasswordView.as_view(), name='update-password'),
    path('login', LoginView.as_view(), name='login'),
    path('authcheck', AuthCheckView.as_view(), name='authcheck'),
    path('logout', LogoutView.as_view(), name='logout'),
    path('refresh', RefreshTokenView.as_view(), name='refresh-token'),
    path('csrf', GetCSRFToken.as_view(), name='get-csrf'),
    path('user/update', UpdateUserView.as_view(), name='update-user'),
    path('user/profile-picture-url', ProfilePictureURLView.as_view(), name='profile-picture-url'),
    path('health', HealthCheckView.as_view(), name='health-check'),
]
