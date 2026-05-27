import json
import subprocess
import tempfile
import os
import random
from datetime import timedelta

from .utils import registrar_avance_misiones, evaluar_codigo, evaluar_reto_interactivo
from django.utils import timezone
from django.utils.timezone import now
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse

from .models import (Curso, Leccion, Ejercicio, Estudiante, Reclutador, 
                     PerfilProfesional, Amistad, OfertaLaboral, RankingSemanal, 
                     LigaSemanal, Postulacion, Notificacion, Novedad, 
                     DesafioDiario, ProgresoDesafio, ProgresoLeccion, CofreAbierto)
from .forms import (RegistroRedOwlForm, EditarEstudianteForm, 
                    EditarPerfilProfesionalForm, EditarReclutadorForm, 
                    OfertaLaboralForm)
from .utils import registrar_avance_misiones

@login_required(login_url='login')
def lista_cursos(request):
    if hasattr(request.user, 'reclutador'):
        return redirect('dashboard_reclutador')
    # Obtenemos todos los cursos
    cursos = Curso.objects.all() 
    return render(request, 'aprendizaje/lista_cursos.html', {'cursos': cursos})

def detalle_curso(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)  
    lecciones = Leccion.objects.filter(curso=curso).order_by('orden')
    cofres_abiertos_ids = set() # Por defecto vacío si es un usuario invitado
    
    # Pre-calculamos el estado de bloqueo y completado para inyectarlo al HTML
    if request.user.is_authenticated and hasattr(request.user, 'estudiante'):
        estudiante = request.user.estudiante
        
        # 📦 NUEVO: Traer los IDs de las lecciones cuyos cofres YA abrió este estudiante
        # (Esto sirve para que si recarga la página, el cofre aparezca como abierto "🔓")
        cofres_abiertos_ids = set(
            CofreAbierto.objects.filter(estudiante=estudiante).values_list('leccion_previa_id', flat=True)
        )
        
        for leccion in lecciones:
            leccion.bloqueada = leccion.esta_bloqueada_para(estudiante)
            progreso = ProgresoLeccion.objects.filter(estudiante=estudiante, leccion=leccion).first()
            leccion.esta_completada = progreso.completada if progreso else False
    else:
        # Si no hay estudiante, bloqueamos todo menos la lección 1 por defecto
        for leccion in lecciones:
            leccion.bloqueada = (leccion.orden != 1)
            leccion.esta_completada = False

    return render(request, 'aprendizaje/detalle_curso.html', {
        'curso': curso, 
        'lecciones': lecciones,
        'cofres_abiertos_ids': cofres_abiertos_ids # <-- NUEVO: Se lo inyectamos a la plantilla
    })

