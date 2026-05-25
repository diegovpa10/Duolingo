import json
import os

archivo_json = 'datos_iniciales.json'

nuevos_datos = [
    # =========================================================
    # 🟠 CURSO 8: JAVASCRIPT INTERMEDIO Y DOM
    # =========================================================
    
    # --- LECCIÓN 2: Selección de Elementos DOM ---
    {
        "model": "aprendizaje.leccion", "pk": 102,
        "fields": { "curso": 8, "orden": 2, "titulo": "Selección de Elementos DOM" }
    },
    {
        "model": "aprendizaje.ejercicio", "pk": 210,
        "fields": { "leccion": 102, "tipo_ejercicio": "Q", "enunciado": "¿Qué método usarías para seleccionar un único elemento HTML basándote en su atributo 'id'?", "xp_recompensa": 10 }
    },
    {
        "model": "aprendizaje.retointeractivo", "pk": 210,
        "fields": { "ejercicio": 210, "tipo_reto": "OM", "configuracion": { "opciones": ["querySelector", "getElementsByClassName", "getElementById", "querySelectorAll"], "respuesta_correcta": "getElementById" } }
    },
    {
        "model": "aprendizaje.ejercicio", "pk": 211,
        "fields": { "leccion": 102, "tipo_ejercicio": "Q", "enunciado": "Enlaza cada selector de JavaScript con lo que devuelve.", "xp_recompensa": 15 }
    },
    {
        "model": "aprendizaje.retointeractivo", "pk": 211,
        "fields": { "ejercicio": 211, "tipo_reto": "EP", "configuracion": { "pares": [ {"termino_A": "getElementById", "termino_B": "Un único elemento"}, {"termino_A": "querySelectorAll", "termino_B": "Un NodeList (lista de elementos)"}, {"termino_A": "getElementsByTagName", "termino_B": "Una HTMLCollection basada en la etiqueta"} ] } }
    },
    {
        "model": "aprendizaje.ejercicio", "pk": 212,
        "fields": { "leccion": 102, "tipo_ejercicio": "C", "enunciado": "Usa document.getElementById para seleccionar el elemento con id 'titulo' y cambia su texto a 'DOM Dominado'.", "xp_recompensa": 30 }
    },
    {
        "model": "aprendizaje.retocodigo", "pk": 212,
        "fields": { "ejercicio": 212, "codigo_base": "const elemento = // Tu código aquí\r\n", "casos_prueba": { "test_1": { "descripcion": "Validar modificación del DOM", "expected_output": "DOM Dominado" } }, "tiempo_limite": 40.0 }
    },

    # --- LECCIÓN 3: Eventos en JavaScript ---
    {
        "model": "aprendizaje.leccion", "pk": 103,
        "fields": { "curso": 8, "orden": 3, "titulo": "Eventos y Listeners" }
    },
    {
        "model": "aprendizaje.ejercicio", "pk": 213,
        "fields": { "leccion": 103, "tipo_ejercicio": "Q", "enunciado": "Completa la sintaxis para escuchar un clic en un botón.", "xp_recompensa": 15 }
    },
    {
        "model": "aprendizaje.retointeractivo", "pk": 213,
        "fields": { "ejercicio": 213, "tipo_reto": "RH", "configuracion": { "texto_antes": "boton.", "texto_despues": "('click', function() { alert('Clic'); });", "respuesta_correcta": "addEventListener" } }
    },
    {
        "model": "aprendizaje.ejercicio", "pk": 214,
        "fields": { "leccion": 103, "tipo_ejercicio": "C", "enunciado": "Crea un EventListener para que al hacer 'click' en el botón (id 'btn'), se imprima 'Botón presionado' en consola.", "xp_recompensa": 25 }
    },
    {
        "model": "aprendizaje.retocodigo", "pk": 214,
        "fields": { "ejercicio": 214, "codigo_base": "const btn = document.getElementById('btn');\r\n\r\n// Añade el evento aquí\r\n", "casos_prueba": { "test_1": { "descripcion": "Validar evento click", "expected_output": "Botón presionado" } }, "tiempo_limite": 45.0 }
    },

    # --- LECCIÓN 4: Creando Elementos ---
    {
        "model": "aprendizaje.leccion", "pk": 104,
        "fields": { "curso": 8, "orden": 4, "titulo": "Modificando el DOM dinámicamente" }
    },
    {
        "model": "aprendizaje.ejercicio", "pk": 215,
        "fields": { "leccion": 104, "tipo_ejercicio": "Q", "enunciado": "Ordena los pasos lógicos para crear un nuevo párrafo e insertarlo en la página.", "xp_recompensa": 20 }
    },
    {
        "model": "aprendizaje.retointeractivo", "pk": 215,
        "fields": { "ejercicio": 215, "tipo_reto": "OT", "configuracion": { "elementos_ordenados": [ "1. document.createElement('p')", "2. p.textContent = 'Nuevo texto'", "3. Seleccionar el elemento padre (ej. body)", "4. padre.appendChild(p)" ] } }
    },

    # =========================================================
    # 🔵 CURSO 9: TECHNICAL ENGLISH FOR DEVS
    # =========================================================
    
    # --- LECCIÓN 2: Functions & Methods Vocabulary ---
    {
        "model": "aprendizaje.leccion", "pk": 105,
        "fields": { "curso": 9, "orden": 2, "titulo": "Functions & Methods Vocabulary" }
    },
    {
        "model": "aprendizaje.ejercicio", "pk": 216,
        "fields": { "leccion": 105, "tipo_ejercicio": "Q", "enunciado": "Match the English technical verb with its correct Spanish translation.", "xp_recompensa": 15 }
    },
    {
        "model": "aprendizaje.retointeractivo", "pk": 216,
        "fields": { "ejercicio": 216, "tipo_reto": "EP", "configuracion": { "pares": [ {"termino_A": "To fetch", "termino_B": "Obtener / Recuperar"}, {"termino_A": "To deploy", "termino_B": "Desplegar"}, {"termino_A": "To debug", "termino_B": "Depurar"}, {"termino_A": "To parse", "termino_B": "Analizar sintácticamente"} ] } }
    },
    {
        "model": "aprendizaje.ejercicio", "pk": 217,
        "fields": { "leccion": 105, "tipo_ejercicio": "Q", "enunciado": "What is the correct definition of 'Parameter' in programming?", "xp_recompensa": 10 }
    },
    {
        "model": "aprendizaje.retointeractivo", "pk": 217,
        "fields": { "ejercicio": 217, "tipo_reto": "OM", "configuracion": { "opciones": ["A variable passed into a function.", "A visual component on the screen.", "A type of database.", "An error in the code."], "respuesta_correcta": "A variable passed into a function." } }
    },

    # --- LECCIÓN 3: Error Handling & Debugging ---
    {
        "model": "aprendizaje.leccion", "pk": 106,
        "fields": { "curso": 9, "orden": 3, "titulo": "Error Handling & Debugging" }
    },
    {
        "model": "aprendizaje.ejercicio", "pk": 218,
        "fields": { "leccion": 106, "tipo_ejercicio": "Q", "enunciado": "Fill in the blank to complete the concept: We use a Try/______ block to handle errors gracefully.", "xp_recompensa": 15 }
    },
    {
        "model": "aprendizaje.retointeractivo", "pk": 218,
        "fields": { "ejercicio": 218, "tipo_reto": "RH", "configuracion": { "texto_antes": "We use a Try / ", "texto_despues": " block.", "respuesta_correcta": "Catch" } }
    },
    {
        "model": "aprendizaje.ejercicio", "pk": 219,
        "fields": { "leccion": 106, "tipo_ejercicio": "Q", "enunciado": "Order the logical sequence of troubleshooting a bug.", "xp_recompensa": 20 }
    },
    {
        "model": "aprendizaje.retointeractivo", "pk": 219,
        "fields": { "ejercicio": 219, "tipo_reto": "OT", "configuracion": { "elementos_ordenados": [ "1. Reproduce the bug", "2. Analyze the stack trace", "3. Isolate the problematic code", "4. Apply a fix and test again" ] } }
    }
]

def inyectar_datos():
    if not os.path.exists(archivo_json):
        print(f"❌ No se encontró el archivo {archivo_json}.")
        return

    try:
        # Leemos el archivo en UTF-8
        with open(archivo_json, 'r', encoding='utf-8') as file:
            datos_actuales = json.load(file)
            
        # Agregamos los nuevos datos
        datos_actuales.extend(nuevos_datos)

        # Escribimos de vuelta con el formato perfecto
        with open(archivo_json, 'w', encoding='utf-8') as file:
            json.dump(datos_actuales, file, indent=4, ensure_ascii=False)

        print(f"✅ ¡Éxito! Se inyectaron 20 nuevos registros (Lecciones, Ejercicios y Retos) a {archivo_json}.")
        print("Ejecuta en tu terminal: python manage.py loaddata datos_iniciales.json")
        
    except Exception as e:
        print(f"❌ Ocurrió un error: {e}")

if __name__ == "__main__":
    inyectar_datos()