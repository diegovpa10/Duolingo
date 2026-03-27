import sys
import io
import json
import subprocess
import tempfile
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import *
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, logout
from django.shortcuts import redirect
from django.contrib.auth.hashers import make_password, check_password
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Curso, Leccion, Ejercicio, Estudiante
from django.utils import timezone
from datetime import timedelta

@login_required(login_url='login')
def lista_cursos(request):
    # Obtenemos todos los cursos
    cursos = Curso.objects.all() 
    return render(request, 'aprendizaje/lista_cursos.html', {'cursos': cursos})

def detalle_curso(request, curso_id):
    # ¡Aquí usamos la herramienta que importamos en la línea 1!
    curso = get_object_or_404(Curso, id=curso_id)  
    # Buscamos las lecciones de este curso específico
    lecciones = Leccion.objects.filter(curso=curso).order_by('orden')
    return render(request, 'aprendizaje/detalle_curso.html', {
        'curso': curso, 
        'lecciones': lecciones
    })

def detalle_leccion(request, leccion_id):
    leccion = get_object_or_404(Leccion, id=leccion_id)
    ejercicios = Ejercicio.objects.filter(leccion=leccion)
    
    # Variables para enviar a la plantilla
    mensaje = None
    es_correcto = False
    codigo_previo = ""

    if request.method == 'POST':
        codigo_recibido = request.POST.get('codigo_alumno', '')
        codigo_previo = codigo_recibido # Guardamos lo que escribió para que no se le borre
        
        # 1. Detectamos el lenguaje basado en el nombre del curso
        nombre_curso = leccion.curso.nombre.lower()
        if 'javascript' in nombre_curso or 'js' in nombre_curso:
            lenguaje = 'javascript'
        elif 'java' in nombre_curso:
            lenguaje = 'java'
        else:
            lenguaje = 'python'
        
        # 2. Extraemos el resultado esperado del JSON
        ejercicio_actual = ejercicios.first()
        expected_output = ""
        
        if ejercicio_actual and hasattr(ejercicio_actual, 'retocodigo'):
            casos_prueba = ejercicio_actual.retocodigo.casos_prueba
            if isinstance(casos_prueba, str):
                try:
                    casos_prueba = json.loads(casos_prueba)
                except json.JSONDecodeError:
                    casos_prueba = {}
            # Sacamos el texto esperado del test_1
            expected_output = casos_prueba.get('test_1', {}).get('expected_output', '').strip()

        salida_texto = ""
        error_texto = ""

        try:
            # =========================================================
            # NUEVO MOTOR DE EJECUCIÓN SEGURO
            # =========================================================
            if lenguaje == 'java':
                # Ejecutamos Java usando un directorio temporal
                with tempfile.TemporaryDirectory() as temp_dir:
                    file_path = os.path.join(temp_dir, 'Main.java')
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(codigo_recibido)
                    
                    # Compilamos el código (javac)
                    compilacion = subprocess.run(
                        ['javac', 'Main.java'],
                        cwd=temp_dir, capture_output=True, text=True, timeout=5
                    )
                    
                    if compilacion.returncode != 0:
                        error_texto = f"Error de sintaxis en Java:\n{compilacion.stderr.strip()}"
                    else:
                        # Ejecutamos el código compilado (java Main)
                        ejecucion = subprocess.run(
                            ['java', 'Main'],
                            cwd=temp_dir, capture_output=True, text=True, timeout=3
                        )
                        salida_texto = ejecucion.stdout.strip()
                        error_texto = ejecucion.stderr.strip()
            elif lenguaje == 'javascript':
                # ¡NUEVO! Ejecutamos JavaScript usando Node.js
                # Node nos permite evaluar código en texto usando "-e" (eval)
                resultado = subprocess.run(
                    ['node', '-e', codigo_recibido],
                    capture_output=True, text=True, timeout=3
                )
                salida_texto = resultado.stdout.strip()
                error_texto = resultado.stderr.strip()
                
            else:
                # Ejecutamos Python de forma segura
                resultado = subprocess.run(
                    ['python', '-c', codigo_recibido],
                    capture_output=True, text=True, timeout=3
                )
                salida_texto = resultado.stdout.strip()
                error_texto = resultado.stderr.strip()

            # =========================================================
            # VALIDACIÓN DE RESULTADOS
            # =========================================================
            if error_texto and not salida_texto:
                # Si hubo un error en el código
                mensaje = f"Ups, encontramos un error:\n{error_texto}"
                es_correcto = False
            else:
                # Comparamos con el JSON de la base de datos
                if expected_output:
                    if salida_texto == expected_output:
                        mensaje = f"¡Perfecto! Tu código imprimió exactamente: {salida_texto}"
                        es_correcto = True
                    else:
                        mensaje = f"Salida incorrecta. Se esperaba '{expected_output}', pero tu código imprimió: '{salida_texto}'"
                        es_correcto = False
                else:
                    # Si no hay JSON configurado, aprobamos si corrió sin errores
                    mensaje = f"¡Tu código corrió sin errores! Resultado: {salida_texto}"
                    es_correcto = True

            # =========================================================
            # SISTEMA DE EXPERIENCIA Y RACHAS 🦉⭐
            # =========================================================
            if es_correcto:
                leccion.completada = True
                leccion.save()
                
                if request.user.is_authenticated:
                    if hasattr(request.user, 'estudiante'):
                        estudiante = request.user.estudiante
                        estudiante.xp_total += 15 
                        
                        hoy = timezone.now().date()
                        ayer = hoy - timedelta(days=1)
                        
                        if estudiante.fecha_ultima_leccion == hoy:
                            pass 
                        elif estudiante.fecha_ultima_leccion == ayer:
                            estudiante.racha_dias += 1
                        else:
                            estudiante.racha_dias = 1
                            
                        estudiante.fecha_ultima_leccion = hoy
                        estudiante.save()
                    else:
                        print(f"El usuario {request.user.username} no es un estudiante válido.")

        except subprocess.TimeoutExpired:
            mensaje = "Tu código tardó demasiado. ¿Tienes un ciclo infinito?"
            es_correcto = False
        except Exception as e:
            mensaje = f"Error del servidor: {str(e)}"
            es_correcto = False

    return render(request, 'aprendizaje/detalle_leccion.html', {
        'leccion': leccion,
        'ejercicios': ejercicios,
        'mensaje': mensaje,
        'es_correcto': es_correcto,
        'codigo_previo': codigo_previo
    })

