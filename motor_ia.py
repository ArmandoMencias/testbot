import os
from groq import Groq

# El cliente se inicializa aquí, encapsulando la credencial
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def obtener_respuesta_ia(mensajes_historial):
    """
    Envía el historial de la conversación al LLM y devuelve solo el texto de respuesta.
    Actúa como una caja negra para la interfaz web.
    """
    try:
        completion = client.chat.completions.create(
            messages=mensajes_historial,
            model="llama-3.3-70b-versatile",
            temperature=0.2,
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error de comunicación con la API de IA: {e}")
        return "Hubo un error al procesar tu respuesta. Por favor, intenta de nuevo."