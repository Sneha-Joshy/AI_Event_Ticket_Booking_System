from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from .models import Event


def index(request):
    return render(request, "booking/index.html")


def login_view(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect("home")

        else:
            return render(request, "booking/login.html", {
                "error": "Invalid username or password"
            })

    return render(request, "booking/login.html")

def register_view(request):

    if request.method == "POST":

        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if User.objects.filter(username=username).exists():
            return render(request, "booking/register.html", {
                "error": "Username already exists"
            })

        User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        return redirect("login")

    return render(request, "booking/register.html")

def events(request):
    events = Event.objects.filter(status=True)
    return render(request, 'booking/events.html', {'events': events})

def event_details(request):
    return render(request, "booking/event_details.html")

def booking(request):
    return render(request, "booking/booking.html")

def payment(request):
    return render(request, "booking/payment.html")

def success(request):
    return render(request, "booking/success.html")

def about(request):
    return render(request, "booking/about.html")

def contact(request):
    return render(request, "booking/contact.html")

def profile(request):
    return render(request, "booking/profile.html")

def my_bookings(request):
    return render(request, 'booking/my_bookings.html')
