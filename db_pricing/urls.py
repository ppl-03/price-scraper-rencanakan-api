# db_pricing/urls.py
from django.urls import path
from . import views

app_name = 'db_pricing'

urlpatterns = [
    # Database status endpoint
    path('status/', views.check_database_status, name='database_status'),
    
    # Price anomaly endpoints
    path('anomalies/', views.list_price_anomalies, name='list_anomalies'),
    path('anomalies/<int:anomaly_id>/', views.get_price_anomaly, name='get_anomaly'),
    path('anomalies/<int:anomaly_id>/review/', views.review_price_anomaly, name='review_anomaly'),
    path('anomalies/statistics/', views.get_anomaly_statistics, name='anomaly_statistics'),
]
