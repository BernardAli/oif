from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("events/", views.events, name="events"),
    path("events/new/", views.event_create, name="event_create"),
    path("events/<int:pk>/", views.event_detail, name="event_detail"),
    path("events/<int:pk>/edit/", views.event_edit, name="event_edit"),
    path("events/<int:pk>/<str:action>/", views.event_action, name="event_action"),
    path("events/<int:event_pk>/registrations/<int:reg_pk>/",
         views.update_registration, name="update_registration"),
    path("donations/", views.donations_view, name="donations"),
    path("donations/<int:pk>/", views.donation_detail, name="donation_detail"),
    path("donations/<int:pk>/<str:action>/", views.donation_action,
         name="donation_action"),
    path("applications/", views.applications_view, name="applications"),
    path("applications/<int:pk>/<str:decision>/", views.review_application,
         name="review_application"),
    path("mentorship/", views.mentorship_view, name="mentorship"),
    path("mentorship/new/", views.mentorship_create, name="mentorship_create"),
    path("mentorship/<int:pk>/edit/", views.mentorship_edit, name="mentorship_edit"),
    path("members/", views.members_view, name="members"),
    path("members/<int:pk>/", views.member_detail, name="member_detail"),
    path("content/", views.content_view, name="content"),
    path("content/<str:section>/new/", views.content_create, name="content_create"),
    path("content/<str:section>/<int:pk>/delete/", views.content_delete,
         name="content_delete"),
    path("content/<str:section>/<int:pk>/", views.content_edit, name="content_edit"),
    path("enquiries/", views.enquiries_view, name="enquiries"),
    path("enquiries/messages/<int:pk>/<str:action>/", views.message_action,
         name="message_action"),
    path("enquiries/partners/<int:pk>/<str:action>/", views.partner_action,
         name="partner_action"),
    path("audit/", views.audit_view, name="audit"),
    path("api/analytics/", views.analytics_api, name="analytics_api"),
]
