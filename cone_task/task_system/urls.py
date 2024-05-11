from django.urls import path
from . import views


urlpatterns = [
    path('get/<str:exchange>/<str:queue>/<str:routing_key>/', views.TaskAPI.get, name='task-get'),
    path('put/<str:exchange>/<str:queue>/<str:routing_key>/', views.TaskAPI.put, name='task-put'),
]
