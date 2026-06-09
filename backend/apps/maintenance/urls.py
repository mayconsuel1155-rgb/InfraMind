from django.urls import path
from . import views

urlpatterns = [
    path('', views.maintenance_list_view, name='maintenance_list'),
    path('novo/', views.maintenance_create_view, name='maintenance_create'),
    path('<int:pk>/', views.maintenance_detail_view, name='maintenance_detail'),
    path('<int:pk>/editar/', views.maintenance_update_view, name='maintenance_update'),
    path('<int:pk>/imprimir/', views.maintenance_print_view, name='maintenance_print'),
]
