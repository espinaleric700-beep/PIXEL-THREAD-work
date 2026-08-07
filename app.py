import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Configuración de página optimizada para móvil
st.set_page_config(page_title="Pixel Nexus", layout="centered")

# --- ESTILOS FUTURISTAS (DARK CYBERPUNK) ---
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
        border-radius: 4px;
        padding: 0.5rem;
    }
    h1, h2, h3 {
        color: #00ffcc !important;
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

# --- LÓGICA DE PERSISTENCIA DE SESIÓN ---
if "user" not in st.session_state:
    st.session_state.user = "Usuario"

st.title("🧵 Pixel Nexus")
user = st.text_input("Tu ID o Nombre de Usuario", value=st.session_state.user)
if st.button("Conectar al Portal"):
    st.session_state.user = user
    st.rerun()

# --- FORMULARIO OPTIMIZADO PARA MÓVIL ---
with st.form("nuevo_pedido", clear_on_submit=True):
    st.subheader("➕ Nuevo Proyecto")
    nombre = st.text_input("Nombre del Logo / Proyecto")
    tipo = st.selectbox("Soporte", ["Tela", "Gorra"])
    submit = st.form_submit_button("ENVIAR A NEXUS")
    
    if submit:
        if nombre:
            data = {
                "cliente": st.session_state.user,
                "nombre": nombre,
                "tipo": tipo,
                "estado": "Pendiente",
                "fecha": datetime.now().isoformat()
            }
            db.collection("logos").add(data)
            st.success("¡Guardado correctamente en la red!")
        else:
            st.warning("Por favor ingresa el nombre del proyecto.")

# --- HISTORIAL DE PEDIDOS ---
st.markdown("---")
st.subheader("📋 Historial de Proyectos")
try:
    docs = db.collection("logos").where("cliente", "==", st.session_state.user).stream()
    hay_datos = False
    for d in docs:
        hay_datos = True
        p = d.to_dict()
        st.info(f"**Proyecto:** {p.get('nombre')} | **Soporte:** {p.get('tipo')} | **Estado:** {p.get('estado')}")
    
    if not hay_datos:
        st.info("No tienes proyectos registrados bajo este usuario.")
except Exception as e:
    st.error(f"No se pudieron cargar los datos: {e}")
