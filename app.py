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

# Intervalo de auto-refresco optimizado a 60 segundos
st_autorefresh(interval=60000, limit=1000, key="auto_refrescar")

# --- CARGA DE IMAGEN DE FONDO LOCAL (fondo.jpg) ---
# Asegúrate de subir tu imagen renombrada como "fondo.jpg" al mismo repositorio de GitHub
try:
    with open("fondo.jpg", "rb") as image_file:
        encoded_bg = base64.b64encode(image_file.read()).decode()
    bg_style = f'background: linear-gradient(rgba(5, 5, 5, 0.85), rgba(5, 5, 5, 0.85)), url("data:image/jpeg;base64,{encoded_bg}");'
except FileNotFoundError:
    # Fondo alternativo por si la imagen aún no se sube a GitHub
    bg_style = 'background: linear-gradient(rgba(5, 5, 5, 0.85), rgba(5, 5, 5, 0.85)), url("https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1000&auto=format&fit=crop");'

# --- CSS FUTURISTA, BOTONES INTERACTIVOS Y ANIMACIONES ---
st.markdown(f"""
<style>
    :root {{ 
        --primary: #00ffcc; 
        --bg-dark: #050505; 
        --accent-glow: 0 0 15px rgba(0, 255, 204, 0.4);
    }}
    
    /* Fondo principal de la aplicación con tu imagen futurista */
    .stApp {{
        {bg_style}
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    
    /* Contenedores y Tarjetas con efecto Glassmorphism */
    div[data-testid="stExpander"], div[data-testid="stVerticalBlock"] > div {{
        background: rgba(10, 10, 15, 0.75) !important;
        border: 1px solid rgba(0, 255, 204, 0.3) !important;
        border-radius: 12px !important;
        backdrop-filter: blur(8px);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }}
    
    div[data-testid="stExpander"]:hover, div[data-testid="stVerticalBlock"] > div:hover {{
        border-color: var(--primary) !important;
        box-shadow: var(--accent-glow);
    }}
    
    /* Botones interactivos con movimiento y brillo neón */
    .stButton > button {{
        background: linear-gradient(135deg, #050505, #10101a) !important;
        color: var(--primary) !important;
        border: 1px solid var(--primary) !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        box-shadow: 0 0 8px rgba(0, 255, 204, 0.2);
        transition: all 0.3s ease-in-out !important;
    }}
    
    .stButton > button:hover {{
        background: var(--primary) !important;
        color: #000000 !important;
        transform: translateY(-2px) scale(1.02);
        box-shadow: 0 0 20px rgba(0, 255, 204, 0.6);
    }}
    
    /* Campos de texto futuristas */
    .stTextInput > div > div > input {{
        background-color: rgba(10, 10, 15, 0.8) !important;
        color: #ffffff !important;
        border: 1px solid rgba(0, 255, 204, 0.3) !important;
        border-radius: 8px !important;
    }}
    
    .stTextInput > div > div > input:focus {{
        border-color: var(--primary) !important;
        box-shadow: var(--accent-glow) !important;
    }}
    
    h1, h2, h3 {{ 
        color: var(--primary) !important; 
        text-shadow: 0 0 10px rgba(0,255,204,0.4); 
    }}
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

# --- CACHE DE CONSULTAS (Protege la cuota de Firebase) ---
@st.cache_data(ttl=60)
def obtener_pedidos_cached():
    docs = list(db.collection("pedidos_bordado").order_by("timestamp").stream())
    return [(doc.id, doc.to_dict()) for doc in docs]

# --- LÓGICA DE NAVEGACIÓN Y ESTADOS ---
if "modo_vista" not in st.session_state: st.session_state.modo_vista = "Cliente"
if "user" not in st.session_state: st.session_state.user = ""

# --- UI PRINCIPAL ---
st.title("⚡ PIXEL THREAD")

# Barra lateral para cambiar de vista (Opcional pero útil)
with st.sidebar:
    st.subheader("Navegación")
    if st.button("Cambiar a Vista Admin / Cliente"):
        st.session_state.modo_vista = "Admin" if st.session_state.modo_vista == "Cliente" else "Cliente"
        st.rerun()

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
            if mis_pedidos:
                for p in mis_pedidos:
                    st.write(f"✨ **Proyecto:** {p.get('nombre_proyecto')} | **Estado:** {p.get('estado')}")
            else:
                st.info("No se encontraron pedidos para este usuario.")
        except Exception as e:
            st.error("Límite de cuota alcanzado o error de conexión. Espera unos segundos.")
            
# --- PANEL ADMIN ---
elif st.session_state.modo_vista == "Admin":
    try:
        todos_los_pedidos = obtener_pedidos_cached()
        st.subheader("Panel de Admin")
        for id, p in todos_los_pedidos:
            st.write(f"👤 **Cliente:** {p.get('cliente')} | 🧵 **Proyecto:** {p.get('nombre_proyecto')}")
    except Exception as e:
    
        st.error("Límite de cuota alcanzado.")
