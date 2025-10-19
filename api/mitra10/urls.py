from django.urls import path
from . import views

app_name = 'mitra10'

urlpatterns = [
    path('scrape/', views.scrape_products, name='scrape_products'),
    path('locations/', views.scrape_locations, name='scrape_locations'),
]