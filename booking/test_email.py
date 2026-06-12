from django.core.mail import send_mail

send_mail(
    'SafeStream Test',
    'Email system working',
    None,
    ['yourgmail@gmail.com'],
    fail_silently=False
)

print("Email sent")