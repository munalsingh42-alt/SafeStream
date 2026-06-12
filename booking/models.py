from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from movies.models import Movie


class Seat(models.Model):

    STATUS_CHOICES = [
        ('available', 'Available'),
        ('locked', 'Locked'),
        ('booked', 'Booked'),
    ]

    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE,
        related_name='seats'
    )
    theater_name = models.CharField(
    max_length=100,
    default='PVR Cinemas'
     )

    screen_name = models.CharField(
    max_length=50,
    default='Screen 1'
)

    seat_number = models.CharField(
        max_length=10
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available'
    )

    locked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    locked_until = models.DateTimeField(
        null=True,
        blank=True
    )

    def lock_seat(self, user):

        self.status = 'locked'

        self.locked_by = user

        self.locked_until = timezone.now() + timedelta(minutes=2)

        self.save()

    def release_seat(self):

        self.status = 'available'

        self.locked_by = None

        self.locked_until = None

        self.save()

    def __str__(self):

        return f"{self.movie.title} - {self.seat_number}"


class Payment(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE
    )

    razorpay_order_id = models.CharField(
        max_length=200,
        unique=True
    )

    razorpay_payment_id = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    razorpay_signature = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )

    amount = models.IntegerField()

    status = models.CharField(
        max_length=50,
        default='created'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )
    created_at = models.DateTimeField(
    auto_now_add=True
    )

    is_cancelled = models.BooleanField(
    default=False
    )

    def __str__(self):

       return self.razorpay_order_id