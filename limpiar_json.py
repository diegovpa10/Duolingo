import json

archivo = 'datos_iniciales.json'

def limpiar_lecciones():
    try:
        # Tu archivo ya debería estar en utf-8 gracias al script anterior
        with open(archivo, 'r', encoding='utf-8') as f:
            datos = json.load(f)
            
        contador = 0
        
        # Buscamos todas las lecciones y les borramos el campo "completada"
        for item in datos:
            if item.get("model") == "aprendizaje.leccion":
                if "completada" in item.get("fields", {}):
                    del item["fields"]["completada"]
                    contador += 1
                    
        # Guardamos el JSON limpio
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
            
        print(f"✅ ¡Limpieza exitosa! Se eliminó el campo fantasma 'completada' de {contador} lecciones.")
        print("Ahora sí, ejecuta: python manage.py loaddata datos_iniciales.json")
        
    except Exception as e:
        print(f"❌ Ocurrió un error: {e}")

if __name__ == "__main__":
    limpiar_lecciones()