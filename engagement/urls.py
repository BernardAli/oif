from django.urls import path
from . import views

app_name = "engagement"

urlpatterns = [
    path("events/<slug:slug>/register/", views.register_event, name="register_event"),
    path("registrations/<int:pk>/cancel/", views.cancel_registration,
         name="cancel_registration"),
    path("apply/", views.apply, name="apply"),
    path("partner/", views.partner_enquiry, name="partner_enquiry"),
    path("newsletter/", views.newsletter_signup, name="newsletter_signup"),
]
