import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Pixel Thread - Estudio 3D Directo",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS ---
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

SKETCHFAB_UID = "52e167c5a6024ee8b9b8fb8b9a7a89fc"

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
    
    if nombre_lower.endswith('svg'):
        return base64.b64encode(b_cont).decode("utf-8"), "svg"
    
    if nombre_lower.endswith(('png', 'jpg', 'jpeg')):
        try:
            img = Image.open(BytesIO(b_cont))
            img.thumbnail((1200, 1200))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGBA")
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                return base64.b64encode(buffered.getvalue()).decode("utf-8"), "png_trans"
            else:
                buffered = BytesIO()
                img.save(buffered, format="JPEG", quality=85)
                return base64.b64encode(buffered.getvalue()).decode("utf-8"), "raster"
        except Exception:
            pass
            
    return base64.b64encode(b_cont).decode("utf-8"), "raster"

def generar_textura_3d(imagen_subida_b64):
    try:
        if not imagen_subida_b64:
            return ""
        
        decoded_elem = base64.b64decode(imagen_subida_b64)
        img_elem = Image.open(BytesIO(decoded_elem)).convert("RGBA")
        
        img_base = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255))
        img_elem = img_elem.resize((500, 500))
        ex = (1024 - 500) // 2
        ey = (1024 - 500) // 2
        
        img_base.paste(img_elem, (ex, ey), img_elem)

        buffered = BytesIO()
        img_base.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception:
        return ""

def obtener_configuracion_activa():
    try:
        doc = db.collection("config_estudio").document("modelo_actual").get()
        if doc.exists:
            return doc.to_dict()
    except Exception:
        pass
    return {
        "nombre_modelo": "Camisa Estándar",
        "sketchfab_uid": SKETCHFAB_UID,
    }

params = st.query_params
if "modo_vista" not in st.session_state: 
    st.session_state.modo_vista = params.get("seccion", "Estudio")
if "user" not in st.session_state: 
    st.session_state.user = params.get("user", "ClienteGeneral")
if "imagen_activa_b64" not in st.session_state:
    st.session_state.imagen_activa_b64 = ""

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
    st.markdown("<h4 style='margin: 0; color: #fff;'>Estudio 3D Directo - Pixel Thread</h4>", unsafe_allow_html=True)
with c_top3:
    if st.session_state.user.strip().lower() in [a.lower() for a in ADMINS_AUTORIZADOS]:
        if st.button("🛠️ Panel Admin", key="btn_admin_top"):
            actualizar_url("Admin" if st.session_state.modo_vista != "Admin" else "Estudio", st.session_state.user)
with c_top4:
    if st.button("Guardar", key="btn_save_top"):
        st.session_state.guardar_trigger = True

st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

