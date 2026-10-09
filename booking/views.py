import re
import base64
import qrcode
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.files import File
from django.urls import reverse

from django.shortcuts import render, get_object_or_404
from django.db.models import Q


from datetime import datetime, timedelta



from .models import Booking, Event, Seat, Organizer
from django.contrib.auth.decorators import login_required

from django.http import HttpResponse, JsonResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

from io import BytesIO
from django.utils import timezone
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired

from .models import Event, Booking, Organizer, ContactMessage, Notification
from google import genai

from .models import *

from django.core.mail import send_mail
from django.conf import settings

from reportlab.pdfgen import canvas


from django.http import HttpResponse

client = genai.Client()

@login_required
def booking(request, id):

    # Organizers cannot book tickets
    if Organizer.objects.filter(user=request.user).exists():
        messages.error(
            request,
            "Organizers cannot book tickets."
        )
        return redirect("events")

    event = get_object_or_404(
        Event,
        id=id,
        status="Approved"
    )

    # Check booking deadline
    if (
        event.booking_deadline
        and timezone.now() > event.booking_deadline
    ):
        messages.error(
            request,
            "Booking for this event has closed."
        )
        return redirect("events")

    # Get seats for this event
    seats = Seat.objects.filter(
        event=event
    ).order_by("id")

    if request.method == "POST":

        # Check email
        if not request.user.email:
            messages.error(
                request,
                "Please add an email address to your profile before booking."
            )
            return redirect("profile")

        # Get selected seats
        selected_seat_ids = request.POST.getlist("selected_seats")

        if not selected_seat_ids:
            messages.error(
                request,
                "Please select at least one seat."
            )

            return render(
                request,
                "booking/booking.html",
                {
                    "event": event,
                    "seats": seats
                }
            )

        # Get selected seats belonging to this event
        selected_seats = Seat.objects.filter(
            id__in=selected_seat_ids,
            event=event,
            is_booked=False
        )

        # Make sure all requested seats are available
        if selected_seats.count() != len(selected_seat_ids):

            messages.error(
                request,
                "One or more selected seats are no longer available. Please select again."
            )

            return redirect(
                "booking",
                id=event.id
            )

        tickets = selected_seats.count()

        total_amount = event.ticket_price * tickets

        # Create booking
        new_booking = Booking.objects.create(
            event=event,
            customer_name=(
                request.user.get_full_name()
                or request.user.username
            ),
            customer_email=request.user.email,
            tickets=tickets,
            total_amount=total_amount
        )

        # Attach selected seats to booking
        new_booking.seats.set(selected_seats)

        # Mark seats as booked
        selected_seats.update(
            is_booked=True
        )

        # Update available seats
        event.available_seats = Seat.objects.filter(
            event=event,
            is_booked=False
        ).count()

        event.save()

        return redirect(
            "payment",
            id=new_booking.id
        )
    return render(
     request,
        "booking/booking.html",
        {
            "event": event,
            "seats": seats
        }
    )
from django.utils import timezone


def event_details(request, id):

    event = get_object_or_404(
        Event,
        id=id,
        status="Approved"
    )

    return render(
        request,
        "booking/event_details.html",
        {
            "event": event,
            "now": timezone.now()
        }
    )

def index(request):

    today = timezone.localdate()

    featured_events = Event.objects.filter(
        status="Approved",
        date__gte=today
    ).values(
        "id",
        "event_name",
        "category",
        "description",
        "date",
        "time",
        "venue",
        "ticket_price",
        "available_seats",
        "image"
    ).order_by("date", "time")[:3]

    return render(
        request,
        "booking/index.html",
        {
            "featured_events": featured_events
        }
    )



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
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
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
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):

            return render(
                request,
                "booking/register.html",
                {
                    "error": "Password must contain at least one special character."
                }
            )

        # ==========================================
        # ORGANIZER REGISTRATION
        # ==========================================

        if user_type == "organizer":

            organization_name = request.POST.get("organization_name")
            phone_number = request.POST.get("phone_number")
            address = request.POST.get("address")

            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password
            )

            Organizer.objects.create(
                user=user,
                organization_name=organization_name,
                phone=phone_number,
                address=address
            )

            messages.success(
                request,
                "Organizer registration successful. Please login."
            )

            return redirect("login")

        # ==========================================
        # CUSTOMER REGISTRATION
        # ==========================================

        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
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
from django.utils import timezone
from django.db.models import Q


