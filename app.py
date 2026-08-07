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
st_autorefresh(interval=5000, limit=1000, key="auto_refrescar_cliente")

# --- ESTILOS ---
st.markdown("""
<style>
    .stApp { background: radial-gradient(circle at center, #1a0033 0%, #000000 100%); color: #00ffcc; }
    div.stButton > button { width: 100%; background-color: #00ffcc; color: black; font-weight: bold; border: none; border-radius: 6px; padding: 0.6rem; }
    h1 { color: #00ffcc !important; }
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

# --- ESTADO DE SESIÓN ---
if "modo_vista" not in st.session_state: st.session_state.modo_vista = "Cliente"
if "user" not in st.session_state: st.session_state.user = ""
if "expandir_nuevo_pedido" not in st.session_state: st.session_state.expandir_nuevo_pedido = False

# --- PANEL DE CLIENTE ---
if st.session_state.modo_vista == "Cliente":
    user_input = st.text_input("Ingresa tu ID de Usuario:", value=st.session_state.user)
    if user_input != st.session_state.user: st.session_state.user = user_input
    
    if st.session_state.user:
        with st.expander("➕ Enviar Nuevo Pedido", expanded=st.session_state.expandir_nuevo_pedido):
            with st.form("form_pedido", clear_on_submit=False):
                nombre_proyecto = st.text_input("Nombre del Proyecto")
                tipo_producto = st.radio("Producto:", ["GORRA", "TELA", "VARIOS"], horizontal=True)
                archivos_subidos = st.file_uploader("Sube tus Archivos", type=["png", "jpg", "jpeg", "dst", "pdf"], accept_multiple_files=True)
                comentarios = st.text_area("Comentarios")
                submit = st.form_submit_button("🚀 ENVIAR PEDIDO")
                
                if submit:
                    if not nombre_proyecto or not archivos_subidos:
                        st.error("⚠️ Debes completar el nombre del proyecto y adjuntar archivos.")
                    else:
                        try:
                            lista_archivos = []
                            for archivo in archivos_subidos:
                                bytes_contenido = archivo.getvalue()
                                
                                # PROCESAMIENTO CON ERROR HANDLING
                                try:
                                    if archivo.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                                        img = Image.open(io.BytesIO(bytes_contenido))
                                        if img.mode in ("CMYK", "P"): img = img.convert("RGB")
                                        img.thumbnail((1200, 1200))
                                        buffered = io.BytesIO()
                                        img.save(buffered, format="JPEG" if img.mode != "RGBA" else "PNG", quality=85)
                                        bytes_contenido = buffered.getvalue()
                                except Exception as img_e:
                                    raise Exception(f"Error procesando la imagen {archivo.name}: {str(img_e)}")

                                lista_archivos.append({"nombre": archivo.name.strip(), "data": base64.b64encode(bytes_contenido).decode("utf-8")})

                            db.collection("pedidos_bordado").add({
                                "cliente": st.session_state.user,
                                "nombre_proyecto": nombre_proyecto,
                                "producto": tipo_producto,
                                "archivos": lista_archivos,
                                "estado": "Pendiente",
                                "timestamp": datetime.now()
                            })
                            st.success("✅ Pedido enviado exitosamente.")
                            st.session_state.expandir_nuevo_pedido = False
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Error al enviar el pedido: {str(e)}")
                            st.session_state.expandir_nuevo_pedido = True # Mantiene el formulario abierto
    
    # Visualización de pedidos
    try:
        pedidos = db.collection("pedidos_bordado").where("cliente", "==", st.session_state.user).stream()
        for p in pedidos:
            st.write(f"### Proyecto: {p.to_dict().get('nombre_proyecto')} - Estado: {p.to_dict().get('estado')}")
    except Exception:
        pass
