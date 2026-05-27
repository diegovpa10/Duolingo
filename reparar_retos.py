import json
import random

archivo = 'datos_iniciales.json'

def reparar_json():
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            datos = json.load(f)
    except UnicodeDecodeError:
        with open(archivo, 'r', encoding='latin-1') as f:
            datos = json.load(f)

    contador_reparaciones = 0

    for item in datos:
        if item.get("model") == "aprendizaje.retointeractivo":
            config = item.get("fields", {}).get("configuracion", {})
            tipo = item.get("fields", {}).get("tipo_reto")

            reparado = False

            # Reparar Rellenar Huecos (RH)
            if tipo == "RH" and "texto_antes" in config:
                config["texto_base"] = f"{config.pop('texto_antes')}[hueco]{config.pop('texto_despues')}"
                reparado = True

            # Reparar Ordenar Texto (OT)
            elif tipo == "OT" and "elementos_ordenados" in config:
                ordenados = config.pop("elementos_ordenados")
                config["orden_correcto"] = list(ordenados)
                desordenados = list(ordenados)
                random.shuffle(desordenados)
                config["elementos_desordenados"] = desordenados
                reparado = True

            # Reparar Enlazar Palabras (EP)
            elif tipo == "EP" and "pares" in config:
                pares = config.pop("pares")
                config["parejas"] = {p["termino_A"]: p["termino_B"] for p in pares}
                reparado = True
                
            # Reparar Opción Múltiple (OM)
            elif tipo == "OM" and "respuesta_correcta" in config and "indice_correcto" not in config:
                resp = config.pop("respuesta_correcta")
                try:
                    config["indice_correcto"] = config["opciones"].index(resp)
                except ValueError:
                    config["indice_correcto"] = 0
                reparado = True

            if reparado:
                contador_reparaciones += 1

    with open(archivo, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)
        
    print(f"Reparación finalizada: {contador_reparaciones} retos adaptados a la nueva estructura.")

if __name__ == "__main__":
    reparar_json()