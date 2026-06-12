from django.urls import path

from . import views


urlpatterns = [

    path(
        '<int:movie_id>/',
        views.movie_booking,
        name='movie_booking'
    ),
    path(
    'webhook/',
    views.razorpay_webhook,
    name='razorpay_webhook'
    ),
    path(
    'admin-dashboard/',
    views.admin_dashboard,
    name='admin_dashboard'
    ), 

    path(
        'lock/<int:seat_id>/',
        views.lock_seat,
        name='lock_seat'
    ),

    path(
        'confirm/<int:movie_id>/',
        views.confirm_booking,
        name='confirm_booking'
    ),

    path(
        'payment/<int:movie_id>/',
        views.payment_page,
        name='payment_page'
    ),

    path(
        'verify-payment/',
        views.verify_payment,
        name='verify_payment'
    ),

    path(
        'signup/',
        views.signup_view,
        name='signup'
    ),

    path(
        'login/',
        views.login_view,
        name='login'
    ),

    path(
        'logout/',
        views.logout_view,
        name='logout'
    ),

]