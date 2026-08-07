import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
from datetime import datetime

# Configuración de página optimizada para móvil
st.set_page_config(page_title="Pixel Nexus", layout="centered")

# --- ESTILOS FUTURISTAS ---
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
if "user" not in st.session_state: st.session_state.user = "Usuario"

st.title("🧵 Pixel Nexus")
user = st.text_input("Tu ID", value=st.session_state.user)
if st.button("Conectar"):
    st.session_state.user = user
    st.rerun()

# --- FORMULARIO OPTIMIZADO ---
with st.form("nuevo_pedido", clear_on_submit=True):
    nombre = st.text_input("Nombre del Proyecto")
    tipo = st.selectbox("Tipo", ["Tela", "Gorra"])
    submit = st.form_submit_button("ENVIAR A NEXUS")
    
    if submit and nombre:
        data = {"cliente": user, "nombre": nombre, "tipo": tipo, "fecha": datetime.now().isoformat()}
        db.collection("logos").add(data)
        st.success("Guardado en la red.")

# --- HISTORIAL ---
st.subheader("Historial")
docs = db.collection("logos").where("cliente", "==", user).stream()
for d in docs:
    p = d.to_dict()
    st.info(f"{p['nombre']} - {p['tipo']}")
