from django.utils import timezone
from datetime import timedelta

def regeneracion_energia(request):
    """Procesador de contexto para recargar energía en cualquier página de la app"""
    if request.user.is_authenticated and hasattr(request.user, 'estudiante'):
        estudiante = request.user.estudiante
        ahora = timezone.now()
        
        if not estudiante.fecha_ultima_recarga:
            estudiante.fecha_ultima_recarga = ahora
            estudiante.save()

        if estudiante.energia < 5:
            tiempo_pasado = ahora - estudiante.fecha_ultima_recarga
            minutos_pasados = tiempo_pasado.total_seconds() / 60
            
            MINUTOS_POR_ENERGIA = 20 
            puntos_recuperados = int(minutos_pasados // MINUTOS_POR_ENERGIA)
            
            if puntos_recuperados > 0:
                nueva_energia = estudiante.energia + puntos_recuperados
                if nueva_energia >= 5:
                    estudiante.energia = 5
                    estudiante.fecha_ultima_recarga = ahora
                else:
                    estudiante.energia = nueva_energia
                    estudiante.fecha_ultima_recarga += timedelta(minutes=puntos_recuperados * MINUTOS_POR_ENERGIA)
                estudiante.save()
        else:
            estudiante.fecha_ultima_recarga = ahora
            estudiante.save()
            
    # No necesitamos retornar variables globales, solo queremos ejecutar la lógica de fondo
    return {}