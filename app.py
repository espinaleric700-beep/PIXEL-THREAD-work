import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import base64
from streamlit_autorefresh import st_autorefresh

# Configuración de página optimizada
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
    if user_input != st.session_state.user: actualizar_url_y_estado("Cliente", user_input)

    if not st.session_state.user.strip():
        st.info("👆 Ingresa tu ID para acceder.")
    else:
        user_doc_ref = db.collection("usuarios_perfil").document(st.session_state.user.strip().lower())
        user_doc = user_doc_ref.get()
        
        if not user_doc.exists:
            st.error(f"❌ El usuario **{st.session_state.user}** no está registrado.")
        else:
            datos = user_doc.to_dict()
            logo_b64 = datos.get("logo_usuario", "")
            
            # --- ENCABEZADO PERSONALIZADO ---
            col1, col2 = st.columns([1, 4])
            if logo_b64: 
                col1.image(base64.b64decode(logo_b64), width=80)
            col2.subheader(f"Bienvenido, {datos.get('nombre_usuario')}")
            st.markdown("---")

            with st.expander("➕ Enviar Nuevo Pedido"):
                with st.form("form_pedido", clear_on_submit=True):
                    nombre = st.text_input("Nombre del Proyecto")
                    archivo = st.file_uploader("Logo/Archivo", type=["png", "jpg", "dst", "pes"])
                    if st.form_submit_button("Enviar"):
                        img_b64 = base64.b64encode(archivo.getvalue()).decode() if archivo else ""
                        db.collection("pedidos_bordado").add({
                            "cliente": st.session_state.user.strip(),
                            "nombre_proyecto": nombre,
                            "archivo_nombre": archivo.name if archivo else "Sin archivo",
                            "archivo_data": img_b64,
                            "estado": "Pendiente",
                            "timestamp": datetime.now()
                        })
                        st.rerun()

            st.subheader("📋 Mis Pedidos")
            # (Lógica de visualización de pedidos...)
            pedidos = db.collection("pedidos_bordado").where("cliente", "==", st.session_state.user.strip().lower()).stream()
            for p in pedidos:
                data = p.to_dict()
                st.write(f"**Proyecto:** {data.get('nombre_proyecto')} | **Estado:** {data.get('estado')}")
                if data.get('archivo_data'):
                    st.image(base64.b64decode(data['archivo_data']), width=100)
                st.markdown("---")

# =========================================================
# 2. PANEL DE ADMINISTRADOR
# =========================================================
else:
    st.title("🛠️ Panel de Administración")
    
    with st.expander("➕ Registrar Nuevo Cliente"):
        with st.form("form_admin_reg"):
            n_id = st.text_input("ID del nuevo cliente")
            n_logo = st.file_uploader("Logo (Opcional)", type=["png", "jpg"])
            if st.form_submit_button("Registrar"):
                l_b64 = base64.b64encode(n_logo.getvalue()).decode() if n_logo else ""
                db.collection("usuarios_perfil").document(n_id.lower()).set({
                    "nombre_usuario": n_id, "logo_usuario": l_b64, "creado": datetime.now()
                })
                st.success("Registrado.")
                st.rerun()

    st.subheader("📋 Gestión de Pedidos")
    docs = db.collection("pedidos_bordado").order_by("timestamp").stream()
    for doc in docs:
        p = doc.to_dict()
        st.write(f"Cliente: {p.get('cliente')} | Proyecto: {p.get('nombre_proyecto')}")
        if st.button(f"Eliminar {doc.id}"):
            db.collection("pedidos_bordado").document(doc.id).delete()
            st.rerun()
