import streamlit as st
import firebase_admin
from firebase_admin import credentials, storage, firestore

# Configuración de la página en Streamlit
st.set_page_config(page_title="Gestión de Pedidos - Bordado", page_icon="🧵", layout="wide")

# Inicializar Firebase Admin usando st.secrets
if not firebase_admin._apps:
    cred_dict = dict(st.secrets["firebase"])
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'pixel-thread-db.appspot.com'
    })

db = firestore.client()

st.title("🧵 Gestión de Pedidos de Bordado")

# --- PANEL DE ADMINISTRACIÓN (SIDEBAR) ---
st.sidebar.header("Panel de Administración")
modo_admin = st.sidebar.checkbox("Activar modo administrador")

if modo_admin:
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Opciones de Administrador")
    
    if st.sidebar.button("🗑️ Eliminar Todo el Historial", type="primary"):
        confirmacion = st.sidebar.checkbox("Confirmo que deseo borrar todo.")
        if confirmacion:
            try:
                # 1. Borrar documentos de Firestore
                docs = db.collection('pedidos_bordado').stream()
                for doc in docs:
                    doc.reference.delete()
                
                # 2. Borrar archivos de Storage
                bucket = storage.bucket()
                blobs = bucket.list_blobs(prefix="pedidos_archivos/")
                for blob in blobs:
                    blob.delete()
                    
                st.sidebar.success("¡Historial eliminado por completo!")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Error: {e}")

# --- SECCIÓN 1: NUEVO PEDIDO ---
st.subheader("➕ Subir Nuevo Pedido")

col1, col2 = st.columns(2)

with col1:
    nombre_cliente = st.text_input("Nombre del Cliente")
    tipo_prenda = st.selectbox("Tipo de Prenda", ["Gorra", "Camisa / Polo", "Chaqueta", "Parche", "Otro"])
    cantidad = st.number_input("Cantidad de piezas", min_value=1, value=1)

with col2:
    medidas = st.text_input("Medidas del diseño (ej. 10x5 cm)")
    observaciones = st.text_area("Observaciones / Notas adicionales")
    archivo = st.file_uploader("Sube tu archivo de diseño", type=["dst", "pes", "jef", "png", "jpg"])

if st.button("🚀 SUBIR Y COMPLETAR", type="primary"):
    if archivo is not None and nombre_cliente.strip() != "":
        try:
            with st.spinner("Subiendo archivo y guardando pedido..."):
                bucket = storage.bucket()
                blob = bucket.blob(f"pedidos_archivos/{archivo.name}")
                
                # Subir archivo binario
                blob.upload_from_string(archivo.getvalue(), content_type=archivo.type)
                blob.make_public()
                download_url = blob.public_url

                # Guardar todos los datos en Firestore
                pedido_data = {
                    "nombre_cliente": nombre_cliente,
                    "tipo_prenda": tipo_prenda,
                    "cantidad": cantidad,
                    "medidas": medidas,
                    "observaciones": observaciones,
                    "archivoUrl": download_url,
                    "archivoNombre": archivo.name,
                    "fechaSubida": firestore.SERVER_TIMESTAMP
                }
                
                db.collection('pedidos_bordado').add(pedido_data)

            st.success("¡Pedido registrado y archivo guardado con éxito!")
            st.rerun()

        except Exception as e:
            st.error(f"Error al procesar el pedido: {e}")
    else:
        st.warning("Por favor, completa al menos el 'Nombre del Cliente' y selecciona un 'archivo'.")

# --- SECCIÓN 2: HISTORIAL DE PEDIDOS REGISTRADOS ---
st.markdown("---")
st.subheader("📋 Historial de Pedidos en la Base de Datos")

try:
    pedidos_ref = db.collection('pedidos_bordado').order_by('fechaSubida', direction=firestore.Query.DESCENDING).stream()
    
    hay_pedidos = False
    for doc in pedidos_ref:
        hay_pedidos = True
        p = doc.to_dict()
        
        with st.expander(f"Cliente: {p.get('nombre_cliente', 'Sin nombre')} — Prenda: {p.get('tipo_prenda', 'N/A')} (Cant: {p.get('cantidad', 1)})"):
            st.write(f"**Medidas:** {p.get('medidas', 'No especificadas')}")
            st.write(f"**Observaciones:** {p.get('observaciones', 'Ninguna')}")
            st.write(f"**Archivo:** {p.get('archivoNombre', 'Desconocido')}")
            
            url_archivo = p.get('archivoUrl')
            if url_archivo:
                st.markdown(f"[📥 Descargar / Ver Archivo de Diseño]({url_archivo})")
                
            # Botón individual para borrar un pedido específico
            if st.button(f"Eliminar este pedido", key=doc.id):
                db.collection('pedidos_bordado').document(doc.id).delete()
                st.success("Pedido eliminado correctamente.")
                st.rerun()

    if not hay_pedidos:
        st.info("No hay pedidos registrados en este momento.")

except Exception as e:
    st.info("Configurando la conexión o la base de datos está vacía. Sube tu primer pedido arriba.")