# =========================================================
# VISTA DE ESTUDIO
# =========================================================
if st.session_state.modo_vista == "Estudio":

    config_actual = obtener_configuracion_activa()
    sk_uid = config_actual.get("sketchfab_uid", SKETCHFAB_UID)

    col_panel, col_visor = st.columns([3.5, 6.5], gap="medium")

    # 1. Panel Izquierdo: Carga de Imagen y Controles
    with col_panel:
        with st.container(border=True):
            st.markdown("<div style='font-size: 15px; font-weight: bold;'>Subir Diseño para Textura 3D</div>", unsafe_allow_html=True)
            nombre_proyecto = st.text_input("Nombre del Proyecto", "Proyecto Pixel 3D")
            
            up_file = st.file_uploader("Seleccionar archivo (PNG, JPG, SVG)", type=["png", "jpg", "jpeg", "svg"])
            
            if up_file:
                st.markdown("<div style='font-size: 12px; color: #aaa; margin-top: 6px;'>Vista previa:</div>", unsafe_allow_html=True)
                try:
                    if up_file.name.lower().endswith(('png', 'jpg', 'jpeg')):
                        st.image(up_file, width=160)
                    elif up_file.name.lower().endswith('svg'):
                        st.caption("📄 Archivo SVG cargado")
                except Exception:
                    pass

            st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("✨ Aplicar al Modelo 3D", key="btn_aplicar_3d"):
                    if up_file:
                        try:
                            b64, _ = procesar_archivo_subido(up_file)
                            st.session_state.imagen_activa_b64 = b64
                            st.success("¡Textura aplicada al modelo 3D!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.warning("Sube un archivo primero.")
            with col_b2:
                if st.button("🚀 Producción", key="btn_prod"):
                    try:
                        lista_archivos = []
                        if up_file:
                            archivo_b64, _ = procesar_archivo_subido(up_file)
                            lista_archivos.append({"nombre": up_file.name, "data": archivo_b64})
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
                        st.success("¡Enviado a Producción!")
                    except Exception as e:
                        st.error(f"Error: {e}")

            if st.session_state.imagen_activa_b64:
                st.markdown("---")
                if st.button("🗑️ Quitar Textura del Modelo"):
                    st.session_state.imagen_activa_b64 = ""
                    st.success("Textura removida.")
                    st.rerun()

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

    # 2. Panel Derecho: Visor 3D Grande a Pantalla Completa
    with col_visor:
        with st.container(border=True):
            st.markdown("<div style='font-size: 14px; font-weight: bold; margin-bottom: 8px;'>Visualizador 3D en Vivo</div>", unsafe_allow_html=True)
            
            textura_b64 = generar_textura_3d(st.session_state.imagen_activa_b64)

            sketchfab_viewer_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ margin: 0; background-color: #141414; overflow: hidden; }}
                    #sketchfab-iframe {{ width: 100%; height: 520px; border: none; display: block; }}
                </style>
                <script src="https://static.sketchfab.com/api/sketchfab-viewer-1.12.1.js"></script>
            </head>
            <body>
                <iframe id="sketchfab-iframe" src="" allow="autoplay; fullscreen; vr" xr-spatial-tracking execution-while-out-of-viewport execution-while-not-rendered web-share allowfullscreen></iframe>
                
                <script>
                    var iframe = document.getElementById('sketchfab-iframe');
                    var urlid = '{sk_uid}';
                    var client = new Sketchfab(iframe);

                    client.init(urlid, {{
                        success: function onSuccess(api) {{
                            api.start();
                            api.addEventListener('viewerready', function() {{
                                api.getMaterialList(function(err, materials) {{
                                    if (!err && materials.length > 0) {{
                                        var material = materials[0];
                                        var b64Data = "data:image/png;base64,{textura_b64}";
                                        
                                        if ("{textura_b64}" !== "") {{
                                            api.addTexture(b64Data, function(err, textureUid) {{
                                                if (!err) {{
                                                    material.channels.AlbedoPBR.texture = {{ uid: textureUid }};
                                                    api.setMaterial(material);
                                                }}
                                            }});
                                        }}
                                    }}
                                }});
                            }});
                        }},
                        error: function onError() {{
                            console.error('Error al inicializar Sketchfab');
                        }}
                    }});
                </script>
            </body>
            </html>
            """
            st.components.v1.html(sketchfab_viewer_html, height=535)

            st.markdown("<div style='font-size: 12px; font-weight: bold; margin-top: 10px;'>Color de Base de la Prenda</div>", unsafe_allow_html=True)
            cc1, cc2, cc3, cc4, cc5, cc6, cc7 = st.columns(7)
            with cc1: st.button("➕", key="c_add")
            with cc2: st.button("⚪", key="c_wh")
            with cc3: st.button("⚫", key="c_bl")
            with cc4: st.button("🔘", key="c_gr")
            with cc5: st.button("🔴", key="c_re")
            with cc6: st.button("🟣", key="c_pu")
            with cc7: st.button("🩷", key="c_pi")

# =========================================================
# VISTA DE ADMIN
# =========================================================
else:
    st.subheader("🛠️ Panel de Administración")
    
    with st.expander("👕 Configurar Modelo 3D Base", expanded=True):
        config_actual = obtener_configuracion_activa()
        nuevo_nombre = st.text_input("Nombre del Modelo / Prenda", config_actual.get("nombre_modelo", "Camisa Estándar"))
        nuevo_uid = st.text_input("Sketchfab Model UID", config_actual.get("sketchfab_uid", SKETCHFAB_UID))
        
        if st.button("💾 Guardar Configuración 3D"):
            try:
                db.collection("config_estudio").document("modelo_actual").set({
                    "nombre_modelo": nuevo_nombre,
                    "sketchfab_uid": nuevo_uid,
                    "actualizado": datetime.now()
                }, merge=True)
                st.success("¡Configuración guardada con éxito!")
                st.rerun()
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
    except Exception as e:
        st.error(f"Error al cargar pedidos: {e}")
