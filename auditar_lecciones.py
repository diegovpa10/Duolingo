import json
import os

def buscar_lecciones_vacias():
    archivo_json = 'datos_iniciales.json'
    
    if not os.path.exists(archivo_json):
        print(f"❌ No se encontró el archivo {archivo_json}.")
        return

    try:
        with open(archivo_json, 'r', encoding='utf-8') as f:
            datos = json.load(f)
    except UnicodeDecodeError:
        with open(archivo_json, 'r', encoding='latin-1') as f:
            datos = json.load(f)

    # 1. Guardar todas las lecciones en un diccionario {pk: titulo}
    lecciones = {item['pk']: item['fields']['titulo'] for item in datos if item['model'] == 'aprendizaje.leccion'}
    
    # 2. Guardar en un conjunto (set) los IDs de las lecciones que SÍ tienen ejercicios
    lecciones_con_ejercicio = set(item['fields']['leccion'] for item in datos if item['model'] == 'aprendizaje.ejercicio')

    # 3. Detectar las que no cruzaron
    lecciones_vacias = []
    for pk, titulo in lecciones.items():
        if pk not in lecciones_con_ejercicio:
            lecciones_vacias.append(f"ID {pk} - '{titulo}'")

    if lecciones_vacias:
        print("⚠️ Se encontraron las siguientes lecciones vacías (sin ejercicios asignados):")
        for vacia in lecciones_vacias:
            print(f" - {vacia}")
    else:
        print("✅ ¡Todo perfecto! Absolutamente todas tus lecciones tienen al menos un ejercicio.")

if __name__ == "__main__":
    buscar_lecciones_vacias()