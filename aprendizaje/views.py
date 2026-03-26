import sys
import io
from django.contrib.auth import get_user_model
from django.contrib.auth.models import *
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.shortcuts import redirect
from django.contrib.auth.hashers import make_password, check_password
from django.shortcuts import render, get_object_or_404
from .models import Curso, Leccion, Ejercicio, Estudiante
from django.utils import timezone
from datetime import timedelta

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

    if leccion.orden > 1:
        # Buscamos la lección inmediatamente anterior del mismo curso
        leccion_anterior = Leccion.objects.filter(curso=leccion.curso, orden=leccion.orden - 1).first()
        
        # Si la lección anterior existe pero NO está completada... ¡Lo regresamos!
        if leccion_anterior and not leccion_anterior.completada:
            # Le mandamos un mensaje de advertencia
            messages.warning(request, "¡Tranquilo, pequeño búho! 🦉 Debes completar la lección anterior primero.")
            
            # Lo redirigimos de vuelta a la ruta del curso (Ajusta 'detalle_curso' si tu URL se llama distinto)
            # Nota: Necesitas pasarle el ID del curso para que sepa a dónde regresar
            return redirect('detalle_curso', curso_id=leccion.curso.id)
    
    # Variables para enviar a la plantilla
    mensaje = None
    es_correcto = False
    codigo_previo = ""

    if request.method == 'POST':
        codigo_recibido = request.POST.get('codigo_alumno')
        codigo_previo = codigo_recibido # Guardamos lo que escribió para que no se le borre
        
        # Preparamos una "trampa" para capturar lo que el código imprima
        salida_capturada = io.StringIO()
        salida_original = sys.stdout
        sys.stdout = salida_capturada
        
        try:
            # ¡Aquí ocurre la magia! Ejecutamos el texto como si fuera código Python
            exec(codigo_recibido)
            
            # Si Python pasa la línea anterior sin explotar, significa que no hubo errores de sintaxis
            salida_texto = salida_capturada.getvalue()
            
            # Puedes personalizar este mensaje
            mensaje = f"¡Excelente! Tu código funcionó sin errores. Resultado impreso: {salida_texto}"
            es_correcto = True

            leccion.completada = True
            leccion.save()
            # =========================================================
            # ¡NUEVO: AQUÍ LE DAMOS LA EXPERIENCIA AL ESTUDIANTE! 🦉⭐
            # =========================================================
            if request.user.is_authenticated:
                if hasattr(request.user, 'estudiante'):
                    estudiante = request.user.estudiante
                    
                    # 1. Le sumamos los 15 puntos de XP
                    estudiante.xp_total += 15 
                    
                    # 2. Calculamos la racha de días
                    hoy = timezone.now().date()
                    ayer = hoy - timedelta(days=1)
                    
                    if estudiante.fecha_ultima_leccion == hoy:
                        # Si ya había practicado hoy, la racha se mantiene igual (no suma doble)
                        pass 
                    elif estudiante.fecha_ultima_leccion == ayer:
                        # Si practicó ayer, ¡excelente! La racha sube en 1
                        estudiante.racha_dias += 1
                    else:
                        # Si pasaron más días (perdió la racha) o es su primera lección, empieza en 1
                        estudiante.racha_dias = 1
                        
                    # 3. Actualizamos la fecha a HOY para que mañana pueda volver a sumar
                    estudiante.fecha_ultima_leccion = hoy
                    
                    # Guardamos la mochila actualizada
                    estudiante.save()
                else:
                    print(f"El usuario {request.user.username} no es un estudiante válido.")
            # =========================================================
            
        except Exception as e:
            # Si el código del alumno tiene un error, entramos aquí
            mensaje = f"Ups, encontramos un error: {e}"
            es_correcto = False
            
        finally:
            # MUY IMPORTANTE: Devolvemos la salida a la normalidad
            sys.stdout = salida_original

    return render(request, 'aprendizaje/detalle_leccion.html', {
        'leccion': leccion,
        'ejercicios': ejercicios,
        'mensaje': mensaje,
        'es_correcto': es_correcto,
        'codigo_previo': codigo_previo # Enviamos el código de vuelta
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
                
                # CORRECCIÓN 1: Usamos la función oficial de Django para iniciar sesión.
                # Esto asegura que el "user.is_authenticated" de tu HTML funcione perfecto.
                login(request, usuario)

                # CORRECCIÓN 2: Cambiamos 'home' por 'lista_cursos' que es tu ruta real
                return redirect('lista_cursos')

            else:
                messages.error(request, "la contraseña esta inorreta carnal :)")

        except User.DoesNotExist:
            messages.error(request, "No esta registrado ve a registrarte :)")

        return redirect('login')

    return render(request, 'aprendizaje/login.html')