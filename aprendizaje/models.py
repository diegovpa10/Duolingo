from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User

# --- 1. SISTEMA DE USUARIOS ---

# La clase usuario creada a mano fue eliminado para usar la predefinida de Django

class Estudiante(models.Model):
    # ¡AQUÍ ESTÁ EL CAMBIO MÁGICO! Cambiamos 'Usuario' por 'User'
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    racha_dias = models.IntegerField(default=0)
    xp_total = models.BigIntegerField(default=0)
    fecha_ultima_leccion = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Estudiante: {self.usuario.username}"

class Reclutador(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    empresa = models.CharField(max_length=200)

    def __str__(self):
        return f"Reclutador: {self.empresa} ({self.usuario.username})"

# --- 2. EMPLEABILIDAD ---

class PerfilProfesional(models.Model):
    estudiante = models.OneToOneField(Estudiante, on_delete=models.CASCADE)
    biografia = models.TextField(blank=True, null=True)
    url_github = models.URLField(max_length=500, blank=True, null=True)
    url_linkedin = models.URLField(max_length=500, blank=True, null=True)
    disponible = models.BooleanField(default=False)
    # Django tiene un campo especial para JSON, ¡es perfecto para tu diseño!
    habilidades = models.JSONField(blank=True, null=True) 

    def __str__(self):
        return f"Perfil de {self.estudiante.usuario.email}"

class OfertaLaboral(models.Model):
    reclutador = models.ForeignKey(Reclutador, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    rango_salarial = models.CharField(max_length=100, blank=True, null=True)
    fecha_publicacion = models.DateField(auto_now_add=True)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return self.titulo

class Postulacion(models.Model):
    ESTADOS = [('Enviada', 'Enviada'), ('En Revisión', 'En Revisión'), ('Aceptada', 'Aceptada'), ('Rechazada', 'Rechazada')]
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    oferta = models.ForeignKey(OfertaLaboral, on_delete=models.CASCADE)
    fecha_postulacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=30, choices=ESTADOS, default='Enviada')

    class Meta:
        unique_together = ('estudiante', 'oferta') # Primary key compuesta

# --- 3. RUTAS DE APRENDIZAJE ---

class Curso(models.Model):
    nombre = models.CharField(max_length=200)
    lenguaje = models.CharField(max_length=100)
    es_ingles_tecnico = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre

class Leccion(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    orden = models.PositiveIntegerField()
    titulo = models.CharField(max_length=200)
    completada = models.BooleanField(default=False)

    class Meta:
        unique_together = ('curso', 'orden')

    def __str__(self):
        return f"{self.orden}. {self.titulo} ({self.curso.nombre})"

class Ejercicio(models.Model):
    TIPOS = [('C', 'Código'), ('Q', 'Quiz')]
    leccion = models.ForeignKey(Leccion, on_delete=models.CASCADE)
    tipo_ejercicio = models.CharField(max_length=1, choices=TIPOS)
    enunciado = models.TextField()
    xp_recompensa = models.PositiveIntegerField()

    def __str__(self):
        return f"Ejercicio {self.id} - {self.get_tipo_ejercicio_display()}"

class RetoCodigo(models.Model):
    ejercicio = models.OneToOneField(Ejercicio, on_delete=models.CASCADE, primary_key=True)
    codigo_base = models.TextField()
    casos_prueba = models.JSONField()
    tiempo_limite = models.FloatField()

class QuizIngles(models.Model):
    ejercicio = models.OneToOneField(Ejercicio, on_delete=models.CASCADE, primary_key=True)
    url_audio = models.URLField(max_length=500, blank=True, null=True)
    opciones = models.JSONField()
    respuesta_correcta = models.PositiveIntegerField()

class ProgresoCurso(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    porcentaje_completado = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    nivel_alcanzado = models.PositiveIntegerField(default=0)
    ultimo_acceso = models.DateField(auto_now=True)

    class Meta:
        unique_together = ('estudiante', 'curso')

# --- 4. GAMIFICACIÓN Y FORO ---

class LigaSemanal(models.Model):
    division = models.CharField(max_length=50)
    fecha_cierre = models.DateField()

    def __str__(self):
        return self.division

class RankingSemanal(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    liga = models.ForeignKey(LigaSemanal, on_delete=models.CASCADE)
    semana_inicio = models.DateField()
    xp_ganada_esta_semana = models.PositiveIntegerField(default=0)
    puesto_actual = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        unique_together = ('estudiante', 'semana_inicio')

class DiscusionForo(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    es_duda_tecnica = models.BooleanField(default=False)
    votos = models.IntegerField(default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    # Se usa 'self' en cadena porque RespuestaForo aún no está definida en el código
    solucion_respuesta = models.OneToOneField('RespuestaForo', on_delete=models.SET_NULL, null=True, blank=True, related_name='discusion_solucionada')

    def __str__(self):
        return self.titulo

class RespuestaForo(models.Model):
    discusion = models.ForeignKey(DiscusionForo, on_delete=models.CASCADE, related_name='respuestas')
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    contenido = models.TextField()
    fecha_respuesta = models.DateTimeField(auto_now_add=True)
    votos = models.IntegerField(default=0)

    def __str__(self):
        return f"Respuesta de {self.estudiante.usuario.email}"

class Perfil(models.Model):
    # OneToOneField significa que cada Usuario tendrá exactamente UN Perfil (una mochila)
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Aquí guardaremos los puntos. Empezarán en 0.
    xp_total = models.IntegerField(default=0)

    def __str__(self):
        return f"Perfil de {self.usuario.username} - {self.xp_total} XP"