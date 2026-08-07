import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import base64
import io
from PIL import Image
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Pixel Thread | Pro", layout="centered")

# Intervalo de auto-refresco optimizado a 60 segundos para cuidar la cuota
st_autorefresh(interval=60000, limit=1000, key="auto_refrescar")

# --- CSS ---
st.markdown("""
<style>
    :root { --primary: #00ffcc; --bg-dark: #050505; }
    .stApp { background: radial-gradient(circle at 50% 50%, #1a0033 0%, #050505 100%); background-attachment: fixed; }
    div[data-testid="stExpander"], div[data-testid="stVerticalBlock"] > div {
        background: rgba(10, 10, 15, 0.6) !important;
        border: 1px solid rgba(0, 255, 204, 0.2) !important;
        border-radius: 12px !important;
    }
    h1, h2, h3 { color: var(--primary) !important; }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
@st.cache_resource
def init_fb():
    if not firebase_admin._apps:
        cred_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_fb()

# --- CACHE DE CONSULTAS (Crucial para no agotar la cuota) ---
@st.cache_data(ttl=60)
def obtener_pedidos_cached():
    docs = list(db.collection("pedidos_bordado").order_by("timestamp").stream())
    return [(doc.id, doc.to_dict()) for doc in docs]

# --- LÓGICA DE NAVEGACIÓN Y ESTADOS ---
if "modo_vista" not in st.session_state: st.session_state.modo_vista = "Cliente"
if "user" not in st.session_state: st.session_state.user = ""

# --- UI PRINCIPAL ---
st.title("⚡ PIXEL THREAD")

# --- PANEL CLIENTE ---
if st.session_state.modo_vista == "Cliente":
    user_input = st.text_input("Usuario:", value=st.session_state.user)
    if user_input != st.session_state.user:
        st.session_state.user = user_input
        st.rerun()

    if st.session_state.user:
        try:
            todos_los_pedidos = obtener_pedidos_cached()
            mis_pedidos = [p for id, p in todos_los_pedidos if p.get("cliente", "").strip().lower() == st.session_state.user.strip().lower()]
            
            st.subheader(f"Pedidos de {st.session_state.user}")
            for p in mis_pedidos:
                st.write(f"Proyecto: {p.get('nombre_proyecto')} | Estado: {p.get('estado')}")
        except Exception as e:
            st.error("Límite de cuota alcanzado. Espera unos segundos.")
            
# --- PANEL ADMIN ---
elif st.session_state.modo_vista == "Admin":
    try:
        todos_los_pedidos = obtener_pedidos_cached()
        st.subheader("Panel de Admin")
        for id, p in todos_los_pedidos:
            st.write(f"Cliente: {p.get('cliente')} | Proyecto: {p.get('nombre_proyecto')}")
    except Exception as e:
        st.error("Límite de cuota alcanzado.")
