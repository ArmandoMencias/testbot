import streamlit as st
import os
import json
from dotenv import load_dotenv
from database import guardar_resultado, verificar_estado_usuario, cargar_carreras
from prompts import obtener_system_prompt
from motor_ia import obtener_respuesta_ia

load_dotenv() 

def verificar_disponibilidad_uv(nombre_ia, bd_carreras):
    """Verifica si la carrera sugerida está en el JSON de Mongo."""
    nombre_limpio = nombre_ia.lower().strip()
    
    # Recorremos todas las facultades y sus carreras
    for facultad, lista_carreras in bd_carreras.items():
        if isinstance(lista_carreras, list):
            for item in lista_carreras:
                carrera_uv = item.get("carrera", "").lower().strip()
                # Flexibilidad: revisa si una palabra está contenida en la otra
                if carrera_uv in nombre_limpio or nombre_limpio in carrera_uv:
                    return True
    return False

# --- CONFIGURACIÓN UI ---
st.set_page_config(page_title="Agente Vocacional", layout="centered")

# Moviendo la carga de datos a la parte superior para alcance global
carreras_db = cargar_carreras()

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "test_completado" not in st.session_state:
    st.session_state.test_completado = False
if "resultados_finales" not in st.session_state:
    st.session_state.resultados_finales = {}

# --- ESTADO 1: Pantalla de Acceso ---
if not st.session_state.autenticado:
    st.title("Acceso al Sistema")
    user_id = st.text_input("Ingresa tu número de usuario (ID):")
    
    if st.button("Comenzar Test"):
        if user_id:
            estado = verificar_estado_usuario(user_id) 
            
            if estado == "permitido":
                st.session_state.user_id = user_id
                st.session_state.autenticado = True
                st.rerun()
            elif estado == "ya_completado":
                st.warning("Acceso denegado. Este número de usuario ya completó el test vocacional.")
            elif estado == "no_registrado":
                st.error("Acceso denegado. Número de usuario no registrado en el sistema.")
            else:
                st.error("Error de conexión con el servidor. Intenta más tarde.")
        else:
            st.error("Por favor ingresa un ID válido.")
    st.stop()

# --- ESTADO 3: Pantalla de Resultados ---
# --- ESTADO 3: Pantalla de Resultados ---
if st.session_state.test_completado:
    st.title("Test Vocacional Finalizado")
    st.success("Tus resultados han sido procesados y guardados de forma segura.")
    st.subheader(f"Resultados para el Usuario: {st.session_state.user_id}")
    
    col1, col2, col3 = st.columns(3)
    columnas = [col1, col2, col3]
    
    # Ahora desempaquetamos en (carrera, datos) porque el valor es un diccionario
    for i, (carrera, datos) in enumerate(st.session_state.resultados_finales.items()):
        if i < 3: 
            with columnas[i]:
                # Extraemos el porcentaje del sub-diccionario
                st.metric(label=carrera, value=datos["porcentaje"])
                
                # Ya no calculamos la disponibilidad, solo leemos el valor booleano
                if datos["disponible_en_uv"]:
                    st.success("Disponible en UV de la región")
                else:
                    st.warning("No disponible en UV de la región")
    
    st.write("---")
    if st.button("Inicio"):
        st.session_state.clear()
        st.rerun()
        
    st.stop()

## --- ESTADO 2: Pantalla del Chat ---
st.title(f"Evaluación en curso - Usuario: {st.session_state.user_id}")

system_prompt = obtener_system_prompt(carreras_db)

if "mensajes" not in st.session_state:
    st.session_state.mensajes = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": f"Hola, soy tu guía. Para empezar, ¿qué materias te apasionan más?"}
    ]

for mensaje in st.session_state.mensajes:
    if mensaje["role"] != "system":
        with st.chat_message(mensaje["role"]):
            st.markdown(mensaje["content"])

if prompt := st.chat_input("Escribe aquí..."):
    st.session_state.mensajes.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analizando..."):
            # Llamada limpia al módulo externo
            respuesta = obtener_respuesta_ia(st.session_state.mensajes)
            
            if "FINALIZADO" in respuesta:
                try:
                    datos_json_str = respuesta.split("FINALIZADO")[1].strip()
                    res_json = json.loads(datos_json_str)
                    
                    # --- PROCESO DE ENRIQUECIMIENTO DE DATOS ---
                    resultados_enriquecidos = {}
                    for carrera, porcentaje in res_json.items():
                        disponible = verificar_disponibilidad_uv(carrera, carreras_db)
                        resultados_enriquecidos[carrera] = {
                            "porcentaje": porcentaje,
                            "disponible_en_uv": disponible
                        }
                    
                    # Guardamos el objeto ya enriquecido en Mongo
                    guardar_resultado(st.session_state.user_id, resultados_enriquecidos)
                    
                    st.session_state.resultados_finales = resultados_enriquecidos
                    st.session_state.test_completado = True
                    st.rerun() 
                except Exception as e:
                    texto_visible = respuesta.replace("FINALIZADO", "")
                    st.markdown(texto_visible)
            else:
                st.markdown(respuesta)
    
    if not st.session_state.test_completado:
        st.session_state.mensajes.append({"role": "assistant", "content": respuesta})