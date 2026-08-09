import re
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

from .models import Event, Booking, Organizer
from django.contrib.auth.decorators import login_required



def booking(request, id):
    event = get_object_or_404(Event, id=id)

    if request.method == "POST":
        customer_name = request.POST.get("customer_name")
        customer_email = request.POST.get("customer_email")
        tickets = int(request.POST.get("tickets"))

        total_amount = event.ticket_price * tickets

        Booking.objects.create(
            event=event,
            customer_name=customer_name,
            customer_email=customer_email,
            tickets=tickets,
            total_amount=total_amount
        )

        return redirect("payment")

    return render(request, "booking/booking.html", {"event": event})







def event_details(request, id):
    event = get_object_or_404(Event, id=id)
    return render(request, "booking/event_details.html", {
        "event": event
    })




def index(request):
    return render(request, "booking/index.html")


def login_view(request):

    if request.method == "POST":

        user_type = request.POST.get("user_type")

        username = request.POST.get("username")

        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is None:

            return render(
                request,
                "booking/login.html",
                {
                    "error": "Invalid username or password."
                }
            )

        # CUSTOMER LOGIN
        if user_type == "customer":

            # Organizer should not login as customer
            if Organizer.objects.filter(user=user).exists():

                return render(
                    request,
                    "booking/login.html",
                    {
                        "error": "Please select Organizer as your user type."
                    }
                )

            # Admin should not login as customer
            if user.is_staff:

                return render(
                    request,
                    "booking/login.html",
                    {
                        "error": "Please select Admin as your user type."
                    }
                )

            login(request, user)

            return redirect("home")


        # ORGANIZER LOGIN
        elif user_type == "organizer":

            if Organizer.objects.filter(user=user).exists():

                login(request, user)

                return redirect("organizer_dashboard")

            return render(
                request,
                "booking/login.html",
                {
                    "error": "This account is not registered as an organizer."
                }
            )


        # ADMIN LOGIN
        elif user_type == "admin":

            if user.is_staff:

                login(request, user)

                return redirect("admin_dashboard")

            return render(
                request,
                "booking/login.html",
                {
                    "error": "You do not have admin access."
                }
            )


        else:

            return render(
                request,
                "booking/login.html",
                {
                    "error": "Please select a user type."
                }
            )

    return render(
        request,
        "booking/login.html"
    )

def register_view(request):

    if request.method == "POST":

        user_type = request.POST.get("user_type")

        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        # Check user type
        if user_type not in ["customer", "organizer"]:

            return render(
                request,
                "booking/register.html",
                {
                    "error": "Please select a valid user type."
                }
            )

        # Check username
        if User.objects.filter(username=username).exists():

            return render(
                request,
                "booking/register.html",
                {
                    "error": "Username already exists."
                }
            )

        # Check password match
        if password != confirm_password:

            return render(
                request,
                "booking/register.html",
                {
                    "error": "Passwords do not match."
                }
            )

        # Password length
        if len(password) < 8:

            return render(
                request,
                "booking/register.html",
                {
                    "error": "Password must be at least 8 characters long."
                }
            )

        # Uppercase
        if not re.search(r"[A-Z]", password):

            return render(
                request,
                "booking/register.html",
                {
                    "error": "Password must contain at least one uppercase letter."
                }
            )

        # Lowercase
        if not re.search(r"[a-z]", password):

            return render(
                request,
                "booking/register.html",
                {
                    "error": "Password must contain at least one lowercase letter."
                }
            )

        # Number
        if not re.search(r"\d", password):

            return render(
                request,
                "booking/register.html",
                {
                    "error": "Password must contain at least one number."
                }
            )

        # Special character
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):

            return render(
                request,
                "booking/register.html",
                {
                    "error": "Password must contain at least one special character."
                }
            )

        # ORGANIZER
        # Do NOT create User here.
        # Send organizer to the organizer registration page.

        if user_type == "organizer":

            return redirect("organizer_register")


        # CUSTOMER
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        messages.success(
            request,
            "Registration successful. Please login."
        )

        return redirect("login")

    return render(
        request,
        "booking/register.html"
    )
