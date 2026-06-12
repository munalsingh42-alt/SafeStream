

from .email_service import send_ticket_email_background

from django.contrib.admin.views.decorators import staff_member_required

from django.db.models import Sum, Count

from django.db.models.functions import ExtractHour

from django.core.cache import cache

from datetime import timedelta

import json
import razorpay

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import Seat, Payment
from movies.models import Movie


# SIGNUP

def signup_view(request):

    if request.method == 'POST':

        username = request.POST['username']

        email = request.POST['email']

        password = request.POST['password']

        if User.objects.filter(username=username).exists():

            return render(
                request,
                'booking/signup.html',
                {
                    'error': 'Username already exists'
                }
            )

        User.objects.create_user(

            username=username,

            email=email,

            password=password

        )

        return redirect('login')

    return render(
        request,
        'booking/signup.html'
    )

# LOGIN

def login_view(request):

    error = None

    if request.method == 'POST':

        username = request.POST['username']

        password = request.POST['password']

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user:

            login(request, user)

            return redirect('/')

        else:

            error = 'Invalid username or password'

    return render(request, 'booking/login.html', {
        'error': error
    })


# LOGOUT

def logout_view(request):

    logout(request)

    return redirect('/')


# MOVIE BOOKING PAGE

def movie_booking(request, movie_id):

    movie = get_object_or_404(Movie, id=movie_id)

    expired_seats = Seat.objects.filter(
        movie=movie,
        status='locked',
        locked_until__lt=timezone.now()
    )

    for seat in expired_seats:
        seat.release_seat()

    seats = Seat.objects.filter(
        movie=movie
    ).order_by('seat_number')

    return render(request, 'booking/home.html', {
        'movie': movie,
        'seats': seats,
        'current_time': timezone.now()
    })


# LOCK SEAT

@transaction.atomic
def lock_seat(request, seat_id):

    if not request.user.is_authenticated:

        return redirect('login')

    seat = Seat.objects.select_for_update().get(id=seat_id)

    if seat.locked_until and seat.locked_until < timezone.now():

        seat.release_seat()

    if seat.status == 'available':

        seat.lock_seat(request.user)

    return redirect('movie_booking', movie_id=seat.movie.id)


# CONFIRM BOOKING

@transaction.atomic
def confirm_booking(request, movie_id):

    if not request.user.is_authenticated:

        return redirect('login')

    movie = get_object_or_404(Movie, id=movie_id)

    locked_seats = Seat.objects.filter(
        movie=movie,
        status='locked',
        locked_by=request.user
    )

    for seat in locked_seats:

        seat.status = 'booked'

        seat.save()

    return redirect('movie_booking', movie_id=movie.id)

# PAYMENT PAGE

def payment_page(request, movie_id):

    if not request.user.is_authenticated:

        return redirect('login')

    movie = get_object_or_404(Movie, id=movie_id)

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    amount = 5000

    razorpay_order = client.order.create({

        'amount': amount,

        'currency': 'INR',

        'payment_capture': '1'

    })

    payment = Payment.objects.create(

        user=request.user,

        movie=movie,

        razorpay_order_id=razorpay_order['id'],

        amount=amount,

        status='created'

    )

    context = {

        'movie': movie,

        'payment': payment,

        'razorpay_key': settings.RAZORPAY_KEY_ID,

        'amount': amount,

        'order_id': razorpay_order['id']

    }

    return render(
        request,
        'booking/payment.html',
        context
    )


# VERIFY PAYMENT

@csrf_exempt
@csrf_exempt
def verify_payment(request):

    if request.method == 'POST':

        data = json.loads(request.body)

        razorpay_payment_id = data.get(
            'razorpay_payment_id'
        )

        razorpay_order_id = data.get(
            'razorpay_order_id'
        )

        razorpay_signature = data.get(
            'razorpay_signature'
        )

        client = razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET
            )
        )

        try:

            client.utility.verify_payment_signature({

                'razorpay_order_id': razorpay_order_id,

                'razorpay_payment_id': razorpay_payment_id,

                'razorpay_signature': razorpay_signature

            })

            payment = Payment.objects.get(
                razorpay_order_id=razorpay_order_id
            )

            if payment.status == 'paid':

                return JsonResponse({

                    'status': 'duplicate'

                })

            payment.razorpay_payment_id = razorpay_payment_id

            payment.razorpay_signature = razorpay_signature

            payment.status = 'paid'

            payment.save()

            locked_seats = Seat.objects.filter(

                movie=payment.movie,

                status='locked',

                locked_by=payment.user

            )

            for seat in locked_seats:

                seat.status = 'booked'

                seat.save()

            send_ticket_email_background(

                payment.user,

                payment,

                list(locked_seats)

            )

            return JsonResponse({

                'status': 'success'

            })

        except Exception:

            try:

                payment = Payment.objects.get(
                    razorpay_order_id=razorpay_order_id
                )

                payment.status = 'failed'

                payment.save()

            except Exception:
                pass

            return JsonResponse({

                'status': 'failed'

            })

    return JsonResponse({

        'status': 'invalid request'

    })