# 📦 NUEVA VISTA AJAX (Agrégala justo aquí abajo)
@login_required(login_url='login')
def abrir_cofre_ajax(request, leccion_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
        
    estudiante = request.user.estudiante
    leccion_previa = get_object_or_404(Leccion, id=leccion_id)

    # 1. Seguridad: Verificar si ya abrió este cofre antes
    if CofreAbierto.objects.filter(estudiante=estudiante, leccion_previa=leccion_previa).exists():
        return JsonResponse({'error': 'Este cofre ya fue reclamado.'}, status=400)

    # 2. Seguridad: Verificar si de verdad completó la lección anterior
    # Usamos tu misma estructura de validación con tu modelo ProgresoLeccion
    progreso = ProgresoLeccion.objects.filter(estudiante=estudiante, leccion=leccion_previa).first()
    if not (progreso and progreso.completada):
        return JsonResponse({'error': 'Primero debes completar la lección anterior para abrir este cofre.'}, status=400)

    # 3. Registrar de forma segura que el cofre ya fue abierto
    CofreAbierto.objects.create(estudiante=estudiante, leccion_previa=leccion_previa)

    # 4. Algoritmo de probabilidad del videojuego (70% XP / 30% Protector de Racha)
    suerte = random.randint(1, 100)
    
    if suerte <= 70:
        # 70% de Probabilidad: XP Aleatoria entre 20 y 50 puntos
        xp_ganada = random.randint(20, 50)
        estudiante.xp_total = (estudiante.xp_total or 0) + xp_ganada
        estudiante.save()
        
        return JsonResponse({
            'success': True,
            'tipo': 'xp',
            'titulo': '¡Puntos de Experiencia!',
            'mensaje': f'¡Has encontrado +{xp_ganada} XP dentro de la caja!',
            'icono': '💎',
            'nuevo_total_xp': estudiante.xp_total
        })
    else:
        # 30% de Probabilidad: Ítem épico (Protector de racha)
        estudiante.protectores_racha = (estudiante.protectores_racha or 0) + 1
        estudiante.save()
        
        return JsonResponse({
            'success': True,
            'tipo': 'protector',
            'titulo': '¡ÍTEM ÉPICO!',
            'mensaje': '¡Has obtenido 1 Protector de Racha (🔥🛡️)! Tus días sin ingresar ahora están protegidos.',
            'icono': '🛡️',
            'protectores_conteo': estudiante.protectores_racha
        })

def detalle_leccion(request, leccion_id):
    leccion = get_object_or_404(Leccion, id=leccion_id)
    ejercicios = Ejercicio.objects.filter(leccion=leccion)

    # 🛡️ NUEVO CERROJO DE SEGURIDAD: Evitar acceso por URL
    if request.user.is_authenticated and hasattr(request.user, 'estudiante'):
        estudiante = request.user.estudiante
        if leccion.esta_bloqueada_para(estudiante):
            # Si está bloqueada, lo regresamos al mapa del curso
            return redirect('detalle_curso', curso_id=leccion.curso.id)
    elif leccion.orden != 1:
        # Si no está logueado y no es la lección 1, también lo rebotamos
        return redirect('detalle_curso', curso_id=leccion.curso.id)
    
    # Variables para enviar a la plantilla
    mensaje = None
    es_correcto = False
    codigo_previo = ""

    # =========================================================================
    # PROCESAMIENTO DEL FORMULARIO (POST)
    # =========================================================================
    if request.method == 'POST':
        # 🛡️ ESCUDO DE SEGURIDAD BACKEND
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

        ejercicio_id = request.POST.get('ejercicio_id')
        if ejercicio_id:
            ejercicio_actual = ejercicios.filter(id=ejercicio_id).first()
        else:
            ejercicio_actual = ejercicios.first()

        # ---------------------------------------------------------
        # 🧠 RAMA A: PROCESAR RETO INTERACTIVO
        # ---------------------------------------------------------
        if ejercicio_actual and ejercicio_actual.tipo_ejercicio == 'Q':
            reto = getattr(ejercicio_actual, 'retointeractivo', None)
            tipo_reto = request.POST.get('tipo_reto')
            respuesta_alumno = request.POST.get('respuesta_alumno', '').strip()
            
            if reto:
                # 🚀 LLAMAMOS A NUESTRA NUEVA HERRAMIENTA EXTERNA
                es_correcto, mensaje = evaluar_reto_interactivo(tipo_reto, respuesta_alumno, reto.configuracion)
            else:
                mensaje = "⚠️ El reto interactivo no está configurado correctamente en la base de datos."
                es_correcto = False
        # ---------------------------------------------------------
        # 💻 RAMA B: PROCESAR RETO DE CÓDIGO
        # ---------------------------------------------------------
        else:
            codigo_recibido = request.POST.get('codigo_alumno', '')
            codigo_previo = codigo_recibido 
            
            # 1. Buscamos el output esperado en el JSON
            expected_output = ""
            if ejercicio_actual and hasattr(ejercicio_actual, 'retocodigo'):
                casos_prueba = ejercicio_actual.retocodigo.casos_prueba
                if isinstance(casos_prueba, str):
                    try:
                        casos_prueba = json.loads(casos_prueba)
                    except json.JSONDecodeError:
                        casos_prueba = {}
                expected_output = casos_prueba.get('test_1', {}).get('expected_output', '').strip()

            # 2. 🚀 LLAMAMOS A NUESTRA HERRAMIENTA EXTERNA
            es_correcto, mensaje = evaluar_codigo(leccion.curso.nombre, codigo_recibido, expected_output)

        # =========================================================
        # SISTEMA DE ENERGÍA (⚡) Y RACHAS
        # =========================================================
        if request.user.is_authenticated and hasattr(request.user, 'estudiante'):
            estudiante = request.user.estudiante
            
            if es_correcto:
                puntos_ejercicio = getattr(ejercicio_actual, 'xp_recompensa', 10)
                estudiante.xp_total += puntos_ejercicio
                estudiante.racha_ejercicios += 1
                
                ranking_actual = RankingSemanal.objects.filter(estudiante=estudiante).order_by('-semana_inicio').first()
                if ranking_actual:
                    ranking_actual.xp_ganada_esta_semana += puntos_ejercicio
                    ranking_actual.save()
                
                if estudiante.racha_ejercicios == 3:
                    estudiante.energia = min(10, estudiante.energia + 1)
                    mensaje += "\n\n⚡ ¡Racha de 3 aciertos! Has recuperado 1 de energía."
                elif estudiante.racha_ejercicios == 5:
                    estudiante.energia = min(10, estudiante.energia + 2)
                    mensaje += "\n\n⚡ ¡Racha de 5 aciertos! Has recuperado 2 de energía."
                elif estudiante.racha_ejercicios == 7:
                    estudiante.energia = min(10, estudiante.energia + 3)
                    mensaje += "\n\n⚡ ¡Imparable! (7 aciertos) Has recuperado 3 de energía."
            else:
                estudiante.racha_ejercicios = 0 
                if estudiante.energia > 0:
                    if estudiante.energia == 10:
                        estudiante.fecha_ultima_recarga = timezone.now()
                    estudiante.energia -= 1
                    mensaje += f"\n\n⚠️ ¡Fallaste! Pierdes 1 de energía. Nivel actual: {estudiante.energia}/10 ⚡."
                else:
                    mensaje = "❌ ¡ENERGÍA AGOTADA! Sistema bloqueado. Espera a recargar."
            
            estudiante.save()

    # =========================================================
    # BONO POR LECCIÓN COMPLETADA
    # =========================================================
    if es_correcto:
        if request.user.is_authenticated and hasattr(request.user, 'estudiante'):
            estudiante = request.user.estudiante
            
            # 🚀 NUEVO: Buscamos o creamos el progreso para ESTE estudiante
            progreso_leccion, created = ProgresoLeccion.objects.get_or_create(
                estudiante=estudiante, 
                leccion=leccion
            )
            
            # Si el registro no estaba marcado como completado, damos la recompensa
            if not progreso_leccion.completada:
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
                
                ranking_actual = RankingSemanal.objects.filter(estudiante=estudiante).order_by('-semana_inicio').first()
                if ranking_actual:
                    ranking_actual.xp_ganada_esta_semana += puntos_a_ganar
                    ranking_actual.save()
                
                registrar_avance_misiones(estudiante, 'xp', puntos_a_ganar)
                registrar_avance_misiones(estudiante, 'lecciones', 1)
                
                mensaje += f" ¡Ganaste {puntos_a_ganar} XP!"
                    
                # 🚀 NUEVO: Guardamos el progreso como completado en la tabla intermedia
                progreso_leccion.completada = True
                progreso_leccion.save()

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
        'ejercicios': ejercicios, 
        'mensaje': mensaje,
        'es_correcto': es_correcto,
        'codigo_previo': codigo_previo
    })

