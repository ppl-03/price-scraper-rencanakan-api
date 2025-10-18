from django.urls import path
from . import views

app_name = 'tokopedia'

urlpatterns = [
    path('scrape/', views.scrape_products, name='scrape_products'),
    path('scrape-with-filters/', views.scrape_products_with_filters, name='scrape_products_with_filters'),
]