from django.urls import path
from . import views


urlpatterns = [

    path('', views.index, name='home'),

    path('login/', views.login_view, name='login'),

    path("register/", views.register_view, name="register"),

    path("events/", views.events, name="events"),

    path("event-details/", views.event_details, name="event_details"),

    path("booking/", views.booking, name="booking"),

    path("payment/", views.payment, name="payment"),

    path("success/", views.success, name="success"),

    path("about/", views.about, name="about"),

    path("contact/", views.contact, name="contact"),

    path("profile/", views.profile, name="profile"),

    path('my-bookings/', views.my_bookings, name='my_bookings')
    


]