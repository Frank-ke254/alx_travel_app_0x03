from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_booking_confirmation_email(user_email, booking_details):
    subject = "Booking Confirmation"
    message = f"Thank you for your booking!\n\nDetails:\n{booking_details}"
    email_from = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user_email]

    send_mail(subject, message, email_from, recipient_list)
    return "Email sent successfully"

@shared_task
def send_payment_confirmation_email(user_email, booking_reference):
    send_mail(
        subject="Payment Confirmation",
        message=f"Your payment for booking {booking_reference} was successful!",
        from_email="no-reply@alxtravel.com",
        recipient_list=[user_email],
        fail_silently=False,
    )
