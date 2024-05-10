from django.urls import path
from . import views


urlpatterns = [
    path('get/<str:exchange>/<str:queue>/', views.TaskAPI.get),
]
