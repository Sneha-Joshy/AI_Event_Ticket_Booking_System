from django.db import models
from django.contrib.auth.models import User


class Organizer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organization_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=15)
    address = models.TextField()

    def __str__(self):
        return self.organization_name


class Event(models.Model):

    organizer = models.ForeignKey(
        Organizer,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    event_name = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    description = models.TextField()

    date = models.DateField()
    time = models.TimeField()

    booking_deadline = models.DateField(
        null=True,
        blank=True
    )

    event_type = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    venue = models.CharField(max_length=200)

    contact_number = models.CharField(
        max_length=10,
        null=True,
        blank=True
    )

    ticket_price = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )

    total_seats = models.PositiveIntegerField()

    available_seats = models.PositiveIntegerField()

    image = models.ImageField(
        upload_to="events/"
    )

    terms = models.TextField(
        null=True,
        blank=True
    )

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.event_name


class Booking(models.Model):

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE
    )

    customer_name = models.CharField(max_length=100)

    customer_email = models.EmailField()

    tickets = models.PositiveIntegerField()

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    booking_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer_name} - {self.event.event_name}"

class ContactMessage(models.Model):

    name = models.CharField(max_length=100)

    email = models.EmailField()

    subject = models.CharField(max_length=200)

    message = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=[
            ("Pending", "Pending"),
            ("Resolved", "Resolved"),
        ],
        default="Pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.subject}"    

class ContactMessage(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    name = models.CharField(
        max_length=100
    )

    email = models.EmailField()

    subject = models.CharField(
        max_length=200
    )

    message = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=[
            ("Pending", "Pending"),
            ("Resolved", "Resolved"),
        ],
        default="Pending"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.name} - {self.subject}" 



class Notification(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    message = models.TextField()

    is_read = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.message[:30]}"   


