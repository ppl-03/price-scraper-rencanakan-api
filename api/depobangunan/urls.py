from django.urls import path
from . import views

app_name = 'depobangunan'

urlpatterns = [
    path('scrape/', views.scrape_products, name='scrape_products'),
]