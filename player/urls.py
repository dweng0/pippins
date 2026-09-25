from django.urls import path

from . import views

app_name = "player"

urlpatterns = [
    path("", views.track_list, name="track_list"),
    path("favourites/", views.favourites, name="favourites"),
    path("tracks/<int:pk>/favourite/", views.favourite_toggle, name="favourite_toggle"),
]
