from django.urls import path
from .views import SignupView, VerifyOTPView, ResetPasswordView, UpdatePasswordView, LoginView, AuthCheckView, LogoutView, GetCSRFToken

urlpatterns = [
    path('signup', SignupView.as_view(), name='signup'),
    path('verifyotp', VerifyOTPView.as_view(), name='verifyotp'),
    path('resetpassword', ResetPasswordView.as_view(), name='reset-password'),
    path('updatepassword', UpdatePasswordView.as_view(), name='update-password'),
    path('login', LoginView.as_view(), name='login'),
    path('authcheck', AuthCheckView.as_view(), name='authcheck'),
    path('logout', LogoutView.as_view(), name='logout'),
    path('csrf', GetCSRFToken.as_view(), name='get-csrf'),
]
