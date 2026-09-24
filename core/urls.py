from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.task_list, name="task_list"),
    path("home/", views.home, name="home"),
    path("healthz/", views.healthz, name="healthz"),
    path("api/tasks/", views.api_create_task, name="api_create_task"),
]
