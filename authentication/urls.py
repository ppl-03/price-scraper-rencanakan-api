from django.urls import path
from . import views_register, views_login, views_verify
from . import views_forgot

app_name = 'authentication'

urlpatterns = [
    path('register/', views_register.register, name='register'),
    path('login/', views_login.login, name='login'),
    path('logout/', views_login.logout, name='logout'),
    path('token/verify/', views_login.verify_token, name='verify_token'),
    path('verify-email/<str:token>/', views_verify.confirm_email, name='confirm_email'),
    path('password/forgot/', views_forgot.request_password_reset, name='password_forgot'),
    path('password/verify/<str:token>/', views_forgot.verify_reset_token, name='password_verify'),
    path('password/reset/', views_forgot.perform_password_reset, name='password_reset'),
]
