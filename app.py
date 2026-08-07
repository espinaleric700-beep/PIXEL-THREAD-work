import streamlit as st
import firebase_admin
from firebase_admin import credentials, storage, firestore

# Inicializar Firebase Admin (asegúrate de cargar tus credenciales correctamente)
if not firebase_admin._apps:
    # Puedes usar st.secrets para almacenar tus credenciales de forma segura en Streamlit Cloud
    # cred = credentials.Certificate(dict(st.secrets["firebase"]))
    cred = credentials.Certificate("ruta/a/tus/credenciales.json")
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'pixel-thread-db.appspot.com'
    })

db = firestore.client()

st.title("🚀 Subida de Pedidos de Bordado")

# Componente de Streamlit para subir archivos
archivo = st.file_uploader("Sube tu archivo de diseño", type=["dst", "pes", "jef", "png", "jpg"])

nombre_cliente = st.text_input("Nombre del Cliente")

if st.button("SUBIR Y COMPLETAR"):
    if archivo is not None:
        try:
            with st.spinner("Subiendo archivo a Firebase Storage..."):
                bucket = storage.bucket()
                
                # Crear ruta en el Storage
                blob = bucket.blob(f"pedidos_archivos/{archivo.name}")
                
                # Subir el archivo desde los bytes del uploader de Streamlit
                blob.upload_from_string(
                    archivo.getvalue(),
                    content_type=archivo.type
                )
                
                # Hacer el archivo público o generar URL
                blob.make_public()
                download_url = blob.public_url

                # Guardar datos en Firestore (evitando el límite de 1MB)
                pedido_data = {
                    "nombre_cliente": nombre_cliente,
                    "archivoUrl": download_url,
                    "archivoNombre": archivo.name,
                    "fechaSubida": firestore.SERVER_TIMESTAMP
                }
                
                db.collection('pedidos_bordado').add(pedido_data)

            st.success("¡Pedido y archivo subidos con éxito!")
            st.markdown(f"[Ver archivo subido]({download_url})")

        except Exception as e:
            st.error(f"Error al subir: {e}")
    else:
        st.warning("Por favor, selecciona un archivo antes de continuar.")
