from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.lista_cursos, name='lista_cursos'),
    path('curso/<int:curso_id>/', views.detalle_curso, name='detalle_curso'),
    path('leccion/<int:leccion_id>/', views.detalle_leccion, name='detalle_leccion'),
    path('registro/', views.registro, name='registro'),
    path('login/', auth_views.LoginView.as_view(template_name='aprendizaje/login.html'), name='login'),
    # Django moderno requiere que el cierre de sesión sea seguro, por eso usamos next_page
    path('logout/', auth_views.LogoutView.as_view(next_page='lista_cursos'), name='logout'),
]