import streamlit as st
import os
import json
from dotenv import load_dotenv
from groq import Groq

# 1. Cargar variables de entorno e inicializar Groq
load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# 2. Configurar la página de Streamlit
st.set_page_config(page_title="Agente Vocacional", layout="centered")
st.title("Agente de Orientación Vocacional")

# 3. Función para cargar el JSON
@st.cache_data
def cargar_datos():
    with open('PerfilEgreso.json', 'r', encoding='utf-8') as archivo:
        return json.load(archivo)

carreras_db = cargar_datos()

# 4. Definir el System Prompt
system_prompt = f"""
Eres un agente de orientación vocacional astuto y directo. Tu objetivo es perfilar al usuario.

Reglas estrictas:
1. Haz preguntas al usuario UNA POR UNA para conocer sus gustos, materias favoritas y habilidades. No lances un interrogatorio policial.
2. Mantén la conversación fluida y natural.
3. Tienes la siguiente base de datos de carreras agrupadas por facultad en formato JSON: {json.dumps(carreras_db)}
4. Analiza en silencio las respuestas cruzándolas con los campos "valores_y_compromisos" y "competencias_clave".
5. REGLA DE FUERA DE RANGO: Si las respuestas del usuario apuntan indudablemente a una disciplina que NO existe en el JSON (por ejemplo, Medicina, Arquitectura, Artes), debes decírselo de frente con un mensaje similar a: "Tu perfil tiene una fuerte inclinación hacia [Nombre de la Carrera], pero lamentablemente no está disponible en las facultades que tengo registradas."
6. Tras aplicar la regla 5, intenta ofrecerle la opción u opciones del JSON que compartan más habilidades transversales con su perfil, explicando la relación. Si de plano no hay relación, díselo.
7. Cuando tengas suficiente información (al menos 3 o 4 respuestas sólidas), DEJA DE PREGUNTAR.
8. Si el perfil sí encaja con el JSON desde el principio, devuelve un Top 3 de carreras recomendadas, indicando Facultad, profesión, porcentaje de afinidad y el porqué del match.
"""

# 5. Inicializar la memoria de Streamlit (Session State)
if "mensajes" not in st.session_state:
    st.session_state.mensajes = [{"role": "system", "content": system_prompt}]
    # Agregamos un mensaje inicial falso del asistente para romper el hielo en la UI
    st.session_state.mensajes.append({"role": "assistant", "content": "Hola. Soy tu agente vocacional. Para empezar a perfilarte, cuéntame: ¿qué te gusta hacer en tu tiempo libre?"})

# 6. Mostrar el historial de mensajes en la interfaz (ocultando el system_prompt)
for mensaje in st.session_state.mensajes:
    if mensaje["role"] != "system":
        with st.chat_message(mensaje["role"]):
            st.markdown(mensaje["content"])

# 7. Capturar entrada del usuario
if prompt := st.chat_input("Escribe tu respuesta aquí..."):
    # Mostrar el mensaje del usuario
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Guardar en memoria
    st.session_state.mensajes.append({"role": "user", "content": prompt})

    # Llamar a Groq
    with st.chat_message("assistant"):
        with st.spinner("Analizando tu perfil..."):
            chat_completion = client.chat.completions.create(
                messages=st.session_state.mensajes,
                model="llama-3.3-70b-versatile",
                temperature=0.2,
            )
            respuesta = chat_completion.choices[0].message.content
            st.markdown(respuesta)
    
    # Guardar la respuesta del asistente en memoria
    st.session_state.mensajes.append({"role": "assistant", "content": respuesta})