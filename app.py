import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Pixel Thread - Estudio de Diseño",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS LIMPIOS PARA DISEÑO FLUIDO ---
st.markdown("""
    <style>
    .stApp {
        background-color: #1a1a1a;
        color: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .block-container {
        max-width: 100% !important;
        padding: 0.4rem 1rem !important;
    }

    .panel-box {
        background-color: #141414;
        border: 1px solid #2a2a2a;
        border-radius: 12px;
        padding: 12px;
        height: 78vh;
        overflow-y: auto;
    }

    .canvas-box {
        background-color: #212121;
        border: 1px solid #2a2a2a;
        border-radius: 12px;
        padding: 12px;
        height: 78vh;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        align-items: center;
    }

    .stButton>button {
        background-color: #00cec9;
        color: #111;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 6px 12px;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #01a3a4;
        color: #fff;
    }
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

# --- FUNCIONES AUXILIARES ---
def recalcular_turnos():
    try:
        docs = list(db.collection("pedidos_bordado").order_by("timestamp").stream())
        turno_actual = 1
        for doc in docs:
            data = doc.to_dict()
            estado = data.get("estado", "Pendiente")
            if estado != "Completado":
                db.collection("pedidos_bordado").document(doc.id).update({"turno": turno_actual})
                turno_actual += 1
            else:
                db.collection("pedidos_bordado").document(doc.id).update({"turno": "N/A"})
    except Exception:
        pass

def procesar_archivo_subido(arch):
    b_cont = arch.getvalue()
    nombre_lower = arch.name.lower()
    if nombre_lower.endswith(('png', 'jpg', 'jpeg')):
        try:
            img = Image.open(BytesIO(b_cont))
            img.thumbnail((700, 700))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=70)
            b_cont = buffered.getvalue()
        except Exception:
            pass
    return base64.b64encode(b_cont).decode("utf-8")

# --- ESTADOS ---
params = st.query_params
if "modo_vista" not in st.session_state: 
    st.session_state.modo_vista = params.get("seccion", "Estudio")
if "user" not in st.session_state: 
    st.session_state.user = params.get("user", "ClienteGeneral")
if "herramienta_activa" not in st.session_state:
    st.session_state.herramienta_activa = "Archivos"

def actualizar_url(vista, user):
    st.session_state.modo_vista = vista
    st.session_state.user = user
    st.query_params.update({"seccion": vista, "user": user})
    st.rerun()

ADMINS_AUTORIZADOS = ["pixel2580", "eric"]

# --- BARRA SUPERIOR ---
c_top1, c_top2, c_top3, c_top4 = st.columns([1, 6, 2, 2])
with c_top1:
    if st.button("✕ Salir", key="btn_exit"):
        actualizar_url("Estudio", st.session_state.user)
with c_top2:
    st.markdown("<h4 style='margin: 0; color: #fff;'>Subir y Diseñar</h4>", unsafe_allow_html=True)
with c_top3:
    if st.session_state.user.strip().lower() in [a.lower() for a in ADMINS_AUTORIZADOS]:
        if st.button("🛠️ Panel Admin", key="btn_admin_top"):
            actualizar_url("Admin" if st.session_state.modo_vista != "Admin" else "Estudio", st.session_state.user)
with c_top4:
    if st.button("Guardar", key="btn_save_top"):
        st.session_state.guardar_trigger = True

st.markdown("<div style='margin-bottom: 6px;'></div>", unsafe_allow_html=True)

# =========================================================
# VISTA DE ESTUDIO
# =========================================================
if st.session_state.modo_vista == "Estudio":

    # Estructura de 4 columnas nativas de Streamlit con proporciones exactas para que todo quede en pantalla
    col_iconos, col_panel, col_centro, col_right = st.columns([0.6, 2.4, 4.8, 2.8], gap="small")

    # 1. Columna de Iconos Laterales
    with col_iconos:
        st.markdown("<div class='panel-box' style='display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 10px 2px;'>", unsafe_allow_html=True)
        if st.button("📁", key="bi_arch"): st.session_state.herramienta_activa = "Archivos"; st.rerun()
        if st.button("🔲", key="bi_elem"): st.session_state.herramienta_activa = "Elementos"; st.rerun()
        if st.button("T", key="bi_text"): st.session_state.herramienta_activa = "Texto"; st.rerun()
        if st.button("✨", key="bi_ia"): st.session_state.herramienta_activa = "IA"; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # 2. Panel Desplegable de Herramientas
    with col_panel:
        st.markdown("<div class='panel-box'>", unsafe_allow_html=True)
        if st.session_state.herramienta_activa == "Archivos":
            st.markdown("<div style='font-size: 13px; font-weight: bold; margin-bottom: 8px;'>Archivos</div>", unsafe_allow_html=True)
            nombre_proyecto = st.text_input("Nombre", "Proyecto Pixel 3D")
            up_file = st.file_uploader("Cargar diseño", type=["png", "jpg", "jpeg", "svg", "dst"])
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            if st.button("🚀 Enviar a Producción", key="btn_prod"):
                try:
                    lista_archivos = []
                    if up_file:
                        lista_archivos.append({"nombre": up_file.name, "data": procesar_archivo_subido(up_file)})
                    db.collection("pedidos_bordado").add({
                        "id": f"PT-{int(datetime.now().timestamp())}",
                        "cliente": st.session_state.user.strip(),
                        "nombre_proyecto": nombre_proyecto,
                        "archivos": lista_archivos,
                        "estado": "Pendiente",
                        "turno": 1,
                        "timestamp": datetime.now()
                    })
                    recalcular_turnos()
                    st.success("¡Enviado!")
                except Exception as e:
                    st.error(f"Error: {e}")
        elif st.session_state.herramienta_activa == "Elementos":
            st.markdown("##### Elementos")
            st.caption("Gráficos de Pixel Thread")
        elif st.session_state.herramienta_activa == "Texto":
            st.markdown("##### Texto")
            st.text_input("Contenido", "Pixel Thread")
        elif st.session_state.herramienta_activa == "IA":
            st.markdown("##### Logo IA")
            st.text_area("Prompt", "Oso urbano bordado")
        st.markdown("</div>", unsafe_allow_html=True)

    # 3. Lienzo Central (Patrones de la Camiseta + Barra de herramientas flotante inferior)
    with col_centro:
        st.markdown("""
            <div class='canvas-box'>
                <div style='display: flex; gap: 15px; width: 100%; justify-content: center; align-items: center; height: 66vh;'>
                    <!-- Frente -->
                    <div style='background: #fff; color: #000; border-radius: 8px; padding: 10px; width: 145px; height: 95%; display: flex; flex-direction: column; align-items: center; justify-content: center;'>
                        <div style='border: 2px dashed #00cec9; border-radius: 50%; width: 65px; height: 65px; display: flex; align-items: center; justify-content: center;'>🐻</div>
                    </div>
                    <!-- Espalda -->
                    <div style='background: #fff; color: #000; border-radius: 8px; padding: 10px; width: 145px; height: 95%; display: flex; flex-direction: column; align-items: center; justify-content: center;'>
                        <div style='border: 2px dashed #ccc; border-radius: 50%; width: 65px; height: 65px; display: flex; align-items: center; justify-content: center;'></div>
                    </div>
                    <!-- Mangas y Cuello -->
                    <div style='display: flex; flex-direction: column; gap: 8px; height: 95%; justify-content: center;'>
                        <div style='background: #fff; color: #000; border-radius: 8px; width: 95px; height: 22%;'></div>
                        <div style='background: #fff; color: #000; border-radius: 8px; width: 95px; height: 37%;'></div>
                        <div style='background: #fff; color: #000; border-radius: 8px; width: 95px; height: 37%;'></div>
                    </div>
                </div>
                <!-- Barra inferior flotante -->
                <div style='background-color: #121212; border: 1px solid #2a2a2a; border-radius: 30px; padding: 6px 18px; display: flex; gap: 15px; align-items: center; font-size: 12px; color: #aaa;'>
                    <span>🔲</span><span>✋</span><span>|</span><span>↩️</span><span>↪️</span><span>|</span><span>- 100% +</span><span>|</span><span>🔄 👁️</span><span>|</span><span>⚡ 50</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # 4. Panel Derecho (Visor 3D y Selector de Colores)
    with col_right:
        st.markdown("<div class='panel-box' style='display: flex; flex-direction: column; gap: 10px;'>", unsafe_allow_html=True)
        
        model_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
            <style>
                body { margin: 0; background-color: #141414; }
                model-viewer { width: 100%; height: 180px; background-color: #141414; border-radius: 8px; }
            </style>
        </head>
        <body>
            <model-viewer src="https://modelviewer.dev/shared-assets/models/Astronaut.glb" auto-rotate camera-controls interaction-prompt="none"></model-viewer>
        </body>
        </html>
        """
        st.components.v1.html(model_html, height=190)

        st.markdown("<div style='font-size: 13px; font-weight: bold;'>Color</div>", unsafe_allow_html=True)
        cc1, cc2, cc3, cc4, cc5, cc6, cc7 = st.columns(7)
        with cc1: st.button("➕", key="c_add")
        with cc2: st.button("⚪", key="c_wh")
        with cc3: st.button("⚫", key="c_bl")
        with cc4: st.button("🔘", key="c_gr")
        with cc5: st.button("🔴", key="c_re")
        with cc6: st.button("🟣", key="c_pu")
        with cc7: st.button("🩷", key="c_pi")

        st.markdown("---")
        st.markdown("<div style='font-size: 13px; font-weight: bold;'>Mis Pedidos</div>", unsafe_allow_html=True)
        try:
            docs_p = list(db.collection("pedidos_bordado").order_by("timestamp").stream())
            mis_p = [p.to_dict() for p in docs_p if p.to_dict().get("cliente", "").strip().lower() == st.session_state.user.strip().lower()]
            if mis_p:
                p_rec = mis_p[-1]
                st.caption(f"🧵 {p_rec.get('nombre_proyecto')} | Turno: #{p_rec.get('turno')}")
                st.caption(f"Estado: {p_rec.get('estado')}")
            else:
                st.caption("Sin pedidos recientes.")
        except Exception:
            pass

        st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# VISTA DE ADMIN
# =========================================================
else:
    st.subheader("🛠️ Panel de Administración")
    try:
        recalcular_turnos()
        docs = list(db.collection("pedidos_bordado").order_by("timestamp").stream())
        for doc in docs:
            p = doc.to_dict()
            with st.container(border=True):
                st.write(f"**Cliente:** {p.get('cliente')} | **Proyecto:** {p.get('nombre_proyecto')} | **Estado:** {p.get('estado')}")
                if st.button("Eliminar", key=f"del_{doc.id}"):
                    db.collection("pedidos_bordado").document(doc.id).delete()
                    recalcular_turnos()
                    st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")
