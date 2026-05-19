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
from .models import Curso, Leccion, Ejercicio, Estudiante, Reclutador, PerfilProfesional, Amistad, RetoCodigo, RetoInteractivo, OfertaLaboral, RankingSemanal, LigaSemanal, Postulacion, PerfilProfesional, Notificacion
from .forms import RegistroRedOwlForm, EditarEstudianteForm, EditarPerfilProfesionalForm
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.forms import AuthenticationForm
from .forms import OfertaLaboralForm

@login_required(login_url='login')
def lista_cursos(request):
    if hasattr(request.user, 'reclutador'):
        return redirect('dashboard_reclutador')
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

    # =========================================================================
    # PROCESAMIENTO DEL FORMULARIO (POST)
    # =========================================================================
    if request.method == 'POST':
        # 🛡️ ESCUDO DE SEGURIDAD BACKEND: Evita ejecuciones si no hay energía
        if request.user.is_authenticated and hasattr(request.user, 'estudiante'):
            if request.user.estudiante.energia <= 0:
                context = {
                    'leccion': leccion,
                    'ejercicios': ejercicios,
                    'mensaje': "❌ Operación abortada por el servidor. Tu terminal no tiene suficiente energía (⚡ 0/5). Espera a la recarga automática.",
                    'es_correcto': False,
                    'codigo_previo': request.POST.get('codigo_alumno', '')
                }
                return render(request, 'aprendizaje/detalle_leccion.html', context)

        # Identificamos QUÉ ejercicio están intentando resolver
        ejercicio_id = request.POST.get('ejercicio_id')
        if ejercicio_id:
            ejercicio_actual = ejercicios.filter(id=ejercicio_id).first()
        else:
            ejercicio_actual = ejercicios.first()

        # ---------------------------------------------------------
        # 🧠 RAMA A: PROCESAR RETO INTERACTIVO (Multi-idioma / Multi-formato)
        # ---------------------------------------------------------
        if ejercicio_actual and ejercicio_actual.tipo_ejercicio == 'Q':
            reto = getattr(ejercicio_actual, 'retointeractivo', None)
            tipo_reto = request.POST.get('tipo_reto')
            respuesta_alumno = request.POST.get('respuesta_alumno', '').strip()
            
            if reto:
                config = reto.configuracion
                try:
                    # 1. Opción Múltiple (OM)
                    if tipo_reto == 'OM':
                        if respuesta_alumno and int(respuesta_alumno) == int(config.get('indice_correcto', -1)):
                            mensaje = "¡Excelente! Respuesta correcta. 🔮"
                            es_correcto = True
                        else:
                            mensaje = "❌ Respuesta incorrecta. Vuelve a intentarlo."
                            es_correcto = False

                    # 2. Rellenar Huecos (RH)
                    elif tipo_reto == 'RH':
                        respuesta_esperada = config.get('respuesta_correcta', '').strip()
                        if respuesta_alumno.lower() == respuesta_esperada.lower():
                            mensaje = "¡Excelente! Has completado el espacio correctamente. 🔮"
                            es_correcto = True
                        else:
                            mensaje = "❌ Respuesta incorrecta. El texto no coincide."
                            es_correcto = False

                    # 3. Ordenar Texto (OT)
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
                            es_correcto = False

                    # 4. Enlazar Palabras (EP)
                    elif tipo_reto == 'EP':
                        try:
                            # El frontend manda un string JSON del dict construido por el alumno
                            dict_alumno = json.loads(respuesta_alumno) if respuesta_alumno else {}
                        except json.JSONDecodeError:
                            dict_alumno = {}
                            
                        dict_esperado = config.get('parejas', {})
                        
                        # Comparamos si ambos diccionarios mapean exactamente lo mismo
                        if dict_alumno == dict_esperado:
                            mensaje = "¡Espléndido! Has enlazado todos los conceptos con su definición correcta. 🔮"
                            es_correcto = True
                        else:
                            if len(dict_alumno) < len(dict_esperado):
                                mensaje = "⚠️ Faltan conceptos por enlazar en la matriz de juego."
                            else:
                                mensaje = "❌ Algunos enlaces no son correctos. Haz clic en los bloques morados para romper el enlace e intentar de nuevo."
                            es_correcto = False

                except Exception as e:
                    mensaje = f"⚠️ Error al procesar los datos del reto: {str(e)}"
                    es_correcto = False
            else:
                mensaje = "⚠️ El reto interactivo no está configurado correctamente en la base de datos."
                es_correcto = False

        # ---------------------------------------------------------
        # 💻 RAMA B: PROCESAR RETO DE CÓDIGO (Tu lógica intacta)
        # ---------------------------------------------------------
        else:
            codigo_recibido = request.POST.get('codigo_alumno', '')
            codigo_previo = codigo_recibido 
            
            # 1. Detectamos el lenguaje basado en el nombre del curso
            nombre_curso = leccion.curso.nombre.lower()
            if 'javascript' in nombre_curso or 'js' in nombre_curso:
                lenguaje = 'javascript'
            elif 'java' in nombre_curso:
                lenguaje = 'java'
            else:
                lenguaje = 'python'
            
            # 2. Extraemos el resultado esperado del JSON
            expected_output = ""
            if ejercicio_actual and hasattr(ejercicio_actual, 'retocodigo'):
                casos_prueba = ejercicio_actual.retocodigo.casos_prueba
                if isinstance(casos_prueba, str):
                    try:
                        casos_prueba = json.loads(casos_prueba)
                    except json.JSONDecodeError:
                        casos_prueba = {}
                expected_output = casos_prueba.get('test_1', {}).get('expected_output', '').strip()

            salida_texto = ""
            error_texto = ""

            try:
                # MOTOR DE EJECUCIÓN SEGURO
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

                # VALIDACIÓN DE RESULTADOS DEL CÓDIGO
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

        # =========================================================
        # SISTEMA DE ENERGÍA (⚡) Y RACHAS (Igual para Ambos Casos)
        # =========================================================
        if request.user.is_authenticated and hasattr(request.user, 'estudiante'):
            estudiante = request.user.estudiante
            
            if es_correcto:
                puntos_ejercicio = getattr(ejercicio_actual, 'xp_recompensa', 10) # Usa 10 como fallback si no existe el campo
                estudiante.xp_total += puntos_ejercicio
                estudiante.racha_ejercicios += 1
                
                # 🛡️ CABLE 1: ¡Sumamos los puntos del ejercicio a la liga semanal!
                ranking_actual = RankingSemanal.objects.filter(estudiante=estudiante).order_by('-semana_inicio').first()
                if ranking_actual:
                    ranking_actual.xp_ganada_esta_semana += puntos_ejercicio
                    ranking_actual.save()
                
                # Lógica de rachas de energía
                if estudiante.racha_ejercicios == 3:
                    estudiante.energia = min(5, estudiante.energia + 1)
                    mensaje += "\n\n⚡ ¡Racha de 3 aciertos! Has recuperado 1 de energía."
                elif estudiante.racha_ejercicios == 5:
                    estudiante.energia = min(5, estudiante.energia + 2)
                    mensaje += "\n\n⚡ ¡Racha de 5 aciertos! Has recuperado 2 de energía."
                elif estudiante.racha_ejercicios == 7:
                    estudiante.energia = min(5, estudiante.energia + 3)
                    mensaje += "\n\n⚡ ¡Imparable! (7 aciertos) Has recuperado 3 de energía."
            else:
                estudiante.racha_ejercicios = 0 
                if estudiante.energia > 0:
                    if estudiante.energia == 5:
                        estudiante.fecha_ultima_recarga = timezone.now()
                    estudiante.energia -= 1
                    mensaje += f"\n\n⚠️ ¡Fallaste! Pierdes 1 de energía. Nivel actual: {estudiante.energia}/5 ⚡."
                else:
                    mensaje = "❌ ¡ENERGÍA AGOTADA! Sistema bloqueado. Espera a recargar."
            
            estudiante.save()

    # =========================================================
    # SISTEMA DE EXPERIENCIA Y RACHAS 🦉⭐ (Bono por Lección Completada)
    # =========================================================
    if es_correcto:
        if not leccion.completada:
            if request.user.is_authenticated and hasattr(request.user, 'estudiante'):
                estudiante = request.user.estudiante
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
                
                # 🛡️ CABLE 2: ¡Sumamos el bono de fin de lección a la liga semanal!
                ranking_actual = RankingSemanal.objects.filter(estudiante=estudiante).order_by('-semana_inicio').first()
                if ranking_actual:
                    ranking_actual.xp_ganada_esta_semana += puntos_a_ganar
                    ranking_actual.save()
                
                mensaje += f" ¡Ganaste {puntos_a_ganar} XP!"
                    
            leccion.completada = True
            leccion.save()

    # =========================================================================
    # PREPARACIÓN PARA EL TEMPLATE (GET y POST)
    # =========================================================================
    # Empaquetamos los ejercicios con sus datos extendidos (Reto o Quiz)
    ejercicios_con_datos = []
    for ej in ejercicios:
        datos = {'ejercicio': ej}
        if ej.tipo_ejercicio == 'C' and hasattr(ej, 'retocodigo'):
            datos['reto'] = ej.retocodigo
        elif ej.tipo_ejercicio == 'Q' and hasattr(ej, 'quizingles'):
            datos['quiz'] = ej.quizingles
        ejercicios_con_datos.append(datos)

    return render(request, 'aprendizaje/detalle_leccion.html', {
        'leccion': leccion,
        'ejercicios': ejercicios, # Pasamos la lista armada
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

@login_required
def dashboard_reclutador(request):
    # Verificamos que el usuario logueado sea realmente un reclutador
    if not hasattr(request.user, 'reclutador'):
        # Si es estudiante o admin, lo mandamos al inicio
        return redirect('lista_cursos') 
    
    reclutador = request.user.reclutador
    # Traemos las ofertas creadas por este reclutador ordenadas por la más reciente
    ofertas = OfertaLaboral.objects.filter(reclutador=reclutador).order_by('-fecha_publicacion')
    
    return render(request, 'aprendizaje/dashboard_reclutador.html', {
        'reclutador': reclutador,
        'ofertas': ofertas
    })

@login_required
def crear_oferta(request):
    if not hasattr(request.user, 'reclutador'):
        return redirect('dashboard_reclutador')
        
    if request.method == 'POST':
        form = OfertaLaboralForm(request.POST)
        if form.is_valid():
            nueva_oferta = form.save(commit=False)
            # Le asignamos la oferta al reclutador que la está creando
            nueva_oferta.reclutador = request.user.reclutador
            nueva_oferta.save()
            return redirect('dashboard_reclutador')
    else:
        form = OfertaLaboralForm()
        
    return render(request, 'aprendizaje/crear_oferta.html', {'form': form})

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
    contexto = {}

    # Siempre calculamos el Top Global histórico (sirve para estudiantes y reclutadores)
    top_global = Estudiante.objects.all().order_by('-xp_total')[:50]
    contexto['top_global'] = top_global

    # LÓGICA PARA ESTUDIANTES
    if hasattr(request.user, 'estudiante'):
        contexto['tipo_usuario'] = 'estudiante'
        estudiante_actual = request.user.estudiante
        
        # Buscamos su ranking semanal
        ranking_usuario = RankingSemanal.objects.filter(estudiante=estudiante_actual).order_by('-semana_inicio').first()
        
        if ranking_usuario:
            competidores = RankingSemanal.objects.filter(
                liga=ranking_usuario.liga,
                semana_inicio=ranking_usuario.semana_inicio
            ).order_by('-xp_ganada_esta_semana')
            
            contexto['nombre_liga'] = ranking_usuario.liga.division
            contexto['competidores'] = competidores
        else:
            contexto['nombre_liga'] = "Liga Bronce"
            contexto['competidores'] = []

    # LÓGICA PARA RECLUTADORES
    elif hasattr(request.user, 'reclutador'):
        contexto['tipo_usuario'] = 'reclutador'
        contexto['nombre_liga'] = "Ranking de Talentos"
    
    else:
        contexto['tipo_usuario'] = 'reclutador'
        contexto['nombre_liga'] = "Ranking Global"

    return render(request, 'aprendizaje/ligas.html', contexto)

@login_required(login_url='login')
def desafios(request):
    return render(request, 'aprendizaje/desafios.html')

def login_usuario(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            usuario = form.get_user()
            login(request, usuario)
            return redirect('lista_cursos')
    else:
        form = AuthenticationForm()
        
    return render(request, 'aprendizaje/login.html', {'form': form})

@login_required
def redireccion_inicio(request):
    # Si tiene el perfil de reclutador, lo mandamos a su panel
    if hasattr(request.user, 'reclutador'):
        return redirect('dashboard_reclutador')
    # Si es estudiante o administrador, lo mandamos a los cursos
    else:
        return redirect('lista_cursos') # Cambia 'lista_cursos' por el nombre de tu vista principal de cursos
    
@login_required
def bolsa_trabajo(request):
    # Verificamos que sea un estudiante
    if not hasattr(request.user, 'estudiante'):
        return redirect('dashboard_reclutador')
    
    estudiante = request.user.estudiante
    # Traemos las ofertas activas
    ofertas_activas = OfertaLaboral.objects.filter(activa=True).order_by('-fecha_publicacion')
    
    perfil = getattr(estudiante, 'perfilprofesional', None)
    
    # Preparamos las habilidades del estudiante en minúsculas para compararlas más fácil
    habilidades_estudiante = []
    if perfil and perfil.habilidades:
        # Convertimos la lista JSON a minúsculas
        habilidades_estudiante = [hab.lower().strip() for hab in perfil.habilidades]

    ofertas_procesadas = []

    for oferta in ofertas_activas:
        # 1. TRUCO NUEVO: Traemos el objeto completo de la postulación si existe (En vez de un .exists() booleano)
        postulacion_actual = Postulacion.objects.filter(estudiante=estudiante, oferta=oferta).first()

        # 2. Motor de Validación Inteligente
        cumple_requisitos = False
        
        if perfil and habilidades_estudiante and oferta.requisitos:
            # Convertimos el texto del reclutador a minúsculas
            requisitos_texto = oferta.requisitos.lower()
            
            # Buscamos si AL MENOS UNA de las habilidades del estudiante se menciona en los requisitos
            for hab in habilidades_estudiante:
                if hab in requisitos_texto:
                    cumple_requisitos = True
                    break # Con una que coincida, desbloqueamos la misión
        
        # 3. Empaquetamos la oferta con el nuevo dato objeto
        ofertas_procesadas.append({
            'oferta': oferta,
            'postulacion_actual': postulacion_actual,  # <--- Enviamos el objeto completo al HTML
            'puede_postularse': cumple_requisitos
        })

    return render(request, 'aprendizaje/bolsa_trabajo.html', {
        'ofertas_procesadas': ofertas_procesadas,
        'perfil': perfil
    })

def iniciar_semana_prueba(request):
    # Solo permitimos que el superusuario haga esto
    if not request.user.is_superuser:
        return redirect('ligas')

    hoy = timezone.now().date()
    fecha_cierre = hoy + timedelta(days=7) # Cierra en 7 días

    # 1. Creamos la "Liga Bronce" de esta semana (o la obtenemos si ya existe)
    liga, creada = LigaSemanal.objects.get_or_create(
        division="Liga Bronce",
        defaults={'fecha_cierre': fecha_cierre}
    )

    # 2. Inscribimos a TODOS los estudiantes en esta liga
    estudiantes = Estudiante.objects.all()
    for estudiante in estudiantes:
        
        # Usamos update_or_create para poder "resetear" la semana 
        # cada vez que visitemos la URL en modo desarrollador
        RankingSemanal.objects.update_or_create(
            estudiante=estudiante,
            semana_inicio=hoy,
            defaults={
                'liga': liga,
                'xp_ganada_esta_semana': 10, # 🎁 ¡Bono de bienvenida de 10 puntos para todos!
                'puesto_actual': 0
            }
        )

    # Al terminar, te regresamos a la pantalla de ligas para ver el resultado
    return redirect('ligas')

def ver_perfil_publico(request, estudiante_id):
    # 1. Buscamos al estudiante por su ID
    estudiante_visto = get_object_or_404(Estudiante, pk=estudiante_id)
    
    # 2. Buscamos su perfil profesional (si es que ya llenó el formulario que me mostraste)
    # Usamos getattr por si el estudiante aún no ha guardado su perfil, para que no truene la página
    perfil_profesional = getattr(estudiante_visto, 'perfilprofesional', None)
    
    # 3. Buscamos su liga actual para presumirla en el currículum
    ranking_actual = RankingSemanal.objects.filter(estudiante=estudiante_visto).order_by('-semana_inicio').first()
    liga_actual = ranking_actual.liga.division if ranking_actual else "Sin clasificar"
    
    contexto = {
        'candidato': estudiante_visto,
        'perfil_profesional': perfil_profesional,
        'liga_actual': liga_actual,
    }
    
    # Renderizamos una nueva plantilla HTML de solo lectura
    return render(request, 'aprendizaje/perfil_publico.html', contexto)

@login_required
def postular_oferta(request, oferta_id):
    if request.method == 'POST':
        estudiante = request.user.estudiante
        oferta = get_object_or_404(OfertaLaboral, id=oferta_id)
        
        # Buscamos si ya existía (no importa el estado) o la creamos si no existía
        postulacion, created = Postulacion.objects.get_or_create(
            estudiante=estudiante,
            oferta=oferta
        )
        
        # Si ya existía y estaba 'Rechazada', la reiniciamos a 'Enviada'
        # Si era nueva, por defecto pasa a 'Enviada'
        postulacion.estado = 'Enviada'
        postulacion.save()
        
    return redirect('bolsa_trabajo')

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import OfertaLaboral, Postulacion

@login_required
def dashboard_reclutador(request):
    # Verificamos que el usuario tenga el perfil de reclutador
    if not hasattr(request.user, 'reclutador'):
        return redirect('bolsa_trabajo') # Si es estudiante, lo mandamos a la bolsa
        
    reclutador = request.user.reclutador
    
    # Traemos las ofertas creadas por este reclutador específico
    # Usamos prefetch_related o un contador para saber cuántas postulaciones tiene cada una
    ofertas = OfertaLaboral.objects.filter(reclutador=reclutador).order_by('-fecha_publicacion')
    
    # Añadimos el conteo de postulaciones de forma dinámica para mostrarlo en el HTML
    for oferta in ofertas:
        oferta.total_postulantes = oferta.postulacion_set.count()

    return render(request, 'aprendizaje/dashboard_reclutador.html', {
        'ofertas': ofertas
    })

@login_required
def ver_postulantes(request, oferta_id):
    if not hasattr(request.user, 'reclutador'):
        return redirect('bolsa_trabajo')
        
    reclutador = request.user.reclutador
    # Aseguramos que la oferta exista y pertenezca a este reclutador para evitar que husmee otras ofertas
    oferta = get_object_or_404(OfertaLaboral, id=oferta_id, reclutador=reclutador)
    
    # Traemos todas las postulaciones de esta oferta
    postulaciones = Postulacion.objects.filter(oferta=oferta).select_related('estudiante__usuario', 'estudiante__perfilprofesional')

    # PROCESAR CAMBIO DE ESTADO (Si el reclutador presiona "Aceptar" o "Rechazar")
    if request.method == 'POST':
        postulacion_id = request.POST.get('postulacion_id')
        nuevo_estado = request.POST.get('nuevo_estado')
        
        if postulacion_id and nuevo_estado in ['En Revisión', 'Aceptada', 'Rechazada']:
            postulacion = get_object_or_404(Postulacion, id=postulacion_id, oferta=oferta)
            postulacion.estado = nuevo_estado
            postulacion.save()
            
            # --- NUEVO: ¡Disparamos la notificación al estudiante! ---
            if nuevo_estado == 'Aceptada':
                mensaje = f"🎉 ¡Felicidades! Fuiste ACEPTADO en la misión: {oferta.titulo}."
            elif nuevo_estado == 'Rechazada':
                mensaje = f"❌ Tu postulación para '{oferta.titulo}' no avanzó. ¡Mejora tus habilidades y vuelve a intentarlo!"
            else:
                mensaje = f"👀 Tu postulación para '{oferta.titulo}' está siendo revisada."
                
            Notificacion.objects.create(usuario=postulacion.estudiante.usuario, mensaje=mensaje)
            # ---------------------------------------------------------

            return redirect('ver_postulantes', oferta_id=oferta.id)

    return render(request, 'aprendizaje/ver_postulantes.html', {
        'oferta': oferta,
        'postulaciones': postulaciones
    })

from django.http import JsonResponse
from .models import Notificacion

@login_required
def marcar_notificaciones_leidas(request):
    if request.method == 'POST':
        # Buscamos las notificaciones del usuario que estén sin leer y las actualizamos
        Notificacion.objects.filter(usuario=request.user, leida=False).update(leida=True)
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)