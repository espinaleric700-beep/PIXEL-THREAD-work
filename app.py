import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import base64

# Configuración de página optimizada para móvil
st.set_page_config(page_title="Pixel Thread - Portal Interactivo", layout="centered")

# --- ESTILOS FUTURISTAS Y COMPONENTES VISUALES ---
st.markdown("""
<style>
    .stApp {
        background: radial-gradient(circle at center, #1a0033 0%, #000000 100%);
        color: #00ffcc;
    }
    div.stButton > button {
        width: 100%;
        background-color: #00ffcc;
        color: black;
        font-weight: bold;
        border: none;
        border-radius: 6px;
        padding: 0.6rem;
        transition: 0.2s;
    }
    div.stButton > button:hover {
        opacity: 0.85;
    }
    h1, h2, h3 {
        color: #00ffcc !important;
    }
    .stTextInput input, .stSelectbox select {
        background-color: #0b0f19;
        color: white;
        border: 1px solid #00ffcc55;
    }
</style>
""", unsafe_allow_html=True)

# --- CONEXIÓN FIREBASE (SEGURO POR SECCIONES) ---
@st.cache_resource
def init_fb():
    if not firebase_admin._apps:
        cred_dict = {
            "type": st.secrets["firebase"]["type"],
            "project_id": st.secrets["firebase"]["project_id"],
            "private_key_id": st.secrets["firebase"]["private_key_id"],
            "private_key": st.secrets["firebase"]["private_key"],
            "client_email": st.secrets["firebase"]["client_email"],
            "client_id": st.secrets["firebase"]["client_id"],
            "auth_uri": st.secrets["firebase"]["auth_uri"],
            "token_uri": st.secrets["firebase"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"],
            "universe_domain": st.secrets["firebase"]["universe_domain"]
        }
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_fb()

# --- GESTIÓN DE ESTADOS (SESSION STATE) ---
if "user" not in st.session_state:
    st.session_state.user = "Cliente General"
if "modo_vista" not in st.session_state:
    st.session_state.modo_vista = "Cliente"

# Barra superior de navegación entre paneles
col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("👤 Panel de Cliente"):
        st.session_state.modo_vista = "Cliente"
        st.rerun()
with col_nav2:
    if st.button("🛠️ Panel Admin"):
        st.session_state.modo_vista = "Admin"
        st.rerun()

st.markdown("---")

# =========================================================
# 1. PANEL DE CLIENTE
# =========================================================
if st.session_state.modo_vista == "Cliente":
    st.title("🧵 Pixel Thread - Nuevo Pedido")
    
    # Identificador de usuario persistente
    user = st.text_input("Tu Nombre o ID de Usuario:", value=st.session_state.user)
    st.session_state.user = user

    with st.form("form_pedido_streamlit", clear_on_submit=True):
        nombre_proyecto = st.text_input("1. Nombre o Referencia del Proyecto")
        
        archivo_subido = st.file_uploader("2. Sube tu Logo (PNG, JPG, DST, PES)", type=["png", "jpg", "jpeg", "dst", "pes"])
        
        st.markdown("3. **Selecciona el Tipo de Producto:**")
        tipo_producto = st.radio("Producto:", ["GORRA", "TELA"], horizontal=True, label_visibility="collapsed")
        
        ubicacion = "N/A"
        estilo_frente = "N/A"
        
        # Lógica condicional interactiva si selecciona GORRA
        if tipo_producto == "GORRA":
            st.markdown("📍 **Ubicación en la Gorra:**")
            ubicacion = st.radio("Ubicación:", ["FRENTE", "TRASERO", "LATERAL"], horizontal=True, label_visibility="collapsed")
            
            # Sub-lógica condicional si selecciona FRENTE
            if ubicacion == "FRENTE":
                st.markdown("✨ **Estilo de Bordado (Frente):**")
                estilo_frente = st.radio("Estilo:", ["3D (Relieve)", "PLANO / FLAT"], horizontal=True, label_visibility="collapsed")

        submit_pedido = st.form_submit_button("🚀 ENVIAR PEDIDO A PRODUCCIÓN")
        
        if submit_pedido:
            if not nombre_proyecto:
                st.warning("⚠️ Debes ingresar el nombre del proyecto.")
            else:
                # Procesar archivo a base64 para guardarlo o referenciarlo
                img_base64 = ""
                file_name = "Sin archivo"
                if archivo_subido is not None:
                    file_name = archivo_subido.name
                    img_base64 = base64.b64encode(archivo_subido.getvalue()).decode("utf-8")

                data_pedido = {
                    "id": "PT-" + str(int(datetime.now().timestamp())),
                    "cliente": st.session_state.user,
                    "nombre_proyecto": nombre_proyecto,
                    "producto": tipo_producto,
                    "ubicacion": ubicacion,
                    "estilo": estilo_frente if ubicacion == "FRENTE" else "N/A",
                    "archivo_nombre": file_name,
                    "archivo_data": img_base64,
                    "estado": "Pendiente",
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                db.collection("pedidos_bordado").add(data_pedido)
                st.success("¡Pedido enviado y guardado correctamente en la base de datos!")

# =========================================================
# 2. PANEL DE ADMINISTRADOR
# =========================================================
else:
    st.title("🛠️ Panel de Administración")
    st.subheader("📋 Gestión de Pedidos Entrantes")

    try:
        docs = db.collection("pedidos_bordado").stream()
        contador = 0

        for doc in docs:
            contador += 1
            p = doc.to_dict()
            doc_id = doc.id

            with st.container():
                st.markdown(f"### 🆔 {p.get('id', 'S/ID')} - {p.get('nombre_proyecto')}")
                st.text(f"Cliente: {p.get('cliente')} | Fecha: {p.get('fecha')}")
                
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.markdown(f"**Producto:** {p.get('producto')}")
                    if p.get('producto') == 'GORRA':
                        st.markdown(f"**Ubicación:** {p.get('ubicacion')}")
                        if p.get('ubicacion') == 'FRENTE':
                            st.markdown(f"**Estilo:** {p.get('estilo')}")
                with col_info2:
                    st.markdown(f"**Archivo:** {p.get('archivo_nombre')}")
                    if p.get('archivo_data'):
                        st.download_button(
                            label="📥 Descargar Logo Adjunto",
                            data=base64.b64decode(p.get('archivo_data')),
                            file_name=p.get('archivo_nombre'),
                            mime="application/octet-stream",
                            key=f"dl_{doc_id}"
                        )

                # Selector de Estado en tiempo real
                estado_actual = p.get('estado', 'Pendiente')
                opciones_estado = ["Pendiente", "En Proceso", "Completado"]
                nuevo_estado = st.selectbox(
                    "Estado del Pedido",
                    opciones_estado,
                    index=opciones_estado.index(estado_actual) if estado_actual in opciones_estado else 0,
                    key=f"status_{doc_id}"
                )

                if nuevo_estado != estado_actual:
                    db.collection("pedidos_bordado").document(doc_id).update({"estado": nuevo_estado})
                    st.rerun()

                # Botón para eliminar pedido completado
                if st.button(f"🗑️ Eliminar Pedido {p.get('id')}", key=f"del_{doc_id}"):
                    db.collection("pedidos_bordado").document(doc_id).delete()
                    st.success("Pedido eliminado.")
                    st.rerun()

                st.markdown("---")

        if contador == 0:
            st.info("No hay pedidos registrados en el sistema.")

    except Exception as e:
        st.error(f"Error al conectar con la base de datos de Firebase: {e}")