@csrf_exempt
def razorpay_webhook(request):

    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET

    received_signature = request.headers.get(
        'X-Razorpay-Signature'
    )

    body = request.body.decode('utf-8')

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    try:

        client.utility.verify_webhook_signature(
            body,
            received_signature,
            webhook_secret
        )

        data = json.loads(body)

        event = data.get('event')

        if event == 'payment.captured':

            payment_entity = data['payload']['payment']['entity']

            razorpay_order_id = payment_entity['order_id']

            razorpay_payment_id = payment_entity['id']

            payment = Payment.objects.get(
                razorpay_order_id=razorpay_order_id
            )

            # IDEMPOTENCY CHECK

            if payment.status == 'paid':

                return JsonResponse({

                    'status': 'already processed'

                })

            payment.razorpay_payment_id = razorpay_payment_id

            payment.status = 'paid'

            payment.save()

        return JsonResponse({

            'status': 'webhook success'

        })

    except Exception:

        return JsonResponse({

            'status': 'webhook failed'

        })

@staff_member_required
def admin_dashboard(request):

    cached_data = cache.get('dashboard_data')

    if cached_data:

        return render(
            request,
            'booking/admin_dashboard.html',
            cached_data
        )

    today = timezone.now()

    # DAILY REVENUE

    daily_revenue = Payment.objects.filter(
        status='paid',
        created_at__date=today.date()
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0

    # WEEKLY REVENUE

    weekly_revenue = Payment.objects.filter(
        status='paid',
        created_at__gte=today - timedelta(days=7)
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0

    # MONTHLY REVENUE

    monthly_revenue = Payment.objects.filter(
        status='paid',
        created_at__month=today.month
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0

    # POPULAR MOVIES

    popular_movies = Payment.objects.filter(
        status='paid'
    ).values(
        'movie__title'
    ).annotate(
        total_bookings=Count('id')
    ).order_by('-total_bookings')[:5]
        # BUSIEST THEATERS

    busiest_theaters = []

    theaters = Seat.objects.values(
        'theater_name'
    ).distinct()

    for theater in theaters:

        theater_name = theater['theater_name']

        total_seats = Seat.objects.filter(
            theater_name=theater_name
        ).count()

        booked_seats = Seat.objects.filter(
            theater_name=theater_name,
            status='booked'
        ).count()

        occupancy_rate = 0

        if total_seats > 0:

            occupancy_rate = (
                booked_seats / total_seats
            ) * 100

        busiest_theaters.append({

            'theater_name': theater_name,

            'occupancy_rate': round(
                occupancy_rate,
                2
            )

        })

    # PEAK BOOKING HOURS

    peak_hours = Payment.objects.filter(
        status='paid'
    ).annotate(
        hour=ExtractHour('created_at')
    ).values(
        'hour'
    ).annotate(
        total=Count('id')
    ).order_by('-total')[:5]

    # CANCELLATION RATE

    cancellation_rate = Payment.objects.filter(
        is_cancelled=True
    ).count()

    total_payments = Payment.objects.count()

    cancellation_percentage = 0

    if total_payments > 0:

        cancellation_percentage = (
            cancellation_rate / total_payments
        ) * 100

    data = {

        'busiest_theaters': busiest_theaters,
        
        'daily_revenue': daily_revenue / 100,

        'weekly_revenue': weekly_revenue / 100,

        'monthly_revenue': monthly_revenue / 100,

        'popular_movies': popular_movies,

        'peak_hours': peak_hours,

        'cancellation_percentage': round(
            cancellation_percentage,
            2
        )

    }

    cache.set(
        'dashboard_data',
        data,
        timeout=60
    )

    return render(
        request,
        'booking/admin_dashboard.html',
        data
    )