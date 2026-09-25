from django.contrib import admin

from .models import Favourite, Listener, Play, Track

admin.site.register(Track)
admin.site.register(Listener)
admin.site.register(Favourite)
admin.site.register(Play)
