from django.contrib import admin

from .models import Listener, Track

admin.site.register(Track)
admin.site.register(Listener)
