from django.contrib import admin
from .models import Event
from .models import Event, Booking, Organizer

admin.site.register(Event)
admin.site.register(Booking)
admin.site.register(Organizer)

