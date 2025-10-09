from django.contrib import admin
from django.urls import path
from dashboard.views import home
from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("scrape/gemilang/", views.trigger_scrape, name="trigger_scrape"),
]
