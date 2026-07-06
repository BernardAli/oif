from django.urls import path
from engagement import views as engagement_views
from . import views

app_name = "pages"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("leadership/", views.leadership, name="leadership"),
    path("speakers/", views.speakers, name="speakers"),
    path("programs/", views.programs, name="programs"),
    path("programs/<str:wing>/", views.program_detail, name="program_detail"),
    path("events/<slug:slug>/", engagement_views.event_detail, name="event_detail"),
    path("events/<slug:slug>/calendar.ics", engagement_views.event_calendar,
         name="event_calendar"),
    path("impact/", views.impact, name="impact"),
    path("get-involved/", views.involved, name="involved"),
    path("donate/", views.donate, name="donate"),
    path("gallery/", views.gallery, name="gallery"),
    path("contact/", engagement_views.contact, name="contact"),
    path("policy/<slug:kind>/", views.policy, name="policy"),
]