def events(request):
    events = Event.objects.filter(status=True)
    return render(request, 'booking/events.html', {'events': events})




def payment(request):
    return render(request, "booking/payment.html")

def success(request):
    return render(request, "booking/success.html")

def about(request):
    return render(request, "booking/about.html")

def contact(request):
    return render(request, "booking/contact.html")

@login_required
def profile(request):

    return render(
        request,
        "booking/profile.html",
        {
            "customer": request.user
        }
    )

@login_required
def my_bookings(request):

    bookings = Booking.objects.filter(
        customer_email=request.user.email
    ).order_by("-booking_date")

    return render(
        request,
        "booking/my_bookings.html",
        {
            "bookings": bookings
        }
    )

def organizer_register(request):

    if request.method == "POST":

        organization_name = request.POST.get("organization_name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        address = request.POST.get("address")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if User.objects.filter(username=username).exists():
            return render(request, "booking/organizer_register.html", {
                "error": "Username already exists."
            })

        if password != confirm_password:
            return render(request, "booking/organizer_register.html", {
                "error": "Passwords do not match."
            })

        if len(password) < 8:
            return render(request, "booking/organizer_register.html", {
                "error": "Password must be at least 8 characters long."
            })

        if not re.search(r"[A-Z]", password):
            return render(request, "booking/organizer_register.html", {
                "error": "Password must contain at least one uppercase letter."
            })

        if not re.search(r"[a-z]", password):
            return render(request, "booking/organizer_register.html", {
                "error": "Password must contain at least one lowercase letter."
            })

        if not re.search(r"\d", password):
            return render(request, "booking/organizer_register.html", {
                "error": "Password must contain at least one number."
            })

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return render(request, "booking/organizer_register.html", {
                "error": "Password must contain at least one special character."
            })

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        Organizer.objects.create(
            user=user,
            organization_name=organization_name,
            phone=phone,
            address=address
        )

        messages.success(
            request,
            "Organizer registered successfully. Please login."
        )

        return redirect("organizer_login")

    return render(request, "booking/organizer_register.html")




def organizer_login(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            if Organizer.objects.filter(user=user).exists():

                login(request, user)

                messages.success(
                    request,
                    f"Welcome {user.username}! You have logged in successfully."
                )

                return redirect("organizer_dashboard")

            else:
                return render(
                    request,
                    "booking/organizer_login.html",
                    {
                        "error": "You are not registered as an organizer."
                    }
                )

        return render(
            request,
            "booking/organizer_login.html",
            {
                "error": "Invalid username or password."
            }
        )

    return render(request, "booking/organizer_login.html")
def organizer_dashboard(request):

    try:
        organizer = Organizer.objects.get(user=request.user)
    except Organizer.DoesNotExist:
        messages.error(request, "Organizer account not found. Please register as an organizer.")
        return redirect("organizer_register")

    return render(
        request,
        "booking/organizer_dashboard.html",
        {
            "organizer": organizer
        }
    )
 

def add_event(request):

    if not Organizer.objects.filter(user=request.user).exists():
        messages.error(request, "Please login as an organizer.")
        return redirect("organizer_login")

    organizer = Organizer.objects.get(user=request.user)

    if request.method == "POST":

        event_name = request.POST.get("event_name")
        category = request.POST.get("category")
        description = request.POST.get("description")
        date = request.POST.get("date")
        time = request.POST.get("time")

        booking_deadline = request.POST.get("booking_deadline")
        event_type = request.POST.get("event_type")

        venue = request.POST.get("venue")
        contact_number = request.POST.get("contact_number")

        ticket_price = request.POST.get("ticket_price")
        total_seats = request.POST.get("total_seats")

        image = request.FILES.get("image")

        terms = request.POST.get("terms")

        Event.objects.create(

            organizer=organizer,

            event_name=event_name,
            category=category,
            description=description,

            date=date,
            time=time,

            booking_deadline=booking_deadline,
            event_type=event_type,

            venue=venue,
            contact_number=contact_number,

            ticket_price=ticket_price,

            total_seats=total_seats,
            available_seats=total_seats,

            image=image,

            terms=terms,

            status="Pending"
        )

        messages.success(
            request,
            "Event submitted successfully. Waiting for admin approval."
        )

        return redirect("organizer_dashboard")

    return render(
        request,
        "booking/add_event.html"
    )

@login_required
def my_events(request):

    organizer = Organizer.objects.get(user=request.user)

    events = Event.objects.filter(organizer=organizer)

    return render(
        request,
        "booking/my_events.html",
        {
            "events": events
        }
    )
def edit_event(request, id):

    event = get_object_or_404(Event, id=id)

    if request.method == "POST":

        event.event_name = request.POST.get("event_name")
        event.category = request.POST.get("category")
        event.description = request.POST.get("description")
        event.date = request.POST.get("date")
        event.time = request.POST.get("time")
        event.venue = request.POST.get("venue")
        event.ticket_price = request.POST.get("ticket_price")
        event.total_seats = request.POST.get("total_seats")

        if request.FILES.get("image"):
            event.image = request.FILES.get("image")

        event.save()

        messages.success(request, "Event updated successfully.")

        return redirect("my_events")

    return render(
        request,
        "booking/edit_event.html",
        {
            "event": event
        }
    )


@login_required
def delete_event(request, id):

    organizer = Organizer.objects.get(user=request.user)

    event = get_object_or_404(
        Event,
        id=id,
        organizer=organizer
    )

    if request.method == "POST":

        event.delete()

        messages.success(
            request,
            "Event deleted successfully."
        )

        return redirect("my_events")

    return render(
        request,
        "booking/delete_event.html",
        {
            "event": event
        }
    )

@login_required
def view_bookings(request, id):

    organizer = Organizer.objects.get(user=request.user)

    event = get_object_or_404(
        Event,
        id=id,
        organizer=organizer
    )

    bookings = Booking.objects.filter(event=event)

    return render(
        request,
        "booking/view_bookings.html",
        {
            "event": event,
            "bookings": bookings
        }
    )
@user_passes_test(lambda user: user.is_staff)
def admin_dashboard(request):

    total_events = Event.objects.count()

    pending_events = Event.objects.filter(
        status="Pending"
    ).count()

    approved_events = Event.objects.filter(
        status="Approved"
    ).count()

    rejected_events = Event.objects.filter(
        status="Rejected"
    ).count()

    total_organizers = Organizer.objects.count()

    total_bookings = Booking.objects.count()

    return render(
        request,
        "booking/admin_dashboard.html",
        {
            "total_events": total_events,
            "pending_events": pending_events,
            "approved_events": approved_events,
            "rejected_events": rejected_events,
            "total_organizers": total_organizers,
            "total_bookings": total_bookings,
        }
    )

@user_passes_test(lambda user: user.is_staff)
def pending_events(request):

    events = Event.objects.filter(status="Pending").order_by("-created_at")

    return render(
        request,
        "booking/pending_events.html",
        {
            "events": events
        }
    )
@user_passes_test(lambda user: user.is_staff)
def update_event_status(request, id, status):

    event = get_object_or_404(Event, id=id)

    if status in ["Approved", "Rejected"]:
        event.status = status
        event.save()

        messages.success(
            request,
            f"Event '{event.event_name}' has been {status.lower()}."
        )

    return redirect("pending_events")   

def admin_login(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None and user.is_staff:

            login(request, user)

            return redirect("admin_dashboard")

        return render(
            request,
            "booking/admin_login.html",
            {
                "error": "Invalid admin username or password."
            }
        )

    return render(
        request,
        "booking/admin_login.html"
    )





def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("home")
