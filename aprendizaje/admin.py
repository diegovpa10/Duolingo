from django.contrib import admin
# Importamos todos los modelos que creamos en models.py
from .models import (Estudiante, Reclutador, PerfilProfesional, 
                     OfertaLaboral, Postulacion, Curso, Leccion, Ejercicio, 
                     RetoCodigo, RetoInteractivo, ProgresoCurso, LigaSemanal, 
                     RankingSemanal, DiscusionForo, RespuestaForo, Novedad, DesafioDiario, ProgresoDesafio)

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
admin.site.register(RetoInteractivo)
admin.site.register(ProgresoCurso)
admin.site.register(LigaSemanal)
admin.site.register(RankingSemanal)
admin.site.register(DiscusionForo)
admin.site.register(RespuestaForo)
@admin.register(Novedad)
class NovedadAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'fecha_publicacion', 'activo')
    list_filter = ('activo', 'fecha_publicacion')
    search_fields = ('titulo', 'contenido')
@admin.register(DesafioDiario)
class DesafioDiarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'meta', 'xp_recompensa', 'icono', 'color_barra')
    list_filter = ('tipo',)
    search_fields = ('nombre', 'descripcion')
    list_editable = ('meta', 'xp_recompensa', 'icono') # Permite editar esto rápido desde la lista

@admin.register(ProgresoDesafio)
class ProgresoDesafioAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'desafio', 'fecha', 'progreso_actual', 'completado')
    list_filter = ('fecha', 'completado', 'desafio')
    search_fields = ('estudiante__usuario__username', 'desafio__nombre')
    readonly_fields = ('fecha',) # Para evitar cambiar fechas por accidente