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

            if check_password(password, usuario.password):

                # Guardar sesión
                request.session['usuario_id'] = usuario.id
                request.session['username'] = usuario.username

                return redirect('home')

            else:
                messages.error(request, "la contraseña esta inorreta carnal :)")

        except User.DoesNotExist:
            messages.error(request, "No esta registrado ve a registrarte :)")

        return redirect('login')

    return render(request, 'aprendizaje/login.html')