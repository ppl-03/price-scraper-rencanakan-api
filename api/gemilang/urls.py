from django.urls import path
from . import views

app_name = 'gemilang'

urlpatterns = [
    path('scrape/', views.scrape_products, name='scrape_products'),
    path('locations/', views.gemilang_locations_view, name='gemilang_locations'),
]