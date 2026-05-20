from .models import ProgresoDesafio
from django.utils import timezone
from django.utils.timezone import now

def registrar_avance_misiones(estudiante, tipo_mision, cantidad_a_sumar):
    hoy = timezone.now().date()
    
    # 🔴 PRINT 1: Avisa que la función sí fue llamada
    print(f"\n[DEBUG MISIONES] Ejecutando disparador para tipo '{tipo_mision}'. Cantidad: {cantidad_a_sumar}")
    
    misiones_activas = ProgresoDesafio.objects.filter(
        estudiante=estudiante,
        fecha=hoy,
        desafio__tipo=tipo_mision,
        completado=False
    )
    
    # 🔴 PRINT 2: Avisa cuántas misiones encontró
    print(f"[DEBUG MISIONES] Se encontraron {misiones_activas.count()} misiones activas hoy para este tipo.")
    
    for progreso in misiones_activas:
        progreso.progreso_actual += cantidad_a_sumar
        # 🔴 PRINT 3: Avisa que está sumando el progreso
        print(f"[DEBUG MISIONES] Sumando progreso a: {progreso.desafio.nombre}. Total actual: {progreso.progreso_actual}")
        
        if progreso.progreso_actual >= progreso.desafio.meta:
            progreso.progreso_actual = progreso.desafio.meta
            progreso.completado = True
            estudiante.xp_total += progreso.desafio.xp_recompensa
            estudiante.save()
                
        progreso.save()