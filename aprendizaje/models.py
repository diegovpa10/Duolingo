from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.timezone import now
from datetime import date, timedelta

# --- 1. SISTEMA DE USUARIOS ---
# La clase usuario creada a mano fue eliminado para usar la predefinida de Django

class Estudiante(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    racha_dias = models.IntegerField(default=0)
    xp_total = models.BigIntegerField(default=0)
    fecha_ultima_leccion = models.DateField(null=True, blank=True)
    fecha_ultima_recarga = models.DateTimeField(default=timezone.now, null=True, blank=True)
    energia = models.IntegerField(default=10) 
    racha_ejercicios = models.IntegerField(default=0)
    avatar = models.ImageField(upload_to='avatares/', default='avatares/default_owl.png', null=True, blank=True)
    escuela = models.CharField(max_length=200, blank=True, null=True)
    protectores_racha = models.IntegerField(default=0)

    def __str__(self):
        return f"Estudiante: {self.usuario.username}"
    
    def verificar_y_limpiar_racha(self):
        """
        Comprueba si el estudiante dejó pasar más de un día sin completar lecciones.
        Si es así, la racha se rompe y vuelve a 0.
        Se debe ejecutar cada vez que el estudiante entra a su panel principal.
        """
        hoy = date.today()
        if self.fecha_ultima_leccion:
            diferencia = hoy - self.fecha_ultima_leccion
            # Si ha pasado más de 1 día completo desde su última lección (ej: hoy es miércoles y su última lección fue el lunes)
            if diferencia.days > 1:
                self.racha_dias = 0
                self.save()

    def extender_racha(self):
        """
        Suma un día a la racha o la mantiene si ya hizo un ejercicio hoy.
        Se ejecuta SOLO cuando completa un ejercicio NUEVO.
        """
        hoy = date.today()
        ayer = hoy - timedelta(days=1)

        if self.fecha_ultima_leccion == hoy:
            # Ya hizo un ejercicio hoy, la racha se mantiene igual (no se suma doble)
            pass
        elif self.fecha_ultima_leccion == ayer:
            # Su última lección fue ayer, ¡mantiene la continuidad! Suma 1 día
            self.racha_dias += 1
            self.fecha_ultima_leccion = hoy
        else:
            # No tenía racha activa o se había roto. Inicia una racha nueva de 1 día
            self.racha_dias = 1
            self.fecha_ultima_leccion = hoy
        
        self.save()

    # 🛡️ SISTEMA DE LIGAS DINÁMICO
    @property
    def obtener_liga_info(self):
        """Retorna un diccionario con el nombre, emoji y color hexadecimal de su liga actual."""
        xp = self.xp_total
        if xp <= 500:
            return {
                "nombre": "Liga de Bronce",
                "emoji": "🟤",
                "color": "#cd7f32",
                "siguiente_liga": "Plata",
                "xp_necesaria": 501 - xp
            }
        elif xp <= 1500:
            return {
                "nombre": "Liga de Plata",
                "emoji": "⚪",
                "color": "#c0c0c0",
                "siguiente_liga": "Oro",
                "xp_necesaria": 1501 - xp
            }
        elif xp <= 3500:
            return {
                "nombre": "Liga de Oro",
                "emoji": "🟡",
                "color": "#ffaa00",
                "siguiente_liga": "Diamante",
                "xp_necesaria": 3501 - xp
            }
        else:
            return {
                "nombre": "Liga Diamante",
                "emoji": "💎",
                "color": "#00e5ff",
                "siguiente_liga": "Máximo Rango alcanzado",
                "xp_necesaria": 0
            }

class Reclutador(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    empresa = models.CharField(max_length=200)
    contacto = models.CharField(max_length=200, blank=True, null=True, help_text="Correo electrónico o URL de LinkedIn")

    def __str__(self):
        return f"Reclutador: {self.empresa} ({self.usuario.username})"

# --- 2. EMPLEABILIDAD ---

class PerfilProfesional(models.Model):
    estudiante = models.OneToOneField(Estudiante, on_delete=models.CASCADE)
    biografia = models.TextField(blank=True, null=True)
    url_github = models.URLField(max_length=500, blank=True, null=True)
    url_linkedin = models.URLField(max_length=500, blank=True, null=True)
    disponible = models.BooleanField(default=False)
    habilidades = models.JSONField(blank=True, null=True) 

    def __str__(self):
        return f"Perfil de {self.estudiante.usuario.email}"

class OfertaLaboral(models.Model):
    reclutador = models.ForeignKey(Reclutador, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)
    
    # --- DIVISIÓN DE REQUISITOS ---
    requisitos_obligatorios = models.TextField(null=True, blank=True, help_text="Máximo 2 o 3 habilidades clave (Ej. Python, Django).")
    requisitos_extras = models.TextField(null=True, blank=True, help_text="Habilidades deseables que suman puntos (Ej. Docker, SQL).")
    # ------------------------------
    
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
    # ❌ Borramos: completada = models.BooleanField(default=False)

    class Meta:
        unique_together = ('curso', 'orden')

    def __str__(self):
        return f"{self.orden}. {self.titulo} ({self.curso.nombre})"
    
    # 👇 NUEVA LÓGICA: Ahora evalúa por estudiante
    def esta_bloqueada_para(self, estudiante):
        # La lección 1 nunca está bloqueada
        if self.orden == 1:
            return False
            
        # Buscamos la lección anterior
        leccion_anterior = Leccion.objects.filter(curso=self.curso, orden=self.orden - 1).first()
        
        if leccion_anterior:
            # Buscamos si el estudiante actual completó esa lección anterior
            progreso = ProgresoLeccion.objects.filter(estudiante=estudiante, leccion=leccion_anterior).first()
            if progreso and progreso.completada:
                return False # Si completó la anterior, esta NO está bloqueada
                
        return True # En cualquier otro caso, está bloqueada
    
class ProgresoLeccion(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    leccion = models.ForeignKey(Leccion, on_delete=models.CASCADE)
    completada = models.BooleanField(default=False)
    fecha_completado = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Asegura que un estudiante no pueda tener dos registros de la misma lección
        unique_together = ('estudiante', 'leccion') 

    def __str__(self):
        estado = "Completada" if self.completada else "Pendiente"
        return f"{self.estudiante.usuario.username} - {self.leccion.titulo}: {estado}"

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

class RetoInteractivo(models.Model):
    TIPOS_RETO = [
        ('OM', 'Opción Múltiple'),
        ('RH', 'Rellenar Huecos (Tecleo)'),
        ('OT', 'Ordenar Texto (Drag & Drop)'),
        ('EP', 'Enlazar Palabras (Match)'),
    ]
    ejercicio = models.OneToOneField(Ejercicio, on_delete=models.CASCADE, primary_key=True)
    tipo_reto = models.CharField(max_length=2, choices=TIPOS_RETO, default='OM')
    
    # Aquí guardaremos toda la magia en formato JSON dependiendo del tipo_reto
    configuracion = models.JSONField(help_text="Estructura del reto (opciones, respuestas, pares, etc.)")

    def __str__(self):
        return f"Reto {self.get_tipo_reto_display()} - Ejercicio {self.ejercicio.id}"

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
    
class Amistad(models.Model):
    # El usuario que envía o tiene al amigo
    usuario = models.ForeignKey(User, related_name='mis_amigos', on_delete=models.CASCADE)
    # El usuario que fue agregado
    amigo = models.ForeignKey(User, related_name='amigo_de', on_delete=models.CASCADE)
    # Cuándo se hicieron amigos
    fecha_conexion = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Esto evita que un usuario agregue a la misma persona dos veces
        unique_together = ('usuario', 'amigo')

    def __str__(self):
        return f"{self.usuario.username} es amigo de {self.amigo.username}"
    
# Asegúrate de tener importado User arriba si no lo tienes: from django.contrib.auth.models import User

class Notificacion(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    mensaje = models.CharField(max_length=255)
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notificación para {self.usuario.username}: {self.mensaje}"
    
class Novedad(models.Model):
    titulo = models.CharField(max_length=150, verbose_name="Título de la Novedad")
    contenido = models.TextField(verbose_name="Contenido / Cuerpo del mensaje")
    fecha_publicacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Publicación")
    activo = models.BooleanField(default=True, verbose_name="¿Mostrar en el sistema?")

    class Meta:
        verbose_name = "Novedad"
        verbose_name_plural = "Novedades"
        ordering = ['-fecha_publicacion'] # Las más nuevas primero

    def __str__(self):
        return self.titulo
    
class DesafioDiario(models.Model):
    TIPO_OPCIONES = [
        ('xp', 'Recolectar XP'),
        ('lecciones', 'Completar Lecciones'),
        ('racha', 'Mantener Conexión (Racha)'),
    ]
    
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_OPCIONES)
    meta = models.IntegerField(help_text="Cantidad a alcanzar (Ej: 50 para XP, 2 para lecciones)")
    xp_recompensa = models.IntegerField(help_text="XP extra al completar el desafío")
    icono = models.CharField(max_length=10, default="⚡")
    color_barra = models.CharField(max_length=20, default="bar-gold", help_text="Clase CSS: bar-gold, bar-red, bar-blue")
    
    def __str__(self):
        return f"{self.nombre} ({self.meta} {self.tipo})"


class ProgresoDesafio(models.Model):
    estudiante = models.ForeignKey('Estudiante', on_delete=models.CASCADE, related_name='desafios_diarios')
    desafio = models.ForeignKey(DesafioDiario, on_delete=models.CASCADE)
    fecha = models.DateField(default=now)
    progreso_actual = models.IntegerField(default=0)
    completado = models.BooleanField(default=False)
    recompensa_reclamada = models.BooleanField(default=False)

    class Meta:
        # Asegura que un estudiante solo tenga un registro por desafío al día
        unique_together = ('estudiante', 'desafio', 'fecha')

    @property
    def porcentaje(self):
        if self.desafio.meta == 0:
            return 0
        calculo = int((self.progreso_actual / self.desafio.meta) * 100)
        return min(calculo, 100) # Nunca superar el 100%

    def __str__(self):
        return f"{self.estudiante.usuario.username} - {self.desafio.nombre} - {self.fecha}"
    
class CofreAbierto(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='cofres_abiertos')
    # Usaremos la lección justo anterior para identificar el cofre de esa posición
    leccion_previa = models.ForeignKey('Leccion', on_delete=models.CASCADE)
    fecha_apertura = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('estudiante', 'leccion_previa') # Un estudiante solo abre un cofre por hito una vez