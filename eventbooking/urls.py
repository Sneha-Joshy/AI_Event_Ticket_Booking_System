from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from booking import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('booking.urls')),
    path(
    "verify-ticket/<uuid:ticket_code>/",
    views.verify_ticket,
    name="verify_ticket"
),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)