def registro(request):
    if request.method == 'POST':
        form = RegistroRedOwlForm(request.POST) 
        if form.is_valid():
            user_django = form.save()
            tipo = form.cleaned_data.get('tipo_usuario')
            
            if tipo == 'estudiante':
                nombre_escuela = form.cleaned_data.get('escuela') or "Sin escuela"
                estudiante = Estudiante.objects.create(usuario=user_django, xp_total=0, racha_dias=0, escuela=nombre_escuela)
                PerfilProfesional.objects.create(estudiante=estudiante)
                
            elif tipo == 'reclutador':
                nombre_empresa = form.cleaned_data.get('empresa') or "Independiente"
                Reclutador.objects.create(usuario=user_django, empresa=nombre_empresa)
            
            login(request, user_django)
            return redirect('lista_cursos')
    else:
        form = RegistroRedOwlForm()
    
    return render(request, 'aprendizaje/registro.html', {'form': form})

@login_required
def mi_panel(request):
    if hasattr(request.user, 'estudiante'):
        estudiante = request.user.estudiante
        estudiante.verificar_y_limpiar_racha()
        return render(request, 'aprendizaje/mi_panel.html', {'estudiante': estudiante})


@login_required
def perfil(request):
    user = request.user
    es_estudiante = hasattr(user, 'estudiante')
    
    if es_estudiante:
        estudiante = user.estudiante
        estudiante.verificar_y_limpiar_racha()
        perfil_prof, created = PerfilProfesional.objects.get_or_create(estudiante=estudiante)
        
        if request.method == 'POST':
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
        # ⚡ LÓGICA PARA CUANDO ENTRA UN RECLUTADOR (NUEVO FORMULARIO INTEGRADO)
        reclutador = user.reclutador
        
        if request.method == 'POST':
            form_reclutador = EditarReclutadorForm(request.POST, instance=reclutador)
            if form_reclutador.is_valid():
                form_reclutador.save()
                messages.success(request, '¡Información del panel de contratista actualizada con éxito!')
                return redirect('perfil')
        else:
            form_reclutador = EditarReclutadorForm(instance=reclutador)
            
        context = {
            'es_estudiante': False,
            'reclutador': reclutador,
            'form_reclutador': form_reclutador, # Lo enviamos al template
        }
        
    return render(request, 'aprendizaje/perfil.html', context)

