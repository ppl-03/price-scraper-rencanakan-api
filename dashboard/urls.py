from django.contrib import admin
from django.urls import path
from dashboard.views import home
from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("scrape/gemilang/", views.trigger_scrape, name="trigger_scrape"),

    # Curated prices (ItemPriceProvince)
    path("prices/", views.curated_price_list, name="curated_price_list"),
    path("prices/new/", views.curated_price_create, name="curated_price_create"),
    path("prices/new/", views.curated_price_create_post, name="curated_price_create_post"),
    path("prices/<int:pk>/edit/", views.curated_price_update, name="curated_price_update"),
    path("prices/<int:pk>/edit/", views.curated_price_update_post, name="curated_price_update_post"),
    path("prices/<int:pk>/delete/", views.curated_price_delete, name="curated_price_delete"),
    path("prices/<int:pk>/delete/", views.curated_price_delete_post, name="curated_price_delete_post"),
    path("prices/new/from-scrape/", views.curated_price_from_scrape, name="curated_price_from_scrape"),
]
