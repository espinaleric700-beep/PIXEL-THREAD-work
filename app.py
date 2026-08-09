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

# --- ESTILOS CSS PARA FIJAR EL DISEÑO ---
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
        padding: 1rem 1.5rem !important;
    }
    
    .stButton>button {
        background-color: #00cec9;
        color: #111;
        font-weight: bold;
        border-radius: 6px;
        border: none;
        padding: 4px 10px;
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
c_top1, c_top2, c_top3, c_top4 = st.columns([1, 5, 2, 2])
with c_top1:
    if st.button("✕ Salir"):
        actualizar_url("Estudio", st.session_state.user)
with c_top2:
    st.markdown("<h4 style='margin: 0; color: #fff;'>Subir y Diseñar</h4>", unsafe_allow_html=True)
with c_top3:
    if st.session_state.user.strip().lower() in [a.lower() for a in ADMINS_AUTORIZADOS]:
        if st.button("🛠️ Panel Admin"):
            actualizar_url("Admin" if st.session_state.modo_vista != "Admin" else "Estudio", st.session_state.user)
with c_top4:
    if st.button("Guardar", use_container_width=True):
        st.session_state.guardar_trigger = True

st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

# =========================================================
# VISTA DE ESTUDIO
# =========================================================
if st.session_state.modo_vista == "Estudio":

    # Distribución en 4 columnas compactas para evitar desbordamientos
    col_iconos, col_panel, col_centro, col_3d = st.columns([0.6, 2.0, 4.4, 2.3], gap="small")

    # 1. Barra de iconos lateral
    with col_iconos:
        st.markdown("<div style='background-color: #121212; border-radius: 8px; padding: 10px 4px; height: 680px; display: flex; flex-direction: column; align-items: center; gap: 10px;'>", unsafe_allow_html=True)
        if st.button("📁", key="bi_arch", help="Archivos"):
            st.session_state.herramienta_activa = "Archivos"; st.rerun()
        if st.button("🔲", key="bi_elem", help="Elementos"):
            st.session_state.herramienta_activa = "Elementos"; st.rerun()
        if st.button("T", key="bi_text", help="Texto"):
            st.session_state.herramienta_activa = "Texto"; st.rerun()
        if st.button("✨", key="bi_ia", help="Logo IA"):
            st.session_state.herramienta_activa = "IA"; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # 2. Panel deslizante de herramientas
    with col_panel:
        st.markdown("<div style='background-color: #1e1e1e; border: 1px solid #333; border-radius: 8px; padding: 12px; height: 680px; overflow-y: auto;'>", unsafe_allow_html=True)
        
        if st.session_state.herramienta_activa == "Archivos":
            st.markdown("##### Archivos Subidos")
            nombre_proyecto = st.text_input("Nombre", "Proyecto Pixel 3D")
            up_file = st.file_uploader("Cargar diseño", type=["png", "jpg", "jpeg", "svg", "dst"])
            st.markdown("---")
            if st.button("🚀 Enviar a Producción", use_container_width=True):
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
            st.caption("Gráficos disponibles de Pixel Thread")

        elif st.session_state.herramienta_activa == "Texto":
            st.markdown("##### Texto")
            st.text_input("Contenido", "Pixel Thread")

        elif st.session_state.herramienta_activa == "IA":
            st.markdown("##### Logo IA")
            st.text_area("Prompt", "Oso urbano bordado")

        st.markdown("</div>", unsafe_allow_html=True)

    # 3. Lienzo central (Despiece de camisas horizontal/organizado)
    with col_centro:
        st.markdown("""
            <div style='background-color: #222; border: 1px solid #333; border-radius: 8px; padding: 15px; height: 680px; display: flex; flex-direction: column; justify-content: space-between; align-items: center;'>
                <div style='display: flex; gap: 10px; width: 100%; justify-content: center; align-items: center; height: 580px;'>
                    <!-- Frente -->
                    <div style='background: #fff; color: #000; border-radius: 6px; padding: 10px; width: 140px; height: 440px; display: flex; flex-direction: column; align-items: center; justify-content: center;'>
                        <span style='font-size: 10px; font-weight: bold;'>FRENTE</span>
                        <div style='border: 2px dashed #00cec9; border-radius: 50%; width: 70px; height: 70px; display: flex; align-items: center; justify-content: center; margin-top: 10px;'>🐻</div>
                    </div>
                    <!-- Espalda -->
                    <div style='background: #fff; color: #000; border-radius: 6px; padding: 10px; width: 140px; height: 440px; display: flex; flex-direction: column; align-items: center; justify-content: center;'>
                        <span style='font-size: 10px; font-weight: bold;'>ESPALDA</span>
                        <div style='border: 2px dashed #ccc; border-radius: 50%; width: 70px; height: 70px; display: flex; align-items: center; justify-content: center; margin-top: 10px;'></div>
                    </div>
                    <!-- Cuello y Mangas -->
                    <div style='display: flex; flex-direction: column; gap: 8px; height: 440px; justify-content: center;'>
                        <div style='background: #fff; color: #000; border-radius: 6px; width: 100px; height: 90px; display: flex; flex-direction: column; align-items: center; justify-content: center;'>
                            <span style='font-size: 8px; font-weight: bold;'>CUELLO</span>
                        </div>
                        <div style='background: #fff; color: #000; border-radius: 6px; width: 100px; height: 165px; display: flex; flex-direction: column; align-items: center; justify-content: center;'>
                            <span style='font-size: 8px; font-weight: bold;'>MANGA IZQ</span>
                        </div>
                        <div style='background: #fff; color: #000; border-radius: 6px; width: 100px; height: 165px; display: flex; flex-direction: column; align-items: center; justify-content: center;'>
                            <span style='font-size: 8px; font-weight: bold;'>MANGA DER</span>
                        </div>
                    </div>
                </div>
                <div style='font-size: 12px; color: #aaa; display: flex; gap: 20px;'>
                    <span>↩️ Deshacer</span><span>🔍 Zoom 100%</span><span>👁️ Vista Previa</span><span>⚡ 50 pts</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # 4. Panel Derecho (Visor 3D y Colores)
    with col_3d:
        st.markdown("<div style='background-color: #1e1e1e; border: 1px solid #333; border-radius: 8px; padding: 12px; height: 680px; display: flex; flex-direction: column; gap: 12px;'>", unsafe_allow_html=True)
        
        model_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
            <style>
                body { margin: 0; background-color: #1e1e1e; }
                model-viewer { width: 100%; height: 260px; background-color: #141414; border-radius: 6px; }
            </style>
        </head>
        <body>
            <model-viewer src="https://modelviewer.dev/shared-assets/models/Astronaut.glb" auto-rotate camera-controls interaction-prompt="none"></model-viewer>
        </body>
        </html>
        """
        st.components.v1.html(model_html, height=270)

        st.markdown("##### Color del Producto")
        cc1, cc2, cc3, cc4, cc5, cc6, cc7 = st.columns(7)
        with cc1: st.button("➕", key="c_add")
        with cc2: st.button("⚪", key="c_wh")
        with cc3: st.button("⚫", key="c_bl")
        with cc4: st.button("🔘", key="c_gr")
        with cc5: st.button("🔴", key="c_re")
        with cc6: st.button("🟣", key="c_pu")
        with cc7: st.button("🩷", key="c_pi")

        st.markdown("---")
        st.markdown("##### Mis Pedidos")
        try:
            docs_p = list(db.collection("pedidos_bordado").order_by("timestamp").stream())
            mis_p = [p.to_dict() for p in docs_p if p.to_dict().get("cliente", "").strip().lower() == st.session_state.user.strip().lower()]
            if mis_p:
                p_rec = mis_p[-1]
                st.caption(f"🧵 {p_rec.get('nombre_proyecto')} | #{p_rec.get('turno')}")
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
