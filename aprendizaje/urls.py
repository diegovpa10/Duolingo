from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import *

urlpatterns = [
    path('', views.lista_cursos, name='lista_cursos'),
    path('curso/<int:curso_id>/', views.detalle_curso, name='detalle_curso'),
    path('leccion/<int:leccion_id>/', views.detalle_leccion, name='detalle_leccion'),
    path('registro/', views.registro, name='registro'),
    path('login/', views.login_usuario, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('perfil/', views.perfil, name='perfil'),
    path('ligas/', views.ligas, name='ligas'),
    path('desafios/', views.desafios, name='desafios'),
    path('red/', views.red_amigos, name='red_amigos'),
]