@login_required
def dashboard_reclutador(request):
    if not hasattr(request.user, 'reclutador'):
        return redirect('lista_cursos') 
    
    reclutador = request.user.reclutador
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
            nueva_oferta.reclutador = request.user.reclutador
            nueva_oferta.save()
            return redirect('dashboard_reclutador')
    else:
        form = OfertaLaboralForm()
        
    return render(request, 'aprendizaje/crear_oferta.html', {'form': form})

@login_required
def editar_oferta(request, oferta_id):
    # Verificamos que sea un reclutador
    if not hasattr(request.user, 'reclutador'):
        return redirect('lista_cursos')
        
    reclutador = request.user.reclutador
    
    # Obtenemos la oferta asegurando que pertenece a este reclutador
    oferta = get_object_or_404(OfertaLaboral, id=oferta_id, reclutador=reclutador)
    
    if request.method == 'POST':
        # Le pasamos instance=oferta para decirle a Django que actualice, no que cree una nueva
        form = OfertaLaboralForm(request.POST, instance=oferta)
        if form.is_valid():
            form.save()
            return redirect('dashboard_reclutador')
    else:
        # Pre-llenamos el formulario con los datos actuales
        form = OfertaLaboralForm(instance=oferta)
        
    return render(request, 'aprendizaje/editar_oferta.html', {
        'form': form, 
        'oferta': oferta
    })

@login_required(login_url='login')
def red_amigos(request):
    usuario_actual = request.user
    mensaje = None
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        
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
                    
        elif accion == 'eliminar':
            amigo_id = request.POST.get('amigo_id')
            Amistad.objects.filter(usuario=usuario_actual, amigo__id=amigo_id).delete()
            mensaje = "> ENLACE DESTRUIDO."

    conexiones = Amistad.objects.filter(usuario=usuario_actual)
    return render(request, 'aprendizaje/amigos.html', {
        'conexiones': conexiones,
        'mensaje': mensaje
    })

