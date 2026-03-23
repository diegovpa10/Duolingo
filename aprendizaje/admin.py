from django.contrib import admin
# Importamos todos los modelos que creamos en models.py
from .models import (Estudiante, Reclutador, PerfilProfesional, 
                     OfertaLaboral, Postulacion, Curso, Leccion, Ejercicio, 
                     RetoCodigo, QuizIngles, ProgresoCurso, LigaSemanal, 
                     RankingSemanal, DiscusionForo, RespuestaForo,)

# Registramos cada modelo para que aparezca en el panel de administrador
admin.site.register(Estudiante)
admin.site.register(Reclutador)
admin.site.register(PerfilProfesional)
admin.site.register(OfertaLaboral)
admin.site.register(Postulacion)
admin.site.register(Curso)
admin.site.register(Leccion)
admin.site.register(Ejercicio)
admin.site.register(RetoCodigo)
admin.site.register(QuizIngles)
admin.site.register(ProgresoCurso)
admin.site.register(LigaSemanal)
admin.site.register(RankingSemanal)
admin.site.register(DiscusionForo)
admin.site.register(RespuestaForo)
