"""
URL configuration for price_scraper_rencanakan_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from db_pricing import views as db_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api/gemilang/', include('api.gemilang.urls')),
    path('api/juragan_material/', include('api.juragan_material.urls')),
    path('api/depobangunan/', include('api.depobangunan.urls')),
    path('api/mitra10/', include('api.mitra10.urls')),
    path('api/db-status/', db_views.check_database_status, name='check_database_status'),
    path("", include("dashboard.urls")),
]