@login_required(login_url='login')
def ligas(request):
    contexto = {}
    
    # 1. Traemos el Top Global (Salón de la fama) idéntico a como lo tenías
    contexto['top_global'] = Estudiante.objects.all().order_by('-xp_total')[:50]
    contexto['competidores'] = [] # Valor por defecto

    # 2. Lógica adaptada para el Estudiante
    if hasattr(request.user, 'estudiante'):
        contexto['tipo_usuario'] = 'estudiante'
        estudiante_actual = request.user.estudiante
        
        # Obtenemos su grupo de competencia de esta semana
        ranking_usuario = RankingSemanal.objects.filter(estudiante=estudiante_actual).order_by('-semana_inicio').first()
        
        if ranking_usuario:
            # Traemos a sus competidores semanales de su misma liga y semana
            contexto['competidores'] = RankingSemanal.objects.filter(
                liga=ranking_usuario.liga,
                semana_inicio=ranking_usuario.semana_inicio
            ).order_by('-xp_ganada_esta_semana')

    # 3. Lógica para Reclutadores o Administradores
    elif hasattr(request.user, 'reclutador'):
        contexto['tipo_usuario'] = 'reclutador'
    else:
        contexto['tipo_usuario'] = 'otro'

    return render(request, 'aprendizaje/ligas.html', contexto)

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
    if hasattr(request.user, 'reclutador'):
        return redirect('dashboard_reclutador')
    else:
        return redirect('lista_cursos') 
    
@login_required
def bolsa_trabajo(request):
    if not hasattr(request.user, 'estudiante'):
        return redirect('dashboard_reclutador')
    
    estudiante = request.user.estudiante
    ofertas_activas = OfertaLaboral.objects.filter(activa=True).order_by('-fecha_publicacion')
    perfil = getattr(estudiante, 'perfilprofesional', None)
    
    habilidades_estudiante = []
    if perfil and perfil.habilidades:
        habilidades_estudiante = [hab.lower().strip() for hab in perfil.habilidades]

    # Obtenemos todos los cursos disponibles en la plataforma
    todos_los_cursos = Curso.objects.all()

    ofertas_procesadas = []
    for oferta in ofertas_activas:
        postulacion_actual = Postulacion.objects.filter(estudiante=estudiante, oferta=oferta).first()
        
        # 1. EVALUAR RESTRICCIÓN (Solo importan los obligatorios)
        cumple_requisitos = False
        if not oferta.requisitos_obligatorios:
            # Si el reclutador no puso requisitos obligatorios, todos pueden postularse
            cumple_requisitos = True
        elif perfil and habilidades_estudiante:
            req_obligatorios_texto = oferta.requisitos_obligatorios.lower()
            for hab in habilidades_estudiante:
                if hab in req_obligatorios_texto:
                    cumple_requisitos = True
                    break 
        
        # 2. SISTEMA DE RECOMENDACIÓN DE CURSOS
        cursos_recomendados = []
        # Juntamos todos los requisitos (obligatorios y extras) para buscar palabras clave
        texto_total_req = f"{oferta.requisitos_obligatorios or ''} {oferta.requisitos_extras or ''}".lower()
        
        for curso in todos_los_cursos:
            # Si el lenguaje del curso (ej. "python") aparece en los requisitos, lo recomendamos
            if curso.lenguaje and curso.lenguaje.lower() in texto_total_req:
                cursos_recomendados.append(curso)

        ofertas_procesadas.append({
            'oferta': oferta,
            'postulacion_actual': postulacion_actual,  
            'puede_postularse': cumple_requisitos,
            'cursos_recomendados': cursos_recomendados # Mandamos las recomendaciones a la plantilla
        })

    return render(request, 'aprendizaje/bolsa_trabajo.html', {
        'ofertas_procesadas': ofertas_procesadas,
        'perfil': perfil
    })

def iniciar_semana_prueba(request):
    if not request.user.is_superuser:
        return redirect('ligas')

    hoy = timezone.now().date()
    fecha_cierre = hoy + timedelta(days=7) 

    liga, creada = LigaSemanal.objects.get_or_create(
        division="Liga Bronce",
        defaults={'fecha_cierre': fecha_cierre}
    )

    estudiantes = Estudiante.objects.all()
    for estudiante in estudiantes:
        RankingSemanal.objects.update_or_create(
            estudiante=estudiante,
            semana_inicio=hoy,
            defaults={
                'liga': liga,
                'xp_ganada_esta_semana': 10, 
                'puesto_actual': 0
            }
        )

    return redirect('ligas')

