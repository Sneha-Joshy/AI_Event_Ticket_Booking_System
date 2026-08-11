import re
import base64
import qrcode
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

from .models import Event, Booking, Organizer
from django.contrib.auth.decorators import login_required

from django.http import HttpResponse, JsonResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from io import BytesIO


from google import genai

client = genai.Client()


@login_required
def booking(request, id):

    event = get_object_or_404(
        Event,
        id=id,
        status="Approved"
    )

    if request.method == "POST":
     if not request.user.email:
        messages.error(
            request,
            "Please add an email address to your profile before booking."
        )

        return redirect("profile")

        try:
            tickets = int(request.POST.get("tickets", 0))
        except (TypeError, ValueError):
            tickets = 0

        if tickets <= 0:

            messages.error(
                request,
                "Please select at least 1 ticket."
            )

            return render(
                request,
                "booking/booking.html",
                {"event": event}
            )

        if tickets > event.available_seats:

            messages.error(
                request,
                f"Only {event.available_seats} seats are available."
            )

            return render(
                request,
                "booking/booking.html",
                {"event": event}
            )

        total_amount = event.ticket_price * tickets

        new_booking = Booking.objects.create(
            event=event,
            customer_name=request.user.get_full_name() or request.user.username,
            customer_email=request.user.email,
            tickets=tickets,
            total_amount=total_amount
        )

        event.available_seats -= tickets
        event.save()

        return redirect(
            "payment",
            id=new_booking.id
        )

    return render(
        request,
        "booking/booking.html",
        {
            "event": event
        }
    )



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

    events = Event.objects.filter(
        status="Approved"
    ).order_by("date", "time")

    return render(
        request,
        "booking/events.html",
        {
            "events": events
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

        messages.success(
            request,
            "Payment successful!"
        )

        return redirect(
            "success",
            id=booking.id
        )

    return render(
        request,
        "booking/payment.html",
        {
            "booking": booking
        }
    )

@login_required
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
@login_required
def view_ticket(request, id):

    booking = get_object_or_404(
        Booking,
        id=id,
        customer_email=request.user.email
    )

    qr_data = (
        f"Booking ID: {booking.id}\n"
        f"Customer: {booking.customer_name}\n"
        f"Event: {booking.event.event_name}\n"
        f"Date: {booking.event.date}\n"
        f"Tickets: {booking.tickets}"
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
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawCentredString(
        width / 2,
        height - 70,
        "AI Event Booking"
    )

    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawCentredString(
        width / 2,
        height - 110,
        "DIGITAL EVENT TICKET"
    )

    # Line
    pdf.line(
        50,
        height - 130,
        width - 50,
        height - 130
    )

    # Event name
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(
        60,
        height - 175,
        booking.event.event_name
    )

    pdf.setFont("Helvetica", 12)

    y = height - 220

    pdf.drawString(60, y, f"Booking ID: #{booking.id}")
    y -= 30

    pdf.drawString(60, y, f"Customer: {booking.customer_name}")
    y -= 30

    pdf.drawString(60, y, f"Email: {booking.customer_email}")
    y -= 30

    pdf.drawString(60, y, f"Date: {booking.event.date}")
    y -= 30

    pdf.drawString(60, y, f"Time: {booking.event.time}")
    y -= 30

    pdf.drawString(60, y, f"Venue: {booking.event.venue}")
    y -= 30

    pdf.drawString(60, y, f"Tickets: {booking.tickets}")
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

    y -= 60

    pdf.setFont("Helvetica-Bold", 14)

    pdf.drawString(
        60,
        y,
        "Status: CONFIRMED"
    )

    pdf.setFont("Helvetica", 10)

    pdf.drawCentredString(
        width / 2,
        50,
        "Please present this ticket at the event entrance."
    )

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