def events(request):

    category = request.GET.get("category")

    now = timezone.localtime()

    events = Event.objects.filter(
        status="Approved"
    ).filter(
        Q(date__gt=now.date()) |
        Q(date=now.date(), time__gte=now.time())
    ).values(
        "id",
        "event_name",
        "category",
        "date",
        "time",
        "venue",
        "ticket_price",
        "image"
    )

    if category and category != "All":
        events = events.filter(
            category__iexact=category
        )

    events = events.order_by("date", "time")

    return render(
        request,
        "booking/events.html",
        {
            "events": events,
            "selected_category": category
        }
    )
@login_required
def payment(request, id):

    booking = get_object_or_404(
        Booking,
        id=id,
        customer_email=request.user.email
    )

    if request.method == "POST":

        # ------------------------------------------
        # PAYMENT SUCCESS
        # ------------------------------------------

        payment_success = True

        if payment_success:

            # --------------------------------------
            # GENERATE QR CODE
            # --------------------------------------

            qr_data = request.build_absolute_uri(
                reverse(
                    "verify_ticket",
                    args=[booking.ticket_code]
                )
            )

            qr = qrcode.QRCode(
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=12,
                border=4
            )

            qr.add_data(qr_data)
            qr.make(fit=True)

            qr_image = qr.make_image()

            qr_buffer = BytesIO()

            qr_image.save(
                qr_buffer,
                format="PNG"
            )

            qr_buffer.seek(0)

            booking.qr_code.save(
                f"booking_{booking.id}.png",
                File(qr_buffer),
                save=True
            )

            # --------------------------------------
            # SEND CONFIRMATION EMAIL
            # --------------------------------------

            send_mail(
                subject="Booking Confirmation - AI Event Booking",

                message=f"""
Dear {booking.customer_name},

Your event ticket booking has been confirmed successfully.

Booking Details
----------------------------

Booking ID: #{booking.id}

Event: {booking.event.event_name}

Date: {booking.event.date}

Time: {booking.event.time}

Venue: {booking.event.venue}

Number of Tickets: {booking.tickets}

Total Amount: Rs. {booking.total_amount}

Thank you for using the AI-Powered Event Ticket Booking System.

Please keep your digital ticket with you for the event.

Regards,
AI Event Booking Team
""",

                from_email=None,

                recipient_list=[
                    booking.customer_email
                ],

                fail_silently=False,
            )

            messages.success(
                request,
                "Payment successful! Booking confirmation email sent."
            )

            return redirect(
                "success",
                id=booking.id
            )

    # --------------------------------------
    # DISPLAY PAYMENT PAGE
    # --------------------------------------

    return render(
        request,
        "booking/payment.html",
        {
            "booking": booking
        }
    )

def success(request, id):

    booking = get_object_or_404(
        Booking,
        id=id,
        customer_email=request.user.email
    )

    return render(
        request,
        "booking/success.html",
        {
            "booking": booking
        }
    )

def about(request):
    return render(request, "booking/about.html")


def contact(request):

    if request.method == "POST":

        name = request.POST.get("name")
        email = request.POST.get("email")
        subject = request.POST.get("subject")
        message = request.POST.get("message")

        if not name or not email or not subject or not message:

            messages.error(
                request,
                "Please fill in all the fields."
            )

            return render(
                request,
                "booking/contact.html"
            )

        ContactMessage.objects.create(
            user=request.user,
            name=name,
            email=email,
            subject=subject,
            message=message
        )

        messages.success(
            request,
            "Your message has been submitted successfully. We will get back to you soon."
        )

        return redirect("contact")

    return render(
        request,
        "booking/contact.html"
    )


@login_required
def profile(request):

    organizer = Organizer.objects.filter(
        user=request.user
    ).first()

    return render(
        request,
        "booking/profile.html",
        {
            "customer": request.user,
            "organizer": organizer
        }
    )


