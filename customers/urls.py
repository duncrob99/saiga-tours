from django.urls import path, include
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path('password_reset/', auth_views.PasswordResetView.as_view(
            html_email_template_name='registration/password_reset_email.html',
        ), name='password_reset'),
    path('', include('django.contrib.auth.urls')),
    path('register/', views.register, name='register'),
    path('activate/<uuid:uuid>/<uuid:token>/', views.activate, name='activate'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('form/<str:pk>', views.view_form, name='view_form'),
    path('completed_form/<str:user_pk>/<str:task_pk>/', views.view_filled_form, name='view_filled_form'),
    path('new_password/<uuid:uuid>/<uuid:token>/', views.set_new_password, name='new_password'),
    path('send_registration_email/<uuid:uuid>/', views.send_registration_email, name='send_registration_email'),
    path('confirm_email/', views.confirm_email, name='confirm_email'),
    path('media/form_files/<uuid:user_id>/<uuid:form_id>/<str:filename>', views.form_file, name='form_file'),
    path('form_pdf/<str:pk>', views.view_form_pdf, name='view_form_pdf'),
]
