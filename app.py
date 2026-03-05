import streamlit as st
import os
import json
import csv # <-- Nueva importación
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# --- FUNCIONES DE PERSISTENCIA ---
def guardar_resultado(id_usuario, resultados):
    archivo_resultados = "resultados_test.json"
    data = {}
    
    if os.path.exists(archivo_resultados):
        try:
            with open(archivo_resultados, "r", encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = {}
            
    data[id_usuario] = resultados
    
    with open(archivo_resultados, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    return "Resultados guardados correctamente."

def usuario_es_valido(id_ingresado):
    try:
        with open('usuario.csv', mode='r', encoding='utf-8') as f:
            lector = csv.DictReader(f)
            for fila in lector:
                # 'usuario' es el nombre de la cabecera en tu CSV
                if fila['usuario'] == id_ingresado:
                    return True
        return False
    except FileNotFoundError:
        st.error("Error interno: Archivo de usuarios no encontrado.")
        return False

# --- CONFIGURACIÓN UI ---
st.set_page_config(page_title="Agente Vocacional", layout="centered")

# Inicializar variables de estado
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "test_completado" not in st.session_state:
    st.session_state.test_completado = False
if "resultados_finales" not in st.session_state:
    st.session_state.resultados_finales = {}

# ESTADO 1: Pantalla de Acceso
if not st.session_state.autenticado:
    st.title("Acceso al Sistema")
    user_id = st.text_input("Ingresa tu número de usuario (ID):")
    
    if st.button("Comenzar Test"):
        if user_id:
            if usuario_es_valido(user_id):
                st.session_state.user_id = user_id
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Acceso denegado. Número de usuario no registrado.")
        else:
            st.error("Por favor ingresa un ID válido.")
    st.stop()

# ESTADO 3: Pantalla de Resultados (Se evalúa antes del chat)
if st.session_state.test_completado:
    st.title("Test Vocacional Finalizado")
    st.success("Tus resultados han sido procesados y guardados de forma segura.")
    st.subheader(f"Resultados para el Usuario: {st.session_state.user_id}")
    
    # Mostrar los resultados de forma elegante usando métricas de Streamlit
    col1, col2, col3 = st.columns(3)
    columnas = [col1, col2, col3]
    
    for i, (carrera, porcentaje) in enumerate(st.session_state.resultados_finales.items()):
        if i < 3: # Asegurar que solo usemos las 3 columnas
            columnas[i].metric(label=carrera, value=porcentaje)
    
    st.write("---")
    # Un botón para limpiar la sesión y volver al inicio. Muy útil para pruebas.
    if st.button("Inicio"):
        st.session_state.clear()
        st.rerun()
        
    st.stop() # Detenemos la ejecución aquí para que no dibuje el chat

# ESTADO 2: Pantalla del Chat (Lógica del Agente)
st.title(f"Evaluación en curso - Usuario: {st.session_state.user_id}")

@st.cache_data
def cargar_datos():
    with open('PerfilEgreso.json', 'r', encoding='utf-8') as archivo:
        return json.load(archivo)

carreras_db = cargar_datos()

system_prompt = f"""
Eres un agente de orientación vocacional imparcial, astuto y directo. Tu objetivo es perfilar al usuario mediante una entrevista.

REGLAS ESTRICTAS DE OPSEC Y COMPORTAMIENTO:
1. CONFIDENCIALIDAD TOTAL: Jamás menciones que tienes una base de datos, un JSON o una lista predefinida de opciones. Para el usuario, tu conocimiento es natural e ilimitado.
2. NEUTRALIDAD ABSOLUTA: Durante la fase de preguntas, NO sugieras, no des pistas, ni menciones el nombre de ninguna carrera. Tu único trabajo ahora es extraer información pura (gustos, materias, formas de trabajar) sin influir en sus respuestas.
3. Haz preguntas UNA POR UNA. Mantén la conversación fluida y natural, no como un interrogatorio policial.
4. Analiza la información en silencio. Cruza sus respuestas con los perfiles que tienes asignados sin decírselo al usuario.
5. Cuando tengas suficiente información (al menos 3 o 4 respuestas con sustancia), DEJA DE PREGUNTAR.
6. si la carrera a la que se esta declinando el usuario es diferente a las que tienes en el json le puedes dicir a que carrera pertenece pero que no esta en la universidad
7. Al final, da una breve explicación de tu análisis y luego debes decir EXACTAMENTE la palabra "FINALIZADO" seguida de un objeto JSON con los resultados de su Top 3 y porcentajes. No agregues texto después del JSON.
Ejemplo de cierre: Según tu perfil, estas son tus mejores opciones... FINALIZADO {{"Licenciatura en Administracion": "85%", "Ingenieria de Software": "70%", "Ingenieria Civil": "60%"}}

Aquí está la información clasificada de carreras para tu análisis interno: {json.dumps(carreras_db)}
"""

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
            completion = client.chat.completions.create(
                messages=st.session_state.mensajes,
                model="llama-3.3-70b-versatile",
                temperature=0.2,
            )
            respuesta = completion.choices[0].message.content
            
            # Lógica de intercepción
            if "FINALIZADO" in respuesta:
                try:
                    # Extraer el JSON
                    datos_json_str = respuesta.split("FINALIZADO")[1].strip()
                    res_json = json.loads(datos_json_str)
                    
                    # Guardar en archivo local
                    guardar_resultado(st.session_state.user_id, res_json)
                    
                    # Cambiar estado de la UI
                    st.session_state.resultados_finales = res_json
                    st.session_state.test_completado = True
                    st.rerun() # Esto recarga la app y nos manda al ESTADO 3
                except Exception as e:
                    # Si el LLM formatea mal el JSON, mostramos la respuesta normal como control de fallos
                    texto_visible = respuesta.replace("FINALIZADO", "")
                    st.markdown(texto_visible)
            else:
                st.markdown(respuesta)
    
    # Solo guardamos el mensaje en el historial si no ha finalizado
    if not st.session_state.test_completado:
        st.session_state.mensajes.append({"role": "assistant", "content": respuesta})