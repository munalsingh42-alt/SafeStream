import logging
import threading
import time

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_ticket_email(user, payment, seats):

    attempts = 3

    for attempt in range(attempts):

        try:

            html_content = render_to_string(
                'emails/ticket_confirmation.html',
                {
                    'username': user.username,
                    'movie': payment.movie.title,
                    'theater': seats[0].theater_name if seats else 'N/A',
                    'screen': seats[0].screen_name if seats else 'N/A',
                    'seats': ", ".join(
                        [seat.seat_number for seat in seats]
                    ),
                    'payment_id': payment.razorpay_payment_id,
                    'booking_time': payment.created_at
                }
            )

            msg = EmailMultiAlternatives(
                subject='SafeStream Ticket Confirmation',
                body='Your booking has been confirmed.',
                to=[str(user.email)]
            )

            msg.attach_alternative(
                html_content,
                "text/html"
            )

            msg.send()

            logger.info("Email sent")

            return

        except Exception as e:

            logger.error(
                f"Email failed attempt {attempt + 1}: {e}"
            )

            time.sleep(2)

    logger.error(
        "Final email failure"
    )


def send_ticket_email_background(
    user,
    payment,
    seats
):

    threading.Thread(
        target=send_ticket_email,
        args=(user, payment, seats),
        daemon=True
    ).start()