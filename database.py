import os
import pymongo
from dotenv import load_dotenv

load_dotenv()

def obtener_coleccion(nombre_coleccion):
    """Función auxiliar para no repetir la conexión a Mongo en cada función."""
    uri = os.environ.get("MONGO_URI")
    cliente = pymongo.MongoClient(uri)
    return cliente["agente_vocacional"][nombre_coleccion]

def guardar_resultado(id_usuario, resultados):
    try:
        coleccion = obtener_coleccion("resultados")
        documento = {
            "usuario_id": id_usuario,
            "porcentajes": resultados
        }
        
        # Validar que no exista antes de insertar (Candado de seguridad)
        if not coleccion.find_one({"usuario_id": id_usuario}):
            coleccion.insert_one(documento)
        return True
    except Exception as e:
        print(f"Error de conexión a la base de datos al guardar: {e}")
        return False

def verificar_estado_usuario(id_ingresado):
    try:
        col_usuarios = obtener_coleccion("usuarios_permitidos")
        col_resultados = obtener_coleccion("resultados")
        
        # 1. Validar si existe en la lista blanca
        if not col_usuarios.find_one({"usuario": id_ingresado}):
            return "no_registrado"
            
        # 2. Validar si ya consumió su intento
        if col_resultados.find_one({"usuario_id": id_ingresado}):
            return "ya_completado"
            
        return "permitido"
        
    except Exception as e:
        print(f"Error en validación de estado: {e}")
        return "error"
    
def cargar_carreras():
    try:
        coleccion = obtener_coleccion("carreras")
        # Trae el primer documento (que contiene todo tu JSON de carreras)
        documento = coleccion.find_one({})
        
        # Limpiamos el metadato interno de Mongo antes de enviarlo a la IA
        if documento and "_id" in documento:
            del documento["_id"]
            
        return documento
    except Exception as e:
        print(f"Error al cargar la base de datos de carreras: {e}")
        return {}