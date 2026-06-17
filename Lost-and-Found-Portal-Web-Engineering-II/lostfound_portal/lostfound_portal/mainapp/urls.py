from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('lost/', views.lost_list, name='lost_list'),
    path('found/', views.found_list, name='found_list'),
    path('post-lost/', views.post_lost, name='post_lost'),
    path('post-found/', views.post_found, name='post_found'),
    path('item/<str:type>/<int:id>/', views.item_detail, name='item_detail'),
    path('<str:type>/<int:id>/delete/', views.delete_item, name='delete_item'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('update-status/<int:id>/', views.update_status, name='update_status'),
]
