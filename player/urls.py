from django.urls import path

from . import views

app_name = "player"

urlpatterns = [
    path("", views.track_list, name="track_list"),
]