@login_required
def my_bookings(request):

    today = timezone.localdate()

    bookings = Booking.objects.filter(
        customer_email=request.user.email,
        event__date__gte=today
    ).order_by("-booking_date")

    return render(
        request,
        "booking/my_bookings.html",
        {"bookings": bookings}
    )

@login_required
def cancel_booking(request, id):

    booking = get_object_or_404(
        Booking,
        id=id,
        customer_email=request.user.email
    )

    # Only allow cancellation of confirmed bookings
    if booking.status == "Cancelled":
        messages.error(
            request,
            "This booking has already been cancelled."
        )
        return redirect("my_bookings")

    # Do not allow cancellation after ticket has been used
    if booking.ticket_used:
        messages.error(
            request,
            "This ticket has already been used and cannot be cancelled."
        )
        return redirect("my_bookings")

    # Check cancellation deadline
    if timezone.now().date() >= booking.event.date:
        messages.error(
            request,
            "This booking cannot be cancelled on or after the event date."
        )
        return redirect("my_bookings")

    if request.method == "POST":

        # Release the selected seats
        booking.seats.update(
            is_booked=False
        )

        # Update available seats
        booking.event.available_seats = Seat.objects.filter(
            event=booking.event,
            is_booked=False
        ).count()

        booking.event.save(
            update_fields=["available_seats"]
        )

        # Change booking status
        booking.status = "Cancelled"

        booking.save(
            update_fields=["status"]
        )

        # Get seat numbers before sending email
        seat_numbers = ", ".join(
            booking.seats.values_list(
                "seat_number",
                flat=True
            )
        )

        # SEND CANCELLATION EMAIL
        send_mail(
            subject="Booking Cancellation Confirmation - AI Event Booking",

            message=f"""
Dear {booking.customer_name},

Your event ticket booking has been cancelled successfully.

Cancellation Details
----------------------------

Booking ID: #{booking.id}

Event: {booking.event.event_name}

Date: {booking.event.date}

Time: {booking.event.time}

Venue: {booking.event.venue}

Number of Tickets: {booking.tickets}

Seat Number(s): {seat_numbers}

Total Amount: Rs. {booking.total_amount}

Booking Status: CANCELLED

Your selected seats have been released and are now available for other customers.

Thank you for using the AI-Powered Event Ticket Booking System.

Regards,
AI Event Booking Team
""",

            from_email=None,
            recipient_list=[booking.customer_email],
            fail_silently=False,
        )

        messages.success(
            request,
            "Booking cancelled successfully. Cancellation email sent."
        )

        return redirect("my_bookings")

    return render(
        request,
        "booking/cancel_booking.html",
        {
            "booking": booking
        }
    )



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

from datetime import datetime, timedelta
from django.utils import timezone