def ver_perfil_publico(request, estudiante_id):
    estudiante_visto = get_object_or_404(Estudiante, pk=estudiante_id)
    perfil_profesional = getattr(estudiante_visto, 'perfilprofesional', None)
    ranking_actual = RankingSemanal.objects.filter(estudiante=estudiante_visto).order_by('-semana_inicio').first()
    liga_actual = ranking_actual.liga.division if ranking_actual else "Sin clasificar"
    
    contexto = {
        'candidato': estudiante_visto,
        'perfil_profesional': perfil_profesional,
        'liga_actual': liga_actual,
    }
    return render(request, 'aprendizaje/perfil_publico.html', contexto)

@login_required
def postular_oferta(request, oferta_id):
    if request.method == 'POST':
        estudiante = request.user.estudiante
        oferta = get_object_or_404(OfertaLaboral, id=oferta_id)
        
        postulacion, created = Postulacion.objects.get_or_create(
            estudiante=estudiante,
            oferta=oferta
        )
        postulacion.estado = 'Enviada'
        postulacion.save()
        
    return redirect('bolsa_trabajo')

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import OfertaLaboral, Postulacion

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

def novedades_view(request):
    # Traemos solo las novedades activas
    lista_novedades = Novedad.objects.filter(activo=True)
    return render(request, 'aprendizaje/novedades.html', {'novedades': lista_novedades})

@login_required(login_url='login')
def desafios(request):
    contexto = {}
    
    if not hasattr(request.user, 'estudiante'):
        return redirect('ligas')
        
    estudiante_actual = request.user.estudiante
    hoy = now().date()
    
    progresos = ProgresoDesafio.objects.filter(estudiante=estudiante_actual, fecha=hoy)
    
    # NUEVA LÓGICA: Inicialización inteligente limitada a 3 desafíos
    if not progresos.exists():
        desafios_globales = list(DesafioDiario.objects.all())
        
        # Seleccionamos máximo 3 desafíos aleatorios del catálogo
        cantidad_a_elegir = min(len(desafios_globales), 3)
        desafios_hoy = random.sample(desafios_globales, cantidad_a_elegir)
        
        for desafio in desafios_hoy:
            progreso_obj = ProgresoDesafio.objects.create(
                estudiante=estudiante_actual,
                desafio=desafio,
                fecha=hoy
            )
            
            # 💡 EXCEPCIÓN DE RACHA: Se comprueba inmediatamente al crearse
            if desafio.tipo == 'racha':
                racha_alumno = getattr(estudiante_actual, 'racha', 0) # Busca el campo 'racha'
                progreso_obj.progreso_actual = min(racha_alumno, desafio.meta)
                
                if progreso_obj.progreso_actual >= desafio.meta:
                    progreso_obj.completado = True
                    # Le sumamos la XP de recompensa por su constancia
                    estudiante_actual.xp_total += desafio.xp_recompensa
                    estudiante_actual.save()
                    
                progreso_obj.save()
                
        # Volvemos a consultar para tener los 3 desafíos definitivos del día
        progresos = ProgresoDesafio.objects.filter(estudiante=estudiante_actual, fecha=hoy)
    
    # Métricas de la terminal
    totales = progresos.count()
    completados = progresos.filter(completado=True).count()
    
    if totales > 0 and completados == totales:
        contexto['status_terminal'] = "SISTEMA COMPLETADO - TODOS LOS OBJETIVOS ALCANZADOS"
    elif totales > 0:
        contexto['status_terminal'] = f"EJECUTANDO: {completados}/{totales} OBJETIVOS CONSEGUIDOS"
    else:
        contexto['status_terminal'] = "SISTEMA EN ESPERA - SIN MISIONES CONFIGURADAS"
        
    contexto['progresos'] = progresos
    return render(request, 'aprendizaje/desafios.html', contexto)