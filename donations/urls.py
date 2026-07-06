from django.urls import path
from . import views

app_name = "donations"

urlpatterns = [
    path("give/", views.give, name="give"),
    path("callback/", views.callback, name="callback"),
    path("status/<str:reference>/", views.status, name="status"),
]
