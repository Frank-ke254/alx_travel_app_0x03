from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_payment_confirmation_email(user_email, booking_reference):
    send_mail(
        subject="Payment Confirmation",
        message=f"Your payment for booking {booking_reference} was successful!",
        from_email="no-reply@alxtravel.com",
        recipient_list=[user_email],
        fail_silently=False,
    )
