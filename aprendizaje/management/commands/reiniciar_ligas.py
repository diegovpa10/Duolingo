from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from aprendizaje.models import Estudiante, LigaSemanal, RankingSemanal

class Command(BaseCommand):
    help = 'Cierra las ligas de la semana pasada, calcula podios e inicializa la nueva semana competitiva.'

    def handle(self, *args, **options):
        hoy = timezone.now().date()
        
        # 1. DETERMINAR FECHAS DE LA SEMANA QUE CORRESPONDE
        # Asumiendo que corre el Domingo a la medianoche o Lunes a primera hora:
        fecha_semana_pasada = hoy - timedelta(days=7)
        
        self.stdout.write(self.style.SUCCESS(f"=== INICIANDO PROCESO DE REINICIO DE LIGAS ({hoy}) ==="))

        # =====================================================================
        # FASE 1: PROCESAR Y CERRAR LA SEMANA PASADA
        # =====================================================================
        # Buscamos todos los rankings de la semana que acaba de terminar
        rankings_pasados = RankingSemanal.objects.filter(semana_inicio=fecha_semana_pasada)
        
        if rankings_pasados.exists():
            # Agrupamos por cada liga individual para calcular los puestos de forma independiente
            ligas_afectadas = rankings_pasados.values_list('liga', flat=True).distinct()
            
            for liga_id in ligas_afectadas:
                liga_obj = LigaSemanal.objects.get(id=liga_id)
                # Obtenemos los alumnos de ESTA liga ordenados por quién ganó más XP esa semana
                competidores = rankings_pasados.filter(liga=liga_obj).order_by('-xp_ganada_esta_semana')
                
                self.stdout.write(f"Procesando posiciones para la división: {liga_obj.division}")
                
                for puesto, ranking in enumerate(competidores, start=1):
                    ranking.puesto_actual = puesto
                    ranking.save()
                    
                    # 🎁 RECOMPENSA OPCIONAL: Si quedó en 1er lugar, le regalamos un bono a su XP Total
                    if puesto == 1 and ranking.xp_ganada_esta_semana > 0:
                        estudiante = ranking.estudiante
                        bono = 100  # Puedes ajustar los puntos de recompensa
                        estudiante.xp_total += bono
                        estudiante.save()
                        self.stdout.write(self.style.SUCCESS(f"   ¡{estudiante.usuario.username} ganó la liga! Recompensa de +{bono} XP otorgada."))
        else:
            self.stdout.write(self.style.WARNING("No se encontraron registros de rankings para la semana pasada."))


        # =====================================================================
        # FASE 2: INICIALIZAR LA NUEVA SEMANA COMPETITIVA
        # =====================================================================
        self.stdout.write("Inicializando nuevas divisiones para la próxima semana...")
        
        # Definimos las 4 divisiones que tu propiedad `@property obtener_liga_info` maneja
        nombres_divisiones = ["Liga de Bronce", "Liga de Plata", "Liga de Oro", "Liga de Diamante"]
        nuevas_ligas_dict = {}
        
        # El cierre de la nueva liga será el próximo domingo (6 días a partir de hoy lunes)
        proximo_cierre = hoy + timedelta(days=6)
        
        for nombre in nombres_divisiones:
            liga_nueva, created = LigaSemanal.objects.get_or_create(
                division=nombre,
                fecha_cierre=proximo_cierre
            )
            nuevas_ligas_dict[nombre] = liga_nueva

        # Traemos a todos los estudiantes activos del sistema
        estudiantes = Estudiante.objects.all()
        contador_nuevos_rankings = 0
        
        for estudiante in estudiantes:
            # Tu propiedad mágica calcula automáticamente en qué liga cae según su `xp_total` actual
            info_liga_actual = estudiante.obtener_liga_info
            nombre_liga_estudiante = info_liga_actual["nombre"]
            
            # Obtenemos el objeto de la liga correspondiente para esta nueva semana
            liga_asignada = nuevas_ligas_dict.get(nombre_liga_estudiante)
            
            # Creamos el nuevo contenedor de ranking semanal para el alumno a 0 XP
            if liga_asignada:
                RankingSemanal.objects.get_or_create(
                    estudiante=estudiante,
                    semana_inicio=hoy,
                    defaults={
                        'liga': liga_asignada,
                        'xp_ganada_esta_semana': 0,
                        'puesto_actual': None
                    }
                )
                contador_nuevos_rankings += 1

        self.stdout.write(self.style.SUCCESS(f"=== PROCESO COMPLETADO CORRECOTAMENTE ==="))
        self.stdout.write(self.style.SUCCESS(f"Se crearon/verificaron {contador_nuevos_rankings} rankings para la nueva semana."))