def registro(request):
    if request.method == 'POST':
        # Volvemos a usar el formulario original de Django
        form = UserCreationForm(request.POST) 
        if form.is_valid():
            # Esto guarda al User de Django (con su contraseña segura)
            user_django = form.save()
            
            # Creamos la mochila del Estudiante conectada a ese User
            # Usamos xp_total=0 porque así se llama en tu modelo
            Estudiante.objects.create(usuario=user_django, xp_total=0, racha_dias=0)
            
            login(request, user_django)
            return redirect('lista_cursos')
    else:
        form = UserCreationForm()
    
    return render(request, 'aprendizaje/registro.html', {'form': form})

def login_usuario(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        try:
            usuario = User.objects.get(username=username)

            # Validamos la contraseña
            if check_password(password, usuario.password):
                
                # Usamos la función oficial de Django para iniciar sesión.
                login(request, usuario)

                # Cambiamos 'home' por 'lista_cursos' que es tu ruta real
                return redirect('lista_cursos')

            else:
                messages.error(request, "la contraseña esta incorrecta carnal :)")

        except User.DoesNotExist:
            messages.error(request, "No esta registrado ve a registrarte :)")

        return redirect('login')

    return render(request, 'aprendizaje/login.html')

# =========================================================
# VISTAS: PERFIL, LIGAS, DESAFÍOS Y LOGOUT
# =========================================================

@login_required(login_url='login')
def perfil(request):
    if request.method == 'POST':
        # Manejamos el botón de cerrar sesión que pusimos en perfil.html
        logout(request)
        return redirect('login')
        
    return render(request, 'aprendizaje/perfil.html')

@login_required(login_url='login')
def ligas(request):
    return render(request, 'aprendizaje/ligas.html')

@login_required(login_url='login')
def desafios(request):
    return render(request, 'aprendizaje/desafios.html')
