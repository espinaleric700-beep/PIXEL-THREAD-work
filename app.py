import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import base64
from streamlit_autorefresh import st_autorefresh

# Configuración de página
st.set_page_config(page_title="Pixel Thread - Portal Interactivo", layout="centered")
st_autorefresh(interval=5000, limit=1000, key="auto_refrescar_cliente")

# --- ESTILOS ---
st.markdown("""
<style>
    .stApp { background: radial-gradient(circle at center, #1a0033 0%, #000000 100%); color: #00ffcc; }
    div.stButton > button { width: 100%; background-color: #00ffcc; color: black; font-weight: bold; border: none; border-radius: 6px; padding: 0.6rem; }
    h1, h2, h3 { color: #00ffcc !important; }
</style>
""", unsafe_allow_html=True)

# --- CONEXIÓN FIREBASE ---
@st.cache_resource
def init_fb():
    if not firebase_admin._apps:
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_fb()

# --- NAVEGACIÓN ---
params = st.query_params
st.session_state.modo_vista = params.get("seccion", "Cliente")
st.session_state.user = params.get("user", "")

def actualizar_url_y_estado(nueva_vista, nuevo_usuario):
    st.query_params["seccion"] = nueva_vista
    st.query_params["user"] = nuevo_usuario
    st.rerun()

col_nav1, col_nav2 = st.columns(2)
if col_nav1.button("👤 Panel de Cliente"): actualizar_url_y_estado("Cliente", st.session_state.user)
if col_nav2.button("🛠️ Panel Admin"): actualizar_url_y_estado("Admin", st.session_state.user)

st.markdown("---")

# =========================================================
# 1. PANEL DE CLIENTE
# =========================================================
if st.session_state.modo_vista == "Cliente":
    st.title("🧵 Pixel Thread - Portal de Cliente")
    user_input = st.text_input("Ingresa tu ID de Usuario:", value=st.session_state.user)
    
    if user_input != st.session_state.user:
        actualizar_url_y_estado("Cliente", user_input)

    if not st.session_state.user.strip():
        st.info("👆 Ingresa tu ID para acceder.")
    else:
        user_doc_ref = db.collection("usuarios_perfil").document(st.session_state.user.strip().lower())
        user_doc = user_doc_ref.get()
        
        if not user_doc.exists:
            st.error(f"❌ El usuario **{st.session_state.user}** no está registrado. Por favor, contacta al administrador.")
        else:
            datos_usuario = user_doc.to_dict()
            logo_perfil_b64 = datos_usuario.get("logo_usuario", "")
            
            c1, c2 = st.columns([3, 1])
            c1.success(f"Bienvenido: **{st.session_state.user}**")
            if logo_perfil_b64: c2.image(base64.b64decode(logo_perfil_b64), width=60)

            with st.expander("➕ Enviar Nuevo Pedido"):
                with st.form("form_pedido", clear_on_submit=True):
                    nombre_proyecto = st.text_input("Nombre del Proyecto")
                    archivo = st.file_uploader("Logo/Archivo", type=["png", "jpg", "dst", "pes"])
                    submit = st.form_submit_button("Enviar")
                    if submit and nombre_proyecto:
                        img_b64 = base64.b64encode(archivo.getvalue()).decode() if archivo else ""
                        db.collection("pedidos_bordado").add({
                            "cliente": st.session_state.user.strip(),
                            "nombre_proyecto": nombre_proyecto,
                            "archivo_data": img_b64,
                            "estado": "Pendiente",
                            "timestamp": datetime.now()
                        })
                        st.rerun()

# =========================================================
# 2. PANEL DE ADMINISTRADOR
# =========================================================
else:
    st.title("🛠️ Panel de Administración")
    
    # Módulo de Registro de Nuevos Clientes
    st.subheader("➕ Registro de Nuevos Clientes")
    with st.expander("Registrar nuevo usuario en el sistema"):
        nuevo_user_id = st.text_input("ID del nuevo usuario")
        logo_file = st.file_uploader("Logo del usuario (Opcional)", type=["png", "jpg"])
        if st.button("Registrar en Base de Datos"):
            if nuevo_user_id:
                l_b64 = base64.b64encode(logo_file.getvalue()).decode() if logo_file else ""
                db.collection("usuarios_perfil").document(nuevo_user_id.lower()).set({
                    "nombre_usuario": nuevo_user_id,
                    "logo_usuario": l_b64,
                    "creado": datetime.now()
                })
                st.success(f"Usuario {nuevo_user_id} registrado.")
            else:
                st.error("Ingresa un ID.")

    st.markdown("---")
    st.subheader("📋 Gestión de Pedidos")
    # (El resto de la lógica de gestión de pedidos sigue igual...)
    docs = db.collection("pedidos_bordado").order_by("timestamp").stream()
    for doc in docs:
        p = doc.to_dict()
        st.write(f"ID: {p.get('id', 'N/A')} | Cliente: {p.get('cliente')} | Estado: {p.get('estado')}")
        if st.button(f"Eliminar {doc.id}"):
            db.collection("pedidos_bordado").document(doc.id).delete()
            st.rerun()
