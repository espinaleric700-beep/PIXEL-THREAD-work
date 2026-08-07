import streamlit as st
import firebase_admin
from firebase_admin import credentials, storage, firestore

# Inicializar Firebase Admin usando st.secrets
if not firebase_admin._apps:
    cred_dict = dict(st.secrets["firebase"])
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'pixel-thread-db.appspot.com'
    })

db = firestore.client()

st.title("🚀 Gestión de Pedidos de Bordado")

# --- PANEL DE ADMINISTRACIÓN ---
st.sidebar.header("Panel de Administración")
modo_admin = st.sidebar.checkbox("Activar modo administrador")

if modo_admin:
    st.markdown("---")
    st.subheader("⚙️ Opciones de Administrador")
    
    st.warning("⚠️ Zona de peligro: Las acciones aquí pueden eliminar datos de forma permanente.")
    
    # Botón para eliminar el historial
    if st.button("🗑️ Eliminar Todo el Historial de Firebase", type="primary"):
        confirmacion = st.checkbox("Confirmo que deseo borrar todos los pedidos y archivos almacenados.")
        
        if confirmacion:
            try:
                with st.spinner("Eliminando registros y archivos..."):
                    # 1. Eliminar documentos de la colección 'pedidos_bordado' en Firestore
                    pedidos_ref = db.collection('pedidos_bordado')
                    docs = pedidos_ref.stream()
                    
                    contador_docs = 0
                    for doc in docs:
                        # Opcional: Si deseas eliminar también el archivo físico de Storage usando la URL guardada:
                        # (Aquí puedes agregar la lógica de Storage si almacenas la ruta exacta)
                        doc.reference.delete()
                        contador_docs += 1
                        
                    # 2. Opcional: Eliminar archivos de la carpeta en Storage
                    bucket = storage.bucket()
                    blobs = bucket.list_blobs(prefix="pedidos_archivos/")
                    contador_archivos = 0
                    for blob in blobs:
                        blob.delete()
                        contador_archivos += 1

                st.success(f"¡Historial eliminado con éxito! Se borraron {contador_docs} registros y {contador_archivos} archivos.")
            except Exception as e:
                st.error(f"Error al eliminar el historial: {e}")
        else:
            st.info("Por favor, marca la casilla de confirmación para habilitar el borrado.")

    st.markdown("---")

# --- INTERFAZ PRINCIPAL DE SUBIDA ---
st.subheader("Subir Nuevo Pedido")
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
                
                # Hacer el archivo público
                blob.make_public()
                download_url = blob.public_url

                # Guardar datos en Firestore
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
