import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import base64
import io
from PIL import Image
from streamlit_autorefresh import st_autorefresh

# Configuración de página
st.set_page_config(page_title="Pixel Thread - Portal Interactivo", layout="centered")
st_autorefresh(interval=5000, limit=1000, key="auto_refrescar")

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

# --- ESTADO ---
if "modo_vista" not in st.session_state: st.session_state.modo_vista = "Cliente"
if "user" not in st.session_state: st.session_state.user = ""
if "form_version" not in st.session_state: st.session_state.form_version = 0
if "mensaje_exito" not in st.session_state: st.session_state.mensaje_exito = ""

ADMINS_AUTORIZADOS = ["Pixel2580", "eric"]

# --- NAVEGACIÓN ---
col1, col2 = st.columns(2)
with col1:
    if st.button("👤 Panel Cliente"): st.session_state.modo_vista = "Cliente"; st.rerun()
with col2:
    if st.button("🛠️ Panel Admin"):
        if st.session_state.user in ADMINS_AUTORIZADOS: st.session_state.modo_vista = "Admin"; st.rerun()
        else: st.error("Acceso denegado")

st.markdown("---")

# =========================================================
# PANEL CLIENTE
# =========================================================
if st.session_state.modo_vista == "Cliente":
    user_input = st.text_input("Usuario:", value=st.session_state.user)
    st.session_state.user = user_input
    
    if st.session_state.mensaje_exito:
        st.success(st.session_state.mensaje_exito)
        st.session_state.mensaje_exito = ""

    fv = st.session_state.form_version
    with st.expander("➕ Nuevo Pedido"):
        nombre_proyecto = st.text_input("Nombre Proyecto", key=f"p_{fv}")
        archivos = st.file_uploader("Archivos", accept_multiple_files=True, key=f"a_{fv}")
        if st.button("ENVIAR", key=f"b_{fv}"):
            if nombre_proyecto and archivos:
                lista_arch = [{"nombre": a.name, "data": base64.b64encode(a.getvalue()).decode()} for a in archivos]
                db.collection("pedidos_bordado").add({
                    "cliente": st.session_state.user, "nombre_proyecto": nombre_proyecto,
                    "archivos": lista_arch, "estado": "Pendiente", "timestamp": datetime.now(),
                    "archivos_finales": [] # Nueva lista para archivos de descarga
                })
                st.session_state.mensaje_exito = "¡Pedido enviado!"
                st.session_state.form_version += 1
                st.rerun()

    # Mostrar pedidos del cliente
    pedidos = db.collection("pedidos_bordado").where("cliente", "==", st.session_state.user).stream()
    for p in pedidos:
        data = p.to_dict()
        st.subheader(f"Proyecto: {data['nombre_proyecto']}")
        # Mostrar Archivos Finales (si existen)
        if data.get("archivos_finales"):
            st.success("✅ ¡Archivos listos para descargar!")
            for af in data["archivos_finales"]:
                st.download_button(f"📥 Descargar {af['nombre']}", data=base64.b64decode(af['data']), file_name=af['nombre'])

# =========================================================
# PANEL ADMIN
# =========================================================
else:
    st.title("🛠️ Panel Admin")
    pedidos = db.collection("pedidos_bordado").order_by("timestamp").stream()
    for doc in pedidos:
        p = doc.to_dict()
        st.markdown(f"### {p['nombre_proyecto']} - {p['cliente']}")
        
        # Subir archivos finales
        subir_final = st.file_uploader(f"Subir entregable para {p['nombre_proyecto']}", key=f"up_{doc.id}")
        if subir_final:
            if st.button(f"Guardar entregable {doc.id}"):
                arch_bytes = base64.b64encode(subir_final.getvalue()).decode()
                lista_finales = p.get("archivos_finales", [])
                lista_finales.append({"nombre": subir_final.name, "data": arch_bytes})
                db.collection("pedidos_bordado").document(doc.id).update({"archivos_finales": lista_finales})
                st.success("Archivo subido correctamente.")
                st.rerun()
