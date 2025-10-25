from django.urls import path
from . import views

app_name = 'juragan_material'

urlpatterns = [
    path('scrape/', views.scrape_products, name='scrape_products'),
    path('scrape-and-save/', views.scrape_and_save_products, name='scrape_and_save_products'),
]