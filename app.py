import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA EN ANCHO COMPLETO ---
st.set_page_config(page_title="Pixel Thread", layout="wide")

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
    st.session_state.user = "Pixel2580"

# --- ENCABEZADO PRINCIPAL ---
st.title("⚡ PIXEL THREAD")

# Botones de navegación superior estilo interfaz original
col_btn1, col_btn2, col_space = st.columns([1, 1, 4])
with col_btn1:
    btn_cliente = st.button("👤 PANEL CLIENTE")
with col_btn2:
    btn_admin = st.button("🛠️ PANEL ADMIN")

st.markdown("---")

# ID de usuario / Conexión rápida
user = st.text_input("Tu ID", value=st.session_state.user)
if st.button("Conectar"):
    st.session_state.user = user
    st.rerun()

st.markdown("---")

# --- PANEL DE ADMINISTRACIÓN Y FORMULARIO DE REGISTRO ---
st.subheader("🛠️ PANEL DE ADMINISTRACIÓN")

with st.form("nuevo_cliente_form", clear_on_submit=True):
    st.markdown("➕ Registrar Nuevo Cliente / Pedido")
    nombre_proyecto = st.text_input("Nombre del Proyecto / Producto")
    tipo_pedido = st.selectbox("Tipo", ["VARIOS", "Tela", "Gorra"])
    submit = st.form_submit_button("Guardar en el sistema")

if submit and nombre_proyecto:
    data = {
        "cliente": user, 
        "nombre": nombre_proyecto, 
        "tipo": tipo_pedido, 
        "estado": "Pendiente",
        "fecha": datetime.now().isoformat()
    }
    db.collection("logos").add(data)
    st.success("¡Registro completado con éxito!")

st.markdown("---")

# --- GESTIÓN DE PEDIDOS ENTRANTES ---
st.subheader("📋 GESTIÓN DE PEDIDOS ENTRANTES")

docs = db.collection("logos").stream()
for d in docs:
    p = d.to_dict()
    with st.container():
        st.markdown(f"👤 **{p.get('cliente', 'N/A')}** — ⏳ **{p.get('tipo', 'N/A')}**")
        st.caption(f"ID de Pedido: {d.id} | Estado: {p.get('estado', 'Pendiente')}")
        st.text(f"Producto: {p.get('nombre', 'N/A')} | Ubicación: N/A | Estilo: N/A")
        st.markdown("---")
