from django.urls import path
from . import views

app_name = 'government_wage'

urlpatterns = [
    path('scrape/', views.scrape_region_data, name='scrape_region_data'),
    path('search/', views.search_by_work_code, name='search_by_work_code'),
    path('regions/', views.get_available_regions, name='get_available_regions'),
    path('scrape-all/', views.scrape_all_regions, name='scrape_all_regions'),
]