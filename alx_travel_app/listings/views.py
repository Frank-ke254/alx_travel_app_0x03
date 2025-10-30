import requests, uuid
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Payment

from rest_framework import viewsets
from .models import Listing, Booking
from .serializers import ListingSerializer, BookingSerializer
from rest_framework import viewsets
from .models import Booking
from .serializers import BookingSerializer
from .tasks import send_booking_confirmation_email


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def perform_create(self, serializer):
        booking = serializer.save()
        user_email = booking.user.email
        booking_details = f"Destination: {booking.destination}, Date: {booking.date}"

        send_booking_confirmation_email.delay(user_email, booking_details)


class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    user = request.user
    booking_reference = request.data.get('booking_reference')
    amount = request.data.get('amount')
    email = request.data.get('email', user.email)

    tx_ref = str(uuid.uuid4())

    headers = {
        'Authorization': f'Bearer {settings.CHAPA_SECRET_KEY}',
        'Content-Type': 'application/json',
    }

    data = {
        "amount": amount,
        "currency": "ETB",
        "email": email,
        "tx_ref": tx_ref,
        "callback_url": "http://127.0.0.1:8000/api/verify-payment/",
        "return_url": "http://127.0.0.1:8000/success/",
        "customization": {
            "title": "Travel Booking Payment",
            "description": "Payment for travel booking"
        }
    }

    response = requests.post(f"{settings.CHAPA_BASE_URL}/transaction/initialize", json=data, headers=headers)
    chapa_response = response.json()

    if chapa_response.get('status') == 'success':
        Payment.objects.create(
            user=user,
            booking_reference=booking_reference,
            transaction_id=tx_ref,
            amount=amount,
            status='Pending'
        )
        return Response({
            "checkout_url": chapa_response['data']['checkout_url'],
            "transaction_id": tx_ref
        })
    else:
        return Response({"error": "Payment initiation failed"}, status=400)

@api_view(['GET'])
def verify_payment(request):
    from .tasks import send_payment_confirmation_email
    send_payment_confirmation_email.delay(payment.user.email, payment.booking_reference)

    tx_ref = request.query_params.get('transaction_id')
    headers = {'Authorization': f'Bearer {settings.CHAPA_SECRET_KEY}'}

    response = requests.get(f"{settings.CHAPA_BASE_URL}/transaction/verify/{tx_ref}", headers=headers)
    chapa_response = response.json()

    try:
        payment = Payment.objects.get(transaction_id=tx_ref)
    except Payment.DoesNotExist:
        return Response({"error": "Transaction not found"}, status=404)

    if chapa_response.get('status') == 'success' and chapa_response['data']['status'] == 'success':
        payment.status = 'Completed'
        payment.save()
        return Response({"message": "Payment verified successfully"})
    else:
        payment.status = 'Failed'
        payment.save()
        return Response({"message": "Payment verification failed"}, status=400)
