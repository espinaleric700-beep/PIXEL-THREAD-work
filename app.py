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

# --- ESTILOS CSS MINIMALISTAS ---
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
        padding: 0.5rem 1rem !important;
    }

    .stButton>button {
        background-color: #00cec9;
        color: #111;
        font-weight: bold;
        border-radius: 6px;
        border: none;
        padding: 4px 10px;
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
    if nombre_lower.endswith(('png', 'jpg', 'jpeg', 'svg')):
        try:
            if not nombre_lower.endswith('svg'):
                img = Image.open(BytesIO(b_cont))
                img.thumbnail((800, 800))
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                buffered = BytesIO()
                img.save(buffered, format="JPEG", quality=80)
                b_cont = buffered.getvalue()
        except Exception:
            pass
    return base64.b64encode(b_cont).decode("utf-8")

def obtener_configuracion_activa():
    try:
        doc = db.collection("config_estudio").document("modelo_actual").get()
        if doc.exists:
            return doc.to_dict()
    except Exception:
        pass
    return {
        "nombre_modelo": "Camisa Estándar",
        "patron_base64": "",
        "modelo_3d_url": "https://modelviewer.dev/shared-assets/models/Astronaut.glb"
    }

# --- ESTADOS ---
params = st.query_params
if "modo_vista" not in st.session_state: 
    st.session_state.modo_vista = params.get("seccion", "Estudio")
if "user" not in st.session_state: 
    st.session_state.user = params.get("user", "ClienteGeneral")
if "herramienta_activa" not in st.session_state:
    st.session_state.herramienta_activa = "Archivos"

if "zoom" not in st.session_state:
    st.session_state.zoom = 100
if "herramienta_lienzo" not in st.session_state:
    st.session_state.herramienta_lienzo = "cursor"

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

    config_actual = obtener_configuracion_activa()
    patron_b64 = config_actual.get("patron_base64", "")
    url_3d = config_actual.get("modelo_3d_url", "https://modelviewer.dev/shared-assets/models/Astronaut.glb")

    col_iconos, col_panel, col_centro, col_right = st.columns([0.5, 2.3, 4.7, 2.5], gap="medium")

    # 1. Barra de Iconos Laterales
    with col_iconos:
        with st.container(border=True):
            if st.button("📁", key="bi_arch"): st.session_state.herramienta_activa = "Archivos"; st.rerun()
            if st.button("🔲", key="bi_elem"): st.session_state.herramienta_activa = "Elementos"; st.rerun()
            if st.button("T", key="bi_text"): st.session_state.herramienta_activa = "Texto"; st.rerun()
            if st.button("✨", key="bi_ia"): st.session_state.herramienta_activa = "IA"; st.rerun()

    # 2. Panel Desplegable de Herramientas
    with col_panel:
        with st.container(border=True):
            if st.session_state.herramienta_activa == "Archivos":
                st.markdown("<div style='font-size: 13px; font-weight: bold;'>Archivos</div>", unsafe_allow_html=True)
                nombre_proyecto = st.text_input("Nombre", "Proyecto Pixel 3D")
                up_file = st.file_uploader("Cargar diseño", type=["png", "jpg", "jpeg", "svg", "dst"])
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

    # 3. Lienzo Central
    with col_centro:
        with st.container(border=True):
            if patron_b64:
                contenido_lienzo = f"<img src='data:image/svg+xml;base64,{patron_b64}' style='max-height: 100%; max-width: 100%; object-fit: contain; border-radius: 6px;' onerror=\"this.onerror=null;this.src='data:image/jpeg;base64,{patron_b64}';\"/>"
            else:
                contenido_lienzo = """
                    <div style='display: flex; gap: 12px; width: 100%; justify-content: center; align-items: center; height: 100%;'>
                        <div style='background: #fff; color: #000; border-radius: 6px; padding: 12px; width: 150px; height: 100%; display: flex; align-items: center; justify-content: center;'>
                            <svg viewBox="0 0 100 120" style="width: 80%; height: 80%; fill: #fff; stroke: #000; stroke-width: 2;"><path d="M 30,10 Q 50,25 70,10 L 85,25 L 75,45 L 85,115 L 15,115 L 25,45 L 15,25 Z"/></svg>
                        </div>
                    </div>
                """

            st.markdown(f"""
                <div style='display: flex; justify-content: center; align-items: center; height: 58vh; background: #181818; border-radius: 8px; overflow: hidden; padding: 10px;'>
                    <div style='transform: scale({st.session_state.zoom / 100}); transform-origin: center; display: flex; justify-content: center; align-items: center; width: 100%; height: 100%;'>
                        {contenido_lienzo}
                    </div>
                </div>
            """, unsafe_allow_html=True)

            st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
            tb1, tb2, tb3, tb4, tb5, tb6, tb7, tb8, tb9, tb10 = st.columns([1, 1, 1, 1, 1, 1, 1.2, 1, 1, 1.2])
            with tb1:
                if st.button("🎯", key="t_cursor", help="Cursor"): st.session_state.herramienta_lienzo = "cursor"
            with tb2:
                if st.button("✋", key="t_hand", help="Mover"): st.session_state.herramienta_lienzo = "hand"
            with tb3:
                if st.button("↩️", key="t_undo", help="Deshacer"): pass
            with tb4:
                if st.button("↪️", key="t_redo", help="Rehacer"): pass
            with tb5:
                if st.button("➖", key="t_zoom_out", help="Alejar"): 
                    if st.session_state.zoom > 50: st.session_state.zoom -= 10; st.rerun()
            with tb6:
                st.markdown(f"<div style='text-align: center; font-size: 11px; padding-top: 6px; color: #fff;'>{st.session_state.zoom}%</div>", unsafe_allow_html=True)
            with tb7:
                if st.button("➕", key="t_zoom_in", help="Acercar"): 
                    if st.session_state.zoom < 200: st.session_state.zoom += 10; st.rerun()
            with tb8:
                if st.button("🔄", key="t_rot", help="Rotar"): pass
            with tb9:
                if st.button("👁️", key="t_view", help="Vista previa"): pass
            with tb10:
                if st.button("⚡ 50", key="t_bolt", help="Acción rápida"): pass

    # 4. Panel Derecho (Visor 3D y Colores)
    with col_right:
        with st.container(border=True):
            model_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
                <style>
                    body {{ margin: 0; background-color: #141414; }}
                    model-viewer {{ width: 100%; height: 150px; background-color: #141414; border-radius: 6px; }}
                </style>
            </head>
            <body>
                <model-viewer src="{url_3d}" auto-rotate camera-controls interaction-prompt="none"></model-viewer>
            </body>
            </html>
            """
            st.components.v1.html(model_html, height=160)

            st.markdown("<div style='font-size: 12px; font-weight: bold; margin-top: 4px;'>Color</div>", unsafe_allow_html=True)
            cc1, cc2, cc3, cc4, cc5, cc6, cc7 = st.columns(7)
            with cc1: st.button("➕", key="c_add")
            with cc2: st.button("⚪", key="c_wh")
            with cc3: st.button("⚫", key="c_bl")
            with cc4: st.button("🔘", key="c_gr")
            with cc5: st.button("🔴", key="c_re")
            with cc6: st.button("🟣", key="c_pu")
            with cc7: st.button("🩷", key="c_pi")

            st.markdown("---")
            st.markdown("<div style='font-size: 12px; font-weight: bold;'>Mis Pedidos</div>", unsafe_allow_html=True)
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

# =========================================================
# VISTA DE ADMIN
# =========================================================
else:
    st.subheader("🛠️ Panel de Administración")
    
    with st.expander("👕 Configurar Patrón y Modelo 3D del Estudio", expanded=True):
        config_actual = obtener_configuracion_activa()
        nuevo_nombre = st.text_input("Nombre del Modelo / Prenda", config_actual.get("nombre_modelo", "Camisa Estándar"))
        nueva_url_3d = st.text_input("URL del Modelo 3D (.glb)", config_actual.get("modelo_3d_url", ""))
        
        # Actualizado para aceptar archivos .svg además de imágenes rasterizadas
        nuevo_archivo_patron = st.file_uploader("Subir Imagen o Patrón Vectorial (SVG, PNG, JPG)", type=["svg", "png", "jpg", "jpeg"])
        
        if st.button("💾 Guardar Configuración de Prenda"):
            try:
                patron_b64 = config_actual.get("patron_base64", "")
                if nuevo_archivo_patron:
                    patron_b64 = procesar_archivo_subido(nuevo_archivo_patron)
                
                db.collection("config_estudio").document("modelo_actual").set({
                    "nombre_modelo": nuevo_nombre,
                    "modelo_3d_url": nueva_url_3d,
                    "patron_base64": patron_b64,
                    "actualizado": datetime.now()
                })
                st.success("¡Configuración de patrón SVG y modelo 3D actualizada con éxito!")
            except Exception as e:
                st.error(f"Error al guardar: {e}")

    st.markdown("---")
    st.subheader("📋 Gestión de Pedidos")
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
