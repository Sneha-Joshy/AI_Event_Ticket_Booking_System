from django.urls import path
from . import views
from django.contrib import admin
from django.urls import path, include



urlpatterns = [

    path('', views.index, name='home'),

    path('login/', views.login_view, name='login'),

    path("register/", views.register_view, name="register"),

    path("events/", views.events, name="events"),

    path('event/<int:id>/', views.event_details, name='event_details'),

    path("booking/<int:id>/", views.booking, name="booking"),

    path("payment/<int:id>/", views.payment, name="payment"),

    path("success/<int:id>/", views.success, name="success"),

    path("view-ticket/<int:id>/", views.view_ticket, name="view_ticket"),

    path(
    "download-ticket/<int:id>/",
    views.download_ticket_pdf,
    name="download_ticket_pdf"
),



    path("about/", views.about, name="about"),

    path("contact/", views.contact, name="contact"),

    path("profile/", views.profile, name="profile"),

    path('my-bookings/', views.my_bookings, name='my_bookings'),

    path("organizer/register/", views.organizer_register, name="organizer_register"),

    path("organizer/login/", views.organizer_login, name="organizer_login"),

    path("logout/", views.logout_view, name="logout"),

    path("organizer/add-event/", views.add_event, name="add_event"),


    path(
    "organizer/dashboard/",
    views.organizer_dashboard,
    name="organizer_dashboard"
),

    path(
    "organizer/my-events/",
    views.my_events,
    name="my_events"
),

    path(
    "organizer/edit-event/<int:id>/",
    views.edit_event,
    name="edit_event"
),
    path(
    "organizer/delete-event/<int:id>/",
    views.delete_event,
    name="delete_event"
),

    path(
    "organizer/edit-event/<int:id>/",
    views.edit_event,
    name="edit_event"
),

    path(
    "organizer/view-bookings/<int:id>/",
    views.view_bookings,
    name="view_bookings"
),

    path(
    "admin-dashboard/",
    views.admin_dashboard,
    name="admin_dashboard"
),
    path(
    "admin-dashboard/pending-events/",
    views.pending_events,
    name="pending_events"
),

    path(
    "admin-dashboard/event-status/<int:id>/<str:status>/",
    views.update_event_status,
    name="update_event_status"
),
    path(
    "organizer/ticket-sales/",
    views.ticket_sales,
    name="ticket_sales"
),
    path(
    "organizer/bookings/",
    views.organizer_bookings,
    name="organizer_bookings"
),
     
    path(
    "admin-login/",
    views.admin_login,
    name="admin_login"
),
    path("chatbot/", views.chatbot, name="chatbot"),
   path(
    "admin-dashboard/manage-users/",
    views.manage_users,
    name="manage_users"
),

    path(
    "admin-dashboard/toggle-user/<int:id>/",
    views.toggle_user_status,
    name="toggle_user_status"
),
    path(
    "ticket/download/<str:token>/",
    views.qr_download_ticket,
    name="qr_download_ticket"
),
    path(
    "admin-dashboard/customer-enquiries/",
    views.customer_enquiries,
    name="customer_enquiries"
),
    path(
    "admin-dashboard/resolve-enquiry/<int:id>/",
    views.resolve_enquiry,
    name="resolve_enquiry"
),
    path(
    "notifications/",
    views.notifications,
    name="notifications"
),

]