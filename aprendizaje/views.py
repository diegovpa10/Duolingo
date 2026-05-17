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
from .models import Curso, Leccion, Ejercicio, Estudiante, Reclutador, PerfilProfesional, Amistad
from .forms import RegistroRedOwlForm, EditarEstudianteForm, EditarPerfilProfesionalForm
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.forms import AuthenticationForm

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
                # 1. Verificamos que la lección NO se haya completado antes para evitar trampas de XP infinita
                if not leccion.completada:
                    
                    if request.user.is_authenticated:
                        if hasattr(request.user, 'estudiante'):
                            estudiante = request.user.estudiante
                            
                            # 2. Obtenemos la XP dinámica del ejercicio (o 15 por defecto si algo falla)
                            puntos_a_ganar = ejercicio_actual.xp_recompensa if ejercicio_actual else 15
                            estudiante.xp_total += puntos_a_ganar 
                            
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
                            
                            # Opcional: Mandarle un mensaje de felicitación por los puntos
                            mensaje += f" ¡Ganaste {puntos_a_ganar} XP!"
                            
                    # 3. Solo hasta que dimos los puntos, marcamos la lección como completada
                    leccion.completada = True
                    leccion.save()

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
        # Usamos nuestro formulario personalizado
        form = RegistroRedOwlForm(request.POST) 
        
        if form.is_valid():
            # 1. Guardamos al User base (email, pass, etc)
            user_django = form.save()
            
            # 2. Averiguamos qué eligió en los Radio Buttons
            tipo = form.cleaned_data.get('tipo_usuario')
            
            # 3. Ramificación de la lógica
            if tipo == 'estudiante':
                # Creamos su mochila de Estudiante y su Perfil Profesional vacío
                nombre_escuela = form.cleaned_data.get('escuela') or "Sin escuela"
                estudiante = Estudiante.objects.create(usuario=user_django, xp_total=0, racha_dias=0, escuela=nombre_escuela)
                PerfilProfesional.objects.create(estudiante=estudiante)
                
            elif tipo == 'reclutador':
                # Si es reclutador, sacamos el nombre de la empresa (o le damos uno por defecto)
                nombre_empresa = form.cleaned_data.get('empresa') or "Independiente"
                Reclutador.objects.create(usuario=user_django, empresa=nombre_empresa)
            
            # 4. Iniciar sesión automáticamente y redirigir
            login(request, user_django)
            return redirect('lista_cursos')
    else:
        # Si entra por primera vez a la página, mostramos el formulario vacío
        form = RegistroRedOwlForm()
    
    return render(request, 'aprendizaje/registro.html', {'form': form})

@login_required
def perfil(request):
    user = request.user
    
    # Verificamos qué tipo de usuario es para saber qué renderizar
    es_estudiante = hasattr(user, 'estudiante')
    
    if es_estudiante:
        estudiante = user.estudiante
        # Obtenemos o creamos su perfil profesional por si acaso
        perfil_prof, created = PerfilProfesional.objects.get_or_create(estudiante=estudiante)
        
        if request.method == 'POST':
            # ¡ATENCIÓN! request.FILES es obligatorio para que se guarden las imágenes
            form_estudiante = EditarEstudianteForm(request.POST, request.FILES, instance=estudiante)
            form_perfil = EditarPerfilProfesionalForm(request.POST, instance=perfil_prof)
            
            if form_estudiante.is_valid() and form_perfil.is_valid():
                form_estudiante.save()
                form_perfil.save()
                return redirect('perfil')
        else:
            form_estudiante = EditarEstudianteForm(instance=estudiante)
            form_perfil = EditarPerfilProfesionalForm(instance=perfil_prof)
            
        context = {
            'es_estudiante': True,
            'estudiante': estudiante,
            'perfil_prof': perfil_prof,
            'form_estudiante': form_estudiante,
            'form_perfil': form_perfil,
        }
    else:
        # Lógica para cuando entra un Reclutador
        reclutador = user.reclutador
        context = {
            'es_estudiante': False,
            'reclutador': reclutador,
        }
        
    return render(request, 'aprendizaje/perfil.html', context)

# =========================================================
# VISTAS: AMISTAD, LIGAS, DESAFÍOS, LOGIN Y LOGOUT
# =========================================================

@login_required(login_url='login')
def red_amigos(request):
    usuario_actual = request.user
    mensaje = None
    
    if request.method == 'POST':
        # Descubrimos qué botón presionó el usuario
        accion = request.POST.get('accion')
        
        # 1. LÓGICA PARA AGREGAR
        if accion == 'vincular':
            nombre_buscar = request.POST.get('buscar_usuario')
            if nombre_buscar:
                try:
                    usuario_encontrado = User.objects.get(username=nombre_buscar)
                    if usuario_encontrado == usuario_actual:
                        mensaje = "No puedes agregarte a ti mismo como amigo."
                    else:
                        Amistad.objects.get_or_create(usuario=usuario_actual, amigo=usuario_encontrado)
                        mensaje = f"¡Has conectado con {usuario_encontrado.username} exitosamente!"
                except User.DoesNotExist:
                    mensaje = "No se encontró a ningún operador con ese código/nombre."
                    
        # 2. LÓGICA PARA ELIMINAR
        elif accion == 'eliminar':
            amigo_id = request.POST.get('amigo_id')
            # Buscamos la conexión específica y la destruimos
            Amistad.objects.filter(usuario=usuario_actual, amigo__id=amigo_id).delete()
            mensaje = "> ENLACE DESTRUIDO."

    # OBTENER LA LISTA DE AMIGOS ACTUALES
    conexiones = Amistad.objects.filter(usuario=usuario_actual)
    
    return render(request, 'aprendizaje/amigos.html', {
        'conexiones': conexiones,
        'mensaje': mensaje
    })

@login_required(login_url='login')
def ligas(request):
    return render(request, 'aprendizaje/ligas.html')

@login_required(login_url='login')
def desafios(request):
    return render(request, 'aprendizaje/desafios.html')

def login_usuario(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            usuario = form.get_user()
            login(request, usuario)
            return redirect('perfil')
    else:
        form = AuthenticationForm()
        
    return render(request, 'aprendizaje/login.html', {'form': form})