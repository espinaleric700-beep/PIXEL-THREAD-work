import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA EN ANCHO COMPLETO ---
st.set_page_config(page_title="Pixel Nexus", layout="wide")

# --- ESTILOS FUTURISTAS Y ANCHO EXPANDIDO ---
st.markdown("""
<style>
    .block-container {
        max-width: 100% !important;
        padding-left: 2rem;
        padding-right: 2rem;
    }
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
    }
    .css-1544g2n { color: #00ffcc !important; }
</style>
""", unsafe_allow_html=True)

# --- CONEXIÓN FIREBASE ---
@st.cache_resource
def init_fb():
    if not firebase_admin._apps:
        cred = credentials.Certificate(json.loads(st.secrets["FIREBASE_CREDENTIALS"]))
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_fb()

# --- LÓGICA DE PERSISTENCIA ---
if "user" not in st.session_state: 
    st.session_state.user = "Usuario"

st.title("🧵 Pixel Thread / Pixel Nexus")

# --- INTERFAZ PRINCIPAL ---
user = st.text_input("Tu ID / Cliente", value=st.session_state.user)
if st.button("Conectar"):
    st.session_state.user = user
    st.rerun()

st.markdown("---")

# --- PANELES Y GESTIÓN DE PEDIDOS ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("⚡ Panel de Clientes")
    with st.form("nuevo_pedido", clear_on_submit=True):
        nombre = st.text_input("Nombre del Proyecto / Pedido")
        tipo = st.selectbox("Tipo de Diseño", ["Tela", "Gorra", "VARIOS"])
        submit = st.form_submit_button("Registrar Nuevo Cliente / Pedido")
       
    if submit and nombre:
        data = {
            "cliente": user, 
            "nombre": nombre, 
            "tipo": tipo, 
            "estado": "Pendiente",
            "fecha": datetime.now().isoformat()
        }
        db.collection("logos").add(data)
        st.success("¡Pedido guardado en la red con éxito!")

with col2:
    st.subheader("🛠️ Panel de Administración")
    st.info("Herramientas de control y supervisión activas.")

st.markdown("---")

# --- GESTIÓN DE PEDIDOS ENTRANTES E HISTORIAL ---
st.subheader("📋 Gestión de Pedidos Entrantes")

docs = db.collection("logos").stream()
for d in docs:
    p = d.to_dict()
    # Mostramos los pedidos registrados
    with st.container():
        st.markdown(f"**Usuario / Cliente:** {p.get('cliente', 'N/A')} — ⏳ **{p.get('tipo', 'N/A')}**")
        st.caption(f"ID de Pedido: {d.id} | Estado: {p.get('estado', 'Pendiente')}")
        st.text(f"Producto: {p.get('nombre', 'N/A')} | Ubicación: N/A | Estilo: N/A")
        st.markdown("---")
