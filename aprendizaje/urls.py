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
    path('empresa/dashboard/', views.dashboard_reclutador, name='dashboard_reclutador'),
    path('empresa/nueva-oferta/', views.crear_oferta, name='crear_oferta'),
    path('redireccion/', views.redireccion_inicio, name='redireccion_inicio'),
    path('misiones-laborales/', views.bolsa_trabajo, name='bolsa_trabajo'),
    path('dev/iniciar-semana/', views.iniciar_semana_prueba, name='iniciar_semana'),
    path('candidato/<int:estudiante_id>/', views.ver_perfil_publico, name='ver_perfil_publico'),
    path('postular/<int:oferta_id>/', views.postular_oferta, name='postular_oferta'),
    path('reclutador/dashboard/', views.dashboard_reclutador, name='dashboard_reclutador'),
    path('reclutador/oferta/<int:oferta_id>/postulantes/', views.ver_postulantes, name='ver_postulantes'),
    path('notificaciones/marcar-leidas/', views.marcar_notificaciones_leidas, name='marcar_notificaciones_leidas'),
]
