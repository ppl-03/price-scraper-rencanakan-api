from django.urls import path
from . import views

app_name = 'depobangunan'

urlpatterns = [
    path('scrape/', views.scrape_products, name='scrape_products'),
    path('locations/', views.depobangunan_locations_view, name='depobangunan_locations'),
    path('scrape-and-save/', views.scrape_and_save_products, name='scrape_and_save_products'),
    path('scrape-popularity/', views.scrape_popularity, name='scrape_popularity'),
]