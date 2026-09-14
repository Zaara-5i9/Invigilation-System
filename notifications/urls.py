from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='notification_list'),
    path('<int:pk>/read/', views.mark_as_read, name='mark_as_read'),
    path('mark-all-read/', views.mark_all_as_read, name='mark_all_as_read'),
    path('<int:pk>/delete/', views.delete_notification, name='delete_notification'),
    path('preferences/', views.notification_preferences, name='notification_preferences'),
    path('api/unread-count/', views.get_unread_count, name='get_unread_count'),
    path('api/recent/', views.get_recent_notifications, name='get_recent_notifications'),
]