def add_event(request):

    # Only organizers can add events
    if not Organizer.objects.filter(user=request.user).exists():
        messages.error(
            request,
            "Please login as an organizer."
        )
        return redirect("organizer_login")

    organizer = Organizer.objects.get(
        user=request.user
    )

    if request.method == "POST":

        event_name = request.POST.get("event_name")
        category = request.POST.get("category")
        description = request.POST.get("description")

        date = request.POST.get("date")
        time = request.POST.get("time")

        event_type = request.POST.get("event_type")

        venue = request.POST.get("venue")
        contact_number = request.POST.get("contact_number")

        ticket_price = request.POST.get("ticket_price")
        total_seats = int(
            request.POST.get("total_seats")
        )

        image = request.FILES.get("image")

        terms = request.POST.get("terms")

        # -------------------------------------------------
        # Calculate booking deadline automatically
        # 1 hour before the event
        # -------------------------------------------------

        event_datetime = datetime.strptime(
            f"{date} {time}",
            "%Y-%m-%d %H:%M"
        )

        event_datetime = timezone.make_aware(
            event_datetime
        )

        booking_deadline = (
            event_datetime - timedelta(hours=1)
        )

        # -------------------------------------------------
        # Create the event
        # -------------------------------------------------

        event = Event.objects.create(

            organizer=organizer,

            event_name=event_name,
            category=category,
            description=description,

            date=date,
            time=time,

            # Automatically calculated
            booking_deadline=booking_deadline,

            event_type=event_type,

            venue=venue,
            contact_number=contact_number,

            ticket_price=ticket_price,

            total_seats=total_seats,
            available_seats=total_seats,

            image=image,

            terms=terms,

            # Event needs admin approval
            status="Pending"
        )

        # -------------------------------------------------
        # Create individual seats
        # -------------------------------------------------

        for i in range(total_seats):

            row = chr(65 + (i // 100))
            seat_number = (i % 100) + 1

            Seat.objects.create(
                event=event,
                seat_number=f"{row}{seat_number}"
            )

        messages.success(
            request,
            "Event submitted successfully. Waiting for admin approval."
        )

        return redirect(
            "organizer_dashboard"
        )

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
@login_required
def organizer_bookings(request):

    organizer = Organizer.objects.get(user=request.user)

    events = Event.objects.filter(
        organizer=organizer
    )

    bookings = Booking.objects.filter(
        event__in=events
    ).select_related("event").order_by("-booking_date")

    return render(
        request,
        "booking/organizer_bookings.html",
        {
            "bookings": bookings
        }
    )


@login_required
def ticket_sales(request):

    organizer = Organizer.objects.get(user=request.user)

    events = Event.objects.filter(
        organizer=organizer
    )

    total_tickets = 0
    total_revenue = 0

    sales_data = []

    for event in events:

        bookings = Booking.objects.filter(
            event=event
        )

        tickets_sold = sum(
            booking.tickets
            for booking in bookings
        )

        revenue = sum(
            booking.total_amount
            for booking in bookings
        )

        total_tickets += tickets_sold
        total_revenue += revenue

        sales_data.append({
            "event": event,
            "tickets_sold": tickets_sold,
            "revenue": revenue
        })

    return render(
        request,
        "booking/ticket_sales.html",
        {
            "sales_data": sales_data,
            "total_tickets": total_tickets,
            "total_revenue": total_revenue
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
def manage_users(request):

    users = User.objects.all().order_by("-date_joined")

    return render(
        request,
        "booking/manage_users.html",
        {
            "users": users
        }
    )


@user_passes_test(lambda user: user.is_staff)
def toggle_user_status(request, id):

    user = get_object_or_404(User, id=id)

    # Prevent admin from deactivating their own account
    if user == request.user:
        messages.error(
            request,
            "You cannot deactivate your own admin account."
        )
        return redirect("manage_users")

    user.is_active = not user.is_active
    user.save()

    if user.is_active:
        messages.success(
            request,
            f"User '{user.username}' has been activated."
        )
    else:
        messages.success(
            request,
            f"User '{user.username}' has been deactivated."
        )

    return redirect("manage_users")

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

        admin_remarks = request.POST.get("admin_remarks", "").strip()

        if not admin_remarks:
            messages.error(
                request,
                "Please enter a reason before approving or rejecting the event."
            )
            return redirect("pending_events")

        event.status = status
        event.admin_remarks = admin_remarks
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
@login_required
def verify_ticket(request, ticket_code):

    # Only organizers can verify tickets
    organizer = Organizer.objects.filter(
        user=request.user
    ).first()

    if not organizer:
        messages.error(
            request,
            "Only organizers can verify tickets."
        )
        return redirect("events")

    # Find booking using unique ticket code
    booking = get_object_or_404(
        Booking,
        ticket_code=ticket_code
    )

    # Check whether this organizer owns the event
    if booking.event.organizer_id != organizer.id:
        return render(
            request,
            "booking/verify_ticket.html",
            {
                "booking": booking,
                "valid": False,
                "message": "You are not authorized to verify this ticket."
            }
        )

    # Check whether booking has been cancelled
    if booking.status == "Cancelled":
        return render(
            request,
            "booking/verify_ticket.html",
            {
                "booking": booking,
                "valid": False,
                "message": "This ticket has been cancelled and is no longer valid."
            }
        )

    # Check whether ticket has already been used
    if booking.ticket_used:
        return render(
            request,
            "booking/verify_ticket.html",
            {
                "booking": booking,
                "valid": False,
                "message": "This ticket has already been used."
            }
        )

    # Organizer confirms entry
    if request.method == "POST":

        booking.ticket_used = True

        booking.save(
            update_fields=["ticket_used"]
        )

        return render(
            request,
            "booking/verify_ticket.html",
            {
                "booking": booking,
                "valid": False,
                "used_successfully": True,
                "message": "Entry confirmed successfully."
            }
        )

    # Ticket is valid
    return render(
        request,
        "booking/verify_ticket.html",
        {
            "booking": booking,
            "valid": True
        }
    )
@login_required
def view_ticket(request, id):

    booking = get_object_or_404(
        Booking,
        id=id,
        customer_email=request.user.email
    )

    if booking.status == "Cancelled":
        messages.error(
            request,
            "This booking has been cancelled. The ticket is no longer valid."
        )
        return redirect("my_bookings")

    # Your existing QR code code stays here

    seat_numbers = ", ".join(
    booking.seats.values_list("seat_number", flat=True)
)

    qr_data = (
            f"Booking ID: {booking.id}\n"
            f"Customer: {booking.customer_name}\n"
           f"Event: {booking.event.event_name}\n"
            f"Date: {booking.event.date}\n"
           f"Tickets: {booking.tickets}\n"
           f"Seat Number: {seat_numbers}"
    )
    qr = qrcode.make(qr_data)

    buffer = BytesIO()

    qr.save(buffer, format="PNG")

    qr_base64 = base64.b64encode(
        buffer.getvalue()
    ).decode()

    return render(
        request,
        "booking/view_ticket.html",
        {
            "booking": booking,
            "qr_code": qr_base64
        }
    )
@login_required
def download_ticket_pdf(request, id):

    booking = get_object_or_404(
        Booking,
        id=id,
        customer_email=request.user.email
    )

    # --------------------------------------
    # DO NOT ALLOW CANCELLED TICKET
    # --------------------------------------

    if booking.status == "Cancelled":
        messages.error(
            request,
            "This booking has been cancelled. The ticket is no longer valid."
        )
        return redirect("my_bookings")

    # --------------------------------------
    # CREATE PDF RESPONSE
    # --------------------------------------

    response = HttpResponse(
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="ticket_{booking.id}.pdf"'
    )

    pdf = canvas.Canvas(
        response,
        pagesize=A4
    )

    width, height = A4

    # --------------------------------------
    # TITLE
    # --------------------------------------

    pdf.setFont(
        "Helvetica-Bold",
        24
    )

    pdf.drawCentredString(
        width / 2,
        height - 70,
        "AI Event Booking"
    )

    pdf.setFont(
        "Helvetica-Bold",
        20
    )

    pdf.drawCentredString(
        width / 2,
        height - 110,
        "DIGITAL EVENT TICKET"
    )

    pdf.line(
        50,
        height - 130,
        width - 50,
        height - 130
    )

    # --------------------------------------
    # EVENT NAME
    # --------------------------------------

    pdf.setFont(
        "Helvetica-Bold",
        16
    )

    pdf.drawString(
        60,
        height - 175,
        booking.event.event_name
    )

    pdf.setFont(
        "Helvetica",
        12
    )

    y = height - 220

    # --------------------------------------
    # BOOKING DETAILS
    # --------------------------------------

    pdf.drawString(
        60,
        y,
        f"Booking ID: #{booking.id}"
    )
    y -= 30

    pdf.drawString(
        60,
        y,
        f"Customer: {booking.customer_name}"
    )
    y -= 30

    pdf.drawString(
        60,
        y,
        f"Email: {booking.customer_email}"
    )
    y -= 30

    pdf.drawString(
        60,
        y,
        f"Date: {booking.event.date}"
    )
    y -= 30

    pdf.drawString(
        60,
        y,
        f"Time: {booking.event.time}"
    )
    y -= 30

    pdf.drawString(
        60,
        y,
        f"Venue: {booking.event.venue}"
    )
    y -= 30

    pdf.drawString(
        60,
        y,
        f"Tickets: {booking.tickets}"
    )
    y -= 30

    # --------------------------------------
    # SEAT NUMBERS
    # --------------------------------------

    seat_numbers = ", ".join(
        booking.seats.values_list(
            "seat_number",
            flat=True
        )
    )

    pdf.drawString(
        60,
        y,
        f"Seat Number: {seat_numbers}"
    )
    y -= 30

    # --------------------------------------
    # TOTAL AMOUNT
    # --------------------------------------

    pdf.drawString(
        60,
        y,
        f"Total Amount: Rs. {booking.total_amount}"
    )
    y -= 30

    # --------------------------------------
    # BOOKING DATE
    # --------------------------------------

    pdf.drawString(
        60,
        y,
        f"Booking Date: {booking.booking_date}"
    )

    y -= 60

    # --------------------------------------
    # STATUS
    # --------------------------------------

    pdf.setFont(
        "Helvetica-Bold",
        14
    )

    pdf.drawString(
        60,
        y,
        "Status: CONFIRMED"
    )

    # --------------------------------------
    # SAME QR CODE AS DIGITAL TICKET
    # --------------------------------------

    qr_data = (
        f"Booking ID: {booking.id}\n"
        f"Customer: {booking.customer_name}\n"
        f"Event: {booking.event.event_name}\n"
        f"Date: {booking.event.date}\n"
        f"Tickets: {booking.tickets}\n"
        f"Seat Number: {seat_numbers}"
    )

    qr = qrcode.make(qr_data)

    qr_buffer = BytesIO()

    qr.save(
        qr_buffer,
        format="PNG"
    )

    qr_buffer.seek(0)

    # --------------------------------------
    # ADD QR TO PDF
    # --------------------------------------

    pdf.drawImage(
        ImageReader(qr_buffer),
        width - 220,
        height - 430,
        width=150,
        height=150,
        preserveAspectRatio=True,
        mask="auto"
    )

    pdf.setFont(
        "Helvetica-Bold",
        11
    )

    pdf.drawCentredString(
        width - 145,
        height - 450,
        "Scan Ticket"
    )

    # --------------------------------------
    # FOOTER
    # --------------------------------------

    pdf.setFont(
        "Helvetica",
        10
    )

    pdf.drawCentredString(
        width / 2,
        50,
        "Please present this ticket at the event entrance."
    )

    # --------------------------------------
    # SAVE PDF
    # --------------------------------------

    pdf.save()

    return response
def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("home")


def chatbot(request):

    if request.method == "POST":

        user_message = request.POST.get("message", "").strip()

        if not user_message:
            return JsonResponse({
                "response": "Please enter a message."
            })

        # Get approved events from database
        events = Event.objects.filter(status="Approved")

        event_data = []

        for event in events:

            event_data.append(
                f"""
Event: {event.event_name}
Category: {event.category}
Date: {event.date}
Time: {event.time}
Venue: {event.venue}
Ticket Price: ₹{event.ticket_price}
Available Seats: {event.available_seats}
Description: {event.description}
"""
            )

        events_information = "\n".join(event_data)

        system_prompt = f"""
You are the AI Event Booking Assistant for an event ticket
booking website.

Answer the customer's questions politely and clearly.

Here are the approved events from the website database:

{events_information}

Important rules:

1. Only provide event information from the data above.
2. Do not invent events, prices, dates, venues or seat counts.
3. If the requested information is not available, say that
   you don't have that information.
4. Help users understand how to book tickets.
5. Keep answers concise, friendly and directly answer the user's question.
6. Do not start every response with "Hello".
7. Do not add unnecessary booking instructions unless the user asks how to book.
"""

        try:

            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=system_prompt + "\n\nUser question:\n" + user_message
            )

            answer = response.text

            return JsonResponse({
                "response": answer
            })

        except Exception as e:

            print("GEMINI ERROR:", repr(e))

            return JsonResponse({
                "response": f"API Error: {str(e)}"
            })

    return render(
        request,
        "booking/chatbot.html"
    )
def qr_download_ticket(request, token):

    signer = TimestampSigner()

    try:

        booking_id = signer.unsign(
            token,
            max_age=60 * 60 * 24 * 30
        )

    except SignatureExpired:

        return HttpResponse(
            "This ticket link has expired.",
            status=403
        )

    except BadSignature:

        return HttpResponse(
            "Invalid ticket link.",
            status=403
        )

    booking = get_object_or_404(
        Booking,
        id=booking_id
    )

    # Create PDF response
    response = HttpResponse(
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="ticket_{booking.id}.pdf"'
    )

    pdf = canvas.Canvas(
        response,
        pagesize=A4
    )

    width, height = A4

    # Title
    pdf.setFont(
        "Helvetica-Bold",
        24
    )

    pdf.drawCentredString(
        width / 2,
        height - 70,
        "AI Event Booking"
    )

    pdf.setFont(
        "Helvetica-Bold",
        20
    )

    pdf.drawCentredString(
        width / 2,
        height - 110,
        "DIGITAL EVENT TICKET"
    )

    pdf.line(
        50,
        height - 130,
        width - 50,
        height - 130
    )

    # Event
    pdf.setFont(
        "Helvetica-Bold",
        16
    )

    pdf.drawString(
        60,
        height - 175,
        booking.event.event_name
    )

    pdf.setFont(
        "Helvetica",
        12
    )

    y = height - 220

    pdf.drawString(
        60,
        y,
        f"Booking ID: #{booking.id}"
    )

    y -= 30

    pdf.drawString(
        60,
        y,
        f"Customer: {booking.customer_name}"
    )

    y -= 30

    pdf.drawString(
        60,
        y,
        f"Email: {booking.customer_email}"
    )

    y -= 30

    pdf.drawString(
        60,
        y,
        f"Date: {booking.event.date}"
    )

    y -= 30

    pdf.drawString(
        60,
        y,
        f"Time: {booking.event.time}"
    )

    y -= 30

    pdf.drawString(
        60,
        y,
        f"Venue: {booking.event.venue}"
    )

    y -= 30

    pdf.drawString(
        60,
        y,
        f"Tickets: {booking.tickets}"
    )

    y -= 30

    pdf.drawString(
        60,
        y,
        f"Total Amount: Rs. {booking.total_amount}"
    )

    y -= 30

    pdf.drawString(
        60,
        y,
        f"Booking Date: {booking.booking_date}"
    )

    y -= 50

    pdf.setFont(
        "Helvetica-Bold",
        14
    )

    pdf.drawString(
        60,
        y,
        "Status: CONFIRMED"
    )

    pdf.setFont(
        "Helvetica",
        10
    )

    pdf.drawCentredString(
        width / 2,
        50,
        "Please present this ticket at the event entrance."
    )

    pdf.save()

    return response
@user_passes_test(lambda user: user.is_staff)
def customer_enquiries(request):

    enquiries = ContactMessage.objects.all().order_by("-created_at")

    return render(
        request,
        "booking/customer_enquiries.html",
        {
            "enquiries": enquiries
        }
    )
@user_passes_test(lambda user: user.is_staff)
def resolve_enquiry(request, id):

    enquiry = get_object_or_404(
        ContactMessage,
        id=id
    )

    enquiry.status = "Resolved"
    enquiry.save()

    # Create notification for the customer
    if enquiry.user:

        Notification.objects.create(
            user=enquiry.user,
            
            message=(
                f"Your enquiry '{enquiry.subject}' "
                "has been resolved by the EventAI support team."
            )
        )
    
    messages.success(
        request,
        "Customer enquiry has been marked as resolved."
    )

    return redirect("customer_enquiries")



@login_required
def recommendations(request):

    # -------------------------------------------------
    # GET CUSTOMER'S PREVIOUS BOOKINGS
    # -------------------------------------------------

    previous_bookings = Booking.objects.filter(
        customer_email=request.user.email,
        status="Confirmed"
    ).select_related("event")

    preferred_categories = list(
        set(
            booking.event.category
            for booking in previous_bookings
        )
    )

    # -------------------------------------------------
    # GET UPCOMING APPROVED EVENTS
    # -------------------------------------------------

    today = timezone.localdate()

    available_events = Event.objects.filter(
        status="Approved",
        available_seats__gt=0,
        date__gte=today
    ).order_by("date", "time")

    # -------------------------------------------------
    # IF NO EVENTS
    # -------------------------------------------------

    if not available_events.exists():

        return render(
            request,
            "booking/recommendations.html",
            {
                "recommended_events": [],
                "preferred_categories": preferred_categories,
                "ai_reason": "No upcoming events are currently available."
            }
        )

    # -------------------------------------------------
    # PREPARE EVENT INFORMATION FOR AI
    # -------------------------------------------------

    event_data = []

    for event in available_events:

        event_data.append(
            f"""
ID: {event.id}
Event Name: {event.event_name}
Category: {event.category}
Description: {event.description}
Date: {event.date}
Venue: {event.venue}
Ticket Price: ₹{event.ticket_price}
Available Seats: {event.available_seats}
"""
        )

    events_information = "\n".join(event_data)

    # -------------------------------------------------
    # CUSTOMER INTEREST INFORMATION
    # -------------------------------------------------

    if preferred_categories:

        interests = ", ".join(
            preferred_categories
        )

        customer_information = (
            f"The customer previously booked events "
            f"from these categories: {interests}."
        )

    else:

        customer_information = (
            "The customer is a new user and has "
            "no previous booking history."
        )

    # -------------------------------------------------
    # AI RECOMMENDATION PROMPT
    # -------------------------------------------------

    prompt = f"""
You are an AI event recommendation system.

{customer_information}

Below is the list of currently available upcoming events:

{events_information}

Recommend the most relevant events for this customer.

Rules:

1. Recommend only events from the provided list.
2. Do not create or invent event IDs.
3. Consider the customer's previous interests when available.
4. Consider event category and description.
5. For a new customer, recommend a suitable variety of upcoming events.
6. Recommend a maximum of 6 events.
7. Return ONLY the event IDs separated by commas.
8. Do not include event names or explanations.

Example:
3,7,2,9
"""

    # -------------------------------------------------
    # CALL GEMINI
    # -------------------------------------------------

    try:

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt
        )

        ai_result = response.text.strip()

        # -------------------------------------------------
        # EXTRACT EVENT IDs
        # -------------------------------------------------

        recommended_ids = []

        for value in ai_result.split(","):

            value = value.strip()

            if value.isdigit():

                recommended_ids.append(
                    int(value)
                )

        # Remove duplicates
        recommended_ids = list(
            dict.fromkeys(recommended_ids)
        )[:6]

        # -------------------------------------------------
        # GET RECOMMENDED EVENTS FROM DATABASE
        # -------------------------------------------------

        events_dict = {
            event.id: event
            for event in available_events
        }

        recommended_events = [
            events_dict[event_id]
            for event_id in recommended_ids
            if event_id in events_dict
        ]

        # -------------------------------------------------
        # FALLBACK
        # -------------------------------------------------

        if not recommended_events:

            recommended_events = list(
                available_events[:6]
            )

            ai_reason = (
                "Showing upcoming events based on availability."
            )

        else:

            if preferred_categories:

                ai_reason = (
                    "AI recommendations are based on "
                    "your previous event interests."
                )

            else:

                ai_reason = (
                    "AI selected these events from "
                    "currently available upcoming events."
                )

    except Exception as e:

        print(
            "RECOMMENDATION AI ERROR:",
            repr(e)
        )

        # -------------------------------------------------
        # FALLBACK IF AI FAILS
        # -------------------------------------------------

        recommended_events = list(
            available_events[:6]
        )

        ai_reason = (
            "Showing upcoming events based on "
            "availability."
        )

    # -------------------------------------------------
    # DISPLAY RECOMMENDATIONS
    # -------------------------------------------------

    return render(
        request,
        "booking/recommendations.html",
        {
            "recommended_events": recommended_events,
            "preferred_categories": preferred_categories,
            "ai_reason": ai_reason
        }
    )
@login_required
def notifications(request):

    user_notifications = Notification.objects.filter(
        user=request.user
    ).order_by("-created_at")

    return render(
        request,
        "booking/notifications.html",
        {
            "notifications": user_notifications
        }
    )
