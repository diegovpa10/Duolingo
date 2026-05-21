import subprocess
import tempfile
import os
import json
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

# =========================================================
# NUEVA FUNCIÓN: EVALUADOR DE CÓDIGO EXTERNO
# =========================================================
def evaluar_codigo(nombre_curso, codigo_recibido, expected_output):
    """
    Recibe el código del alumno, lo ejecuta de forma segura en consola
    y devuelve si es correcto y el mensaje para el usuario.
    """
    nombre_curso = nombre_curso.lower()
    if 'javascript' in nombre_curso or 'js' in nombre_curso:
        lenguaje = 'javascript'
    elif 'java' in nombre_curso:
        lenguaje = 'java'
    else:
        lenguaje = 'python'

    salida_texto = ""
    error_texto = ""
    es_correcto = False
    mensaje = ""

    try:
        if lenguaje == 'java':
            with tempfile.TemporaryDirectory() as temp_dir:
                file_path = os.path.join(temp_dir, 'Main.java')
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(codigo_recibido)
                
                compilacion = subprocess.run(['javac', 'Main.java'], cwd=temp_dir, capture_output=True, text=True, timeout=5)
                if compilacion.returncode != 0:
                    error_texto = f"Error de sintaxis en Java:\n{compilacion.stderr.strip()}"
                else:
                    ejecucion = subprocess.run(['java', 'Main'], cwd=temp_dir, capture_output=True, text=True, timeout=3)
                    salida_texto = ejecucion.stdout.strip()
                    error_texto = ejecucion.stderr.strip()
        elif lenguaje == 'javascript':
            resultado = subprocess.run(['node', '-e', codigo_recibido], capture_output=True, text=True, timeout=3)
            salida_texto = resultado.stdout.strip()
            error_texto = resultado.stderr.strip()
        else:
            resultado = subprocess.run(['python', '-c', codigo_recibido], capture_output=True, text=True, timeout=3)
            salida_texto = resultado.stdout.strip()
            error_texto = resultado.stderr.strip()

        if error_texto and not salida_texto:
            mensaje = f"Ups, encontramos un error:\n{error_texto}"
            es_correcto = False
        else:
            if expected_output:
                if salida_texto == expected_output:
                    mensaje = f"¡Perfecto! Tu código imprimió exactamente: {salida_texto}"
                    es_correcto = True
                else:
                    mensaje = f"Salida incorrecta. Se esperaba '{expected_output}', pero tu código imprimió: '{salida_texto}'"
                    es_correcto = False
            else:
                mensaje = f"¡Tu código corrió sin errores! Resultado: {salida_texto}"
                es_correcto = True

    except subprocess.TimeoutExpired:
        mensaje = "Tu código tardó demasiado. ¿Tienes un ciclo infinito?"
        es_correcto = False
    except Exception as e:
        mensaje = f"Error del servidor: {str(e)}"
        es_correcto = False

    return es_correcto, mensaje

# =========================================================
# NUEVA FUNCIÓN: EVALUADOR DE RETOS INTERACTIVOS
# =========================================================
def evaluar_reto_interactivo(tipo_reto, respuesta_alumno, config):
    """
    Evalúa la respuesta de los retos interactivos (quiz, ordenar, emparejar, etc.)
    y devuelve si es correcta y el mensaje correspondiente.
    """
    es_correcto = False
    mensaje = ""
    
    try:
        if tipo_reto == 'OM':
            if respuesta_alumno and int(respuesta_alumno) == int(config.get('indice_correcto', -1)):
                mensaje = "¡Excelente! Respuesta correcta. 🔮"
                es_correcto = True
            else:
                mensaje = "❌ Respuesta incorrecta. Vuelve a intentarlo."

        elif tipo_reto == 'RH':
            respuesta_esperada = config.get('respuesta_correcta', '').strip()
            if respuesta_alumno.lower() == respuesta_esperada.lower():
                mensaje = "¡Excelente! Has completado el espacio correctamente. 🔮"
                es_correcto = True
            else:
                mensaje = "❌ Respuesta incorrecta. El texto no coincide."

        elif tipo_reto == 'OT':
            try:
                lista_alumno = json.loads(respuesta_alumno) if respuesta_alumno else []
            except json.JSONDecodeError:
                lista_alumno = []
            lista_esperada = config.get('orden_correcto', [])
            
            if lista_alumno == lista_esperada:
                mensaje = "¡Perfecto! El orden es totalmente correcto. 🔮"
                es_correcto = True
            else:
                if len(lista_alumno) < len(lista_esperada):
                    mensaje = "⚠️ Parece que olvidaste arrastrar algunos bloques. ¡Inténtalo de nuevo!"
                else:
                    mensaje = "❌ El orden no es el correcto. Revisa la lógica paso a paso."

        elif tipo_reto == 'EP':
            try:
                dict_alumno = json.loads(respuesta_alumno) if respuesta_alumno else {}
            except json.JSONDecodeError:
                dict_alumno = {}
                
            dict_esperado = config.get('parejas', {})
            
            if dict_alumno == dict_esperado:
                mensaje = "¡Espléndido! Has enlazado todos los conceptos con su definición correcta. 🔮"
                es_correcto = True
            else:
                if len(dict_alumno) < len(dict_esperado):
                    mensaje = "⚠️ Faltan conceptos por enlazar en la matriz de juego."
                else:
                    mensaje = "❌ Algunos enlaces no son correctos. Haz clic en los bloques morados para romper el enlace e intentar de nuevo."

    except Exception as e:
        mensaje = f"⚠️ Error al procesar los datos del reto: {str(e)}"
        
    return es_correcto, mensaje