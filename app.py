import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Pixel Thread | Pro", layout="centered")
st_autorefresh(interval=5000, limit=1000, key="auto_refrescar")

# --- CSS AVANZADO ---
st.markdown("""
<style>
    :root {
        --primary: #00ffcc;
        --bg-dark: #050505;
    }
    .stApp {
        background: radial-gradient(circle at 50% 50%, #1a0033 0%, #050505 100%);
        background-attachment: fixed;
    }
    .stApp::before {
        content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background-image: linear-gradient(rgba(0, 255, 204, 0.05) 1px, transparent 1px),
                          linear-gradient(90deg, rgba(0, 255, 204, 0.05) 1px, transparent 1px);
        background-size: 50px 50px; pointer-events: none; z-index: 0;
    }
    div[data-testid="stExpander"], div[data-testid="stVerticalBlock"] > div {
        background: rgba(10, 10, 15, 0.6) !important;
        border: 1px solid rgba(0, 255, 204, 0.2) !important;
        border-radius: 12px !important;
        backdrop-filter: blur(10px);
        padding: 15px;
    }
    div.stButton > button {
        background: transparent !important;
        color: var(--primary) !important;
        border: 1px solid var(--primary) !important;
        border-radius: 5px !important;
        transition: all 0.3s ease !important;
        text-transform: uppercase;
        font-weight: bold;
    }
    div.stButton > button:hover {
        background: var(--primary) !important;
        color: black !important;
        box-shadow: 0 0 20px var(--primary) !important;
        transform: translateY(-2px);
    }
    h1, h2, h3 { color: var(--primary) !important; text-transform: uppercase; letter-spacing: 2px; }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE FIREBASE ---
@st.cache_resource
def init_fb():
    if not firebase_admin._apps:
        cred_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_fb()

# --- GESTIÓN ROBUSTA DE ESTADOS Y URL ---
params = st.query_params

if "modo_vista" not in st.session_state:
    st.session_state.modo_vista = params.get("seccion", "Cliente")

if "user" not in st.session_state:
    st.session_state.user = params.get("user", "")

def actualizar_url(vista, user):
    st.session_state.modo_vista = vista
    st.session_state.user = user
    st.query_params.update({"seccion": vista, "user": user})
    st.rerun()

# --- INTERFAZ PRINCIPAL ---
st.title("⚡ PIXEL THREAD")

col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("👤 PANEL CLIENTE"): 
        actualizar_url("Cliente", st.session_state.user)
with col_nav2:
    if st.button("🛠️ PANEL ADMIN"): 
        actualizar_url("Admin", st.session_state.user)

st.markdown("<br>", unsafe_allow_html=True)

# --- CONTROL DE ACCESO A PERFILES ---
if st.session_state.modo_vista == "Cliente":
    st.subheader("Acceso a Perfil de Cliente")
    
    # Campo vinculado directamente al session_state para evitar pérdida de datos
    user_input = st.text_input("Identificación de Usuario / ID:", value=st.session_state.user)
    
    if user_input != st.session_state.user:
        st.session_state.user = user_input
        st.query_params.update({"user": user_input})

    if st.session_state.user:
        # Validación de existencia en base de datos para corregir el fallo de entrada
        user_ref = db.collection("clientes").document(st.session_state.user).get()
        
        if user_ref.exists:
            st.success(f"Sesión activa para el usuario: {st.session_state.user}")
            with st.expander("➕ NUEVO PEDIDO", expanded=False):
                st.write("Configura tu pedido de bordado aquí.")
                if st.button("🚀 ENVIAR A PRODUCCIÓN"):
                    st.success("Pedido procesado y enviado correctamente.")
            
            st.subheader("📋 ESTADO DE ORDENES")
            st.info("Mostrando historial de órdenes activas.")
        else:
            st.warning("⚠️ El usuario no se encuentra registrado en el sistema. Contacta al administrador para gestionar el alta.")
    else:
        st.info("Por favor, introduce tu identificación de usuario para acceder a tu perfil.")

else:
    st.header("PANEL DE CONTROL ADMINISTRATIVO")
    st.write("Gestión general de perfiles, validación de clientes y control de producción.")
    
    # Listado rápido de administración para control de accesos
    try:
        clientes_ref = db.collection("clientes").stream()
        clientes_ids = [doc.id for doc in clientes_ref]
        st.write(f"Clientes registrados en el sistema: {len(clientes_ids)}")
    except Exception as e:
        st.error(f"Error al conectar con la base de datos de perfiles: {e}")
