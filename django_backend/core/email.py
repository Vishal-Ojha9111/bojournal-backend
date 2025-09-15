from django.core.mail import send_mail
from django.core.cache import cache
import random
from django.conf import settings

sender = getattr(settings, 'EMAIL_HOST_USER',)

def sendOtpMail (email,action, data=None):
    try:
        otp = str(random.randint(100000,999999))
        cache.set(f"otp_{email}", {'action':action,'otp':otp, 'data': data}, timeout=300)  # Store OTP in cache for 5 minutes
        send_mail(
            'BO Journal OTP Verification',
            f'Your OTP to verify email is {otp}. It is valid for 5 minutes.',
            sender,
        [email],
        fail_silently=False,
        )
    except Exception as e:
        print(f"Error sending OTP email: {e}")
        return False
    return True


