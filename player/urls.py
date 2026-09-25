from django.urls import path

from . import views

app_name = "player"

urlpatterns = [
    path("", views.track_list, name="track_list"),
    path("favourites/", views.favourites, name="favourites"),
    path("recent/", views.recent, name="recent"),
    path("tracks/<int:pk>/played/", views.played, name="played"),
    path("tracks/<int:pk>/favourite/", views.favourite_toggle, name="favourite_toggle"),
]
