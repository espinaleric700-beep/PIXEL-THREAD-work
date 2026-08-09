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
    
    if nombre_lower.endswith('svg'):
        return base64.b64encode(b_cont).decode("utf-8"), "svg"
    
    if nombre_lower.endswith(('png', 'jpg', 'jpeg')):
        try:
            img = Image.open(BytesIO(b_cont))
            img.thumbnail((1200, 1200))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            b_cont = buffered.getvalue()
        except Exception:
            pass
            
    return base64.b64encode(b_cont).decode("utf-8"), "raster"

def obtener_configuracion_activa():
    try:
        doc = db.collection("config_estudio").document("modelo_actual").get()
        if doc.exists:
            return doc.to_dict()
    except Exception:
        pass
    return {
        "nombre_modelo": "Camisa Estándar",
        "modelo_3d_url": "https://modelviewer.dev/shared-assets/models/Astronaut.glb",
        "piezas": {
            "frente": {"b64": "", "tipo": "raster"},
            "espalda": {"b64": "", "tipo": "raster"},
            "cuello": {"b64": "", "tipo": "raster"},
            "manga_izq": {"b64": "", "tipo": "raster"},
            "manga_der": {"b64": "", "tipo": "raster"}
        }
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
    piezas = config_actual.get("piezas", {})
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
                st.markdown("<div style='font-size: 13px; font-weight: bold;'>Archivos y Patrón</div>", unsafe_allow_html=True)
                nombre_proyecto = st.text_input("Nombre del Proyecto", "Proyecto Pixel 3D")
                
                # Selector para indicar a qué parte del patrón corresponde el diseño
                parte_destino = st.selectbox(
                    "¿A qué parte del patrón agregarlo?",
                    options=["frente", "espalda", "cuello", "manga_izq", "manga_der"],
                    format_func=lambda x: {
                        "frente": "Frente",
                        "espalda": "Espalda",
                        "cuello": "Cuello",
                        "manga_izq": "Manga Izquierda",
                        "manga_der": "Manga Derecha"
                    }[x]
                )
                
                up_file = st.file_uploader("Cargar diseño", type=["png", "jpg", "jpeg", "svg", "dst"])
                
                # Vista previa inmediata en el panel lateral si se subió algo
                if up_file:
                    st.markdown("<div style='font-size: 11px; color: #aaa; margin-top: 4px;'>Vista previa:</div>", unsafe_allow_html=True)
                    try:
                        if up_file.name.lower().endswith(('png', 'jpg', 'jpeg')):
                            st.image(up_file, width=120)
                        elif up_file.name.lower().endswith('svg'):
                            st.caption("📄 Archivo SVG listo para aplicar")
                    except Exception:
                        pass

                col_b_act1, col_b_act2 = st.columns(2)
                with col_b_act1:
                    if st.button("📌 Aplicar al Patrón", key="btn_aplicar_patron"):
                        if up_file:
                            try:
                                b64, tipo = procesar_archivo_subido(up_file)
                                piezas[parte_destino] = {"b64": b64, "tipo": tipo}
                                db.collection("config_estudio").document("modelo_actual").update({
                                    "piezas": piezas
                                })
                                st.success("¡Agregado al patrón!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                        else:
                            st.warning("Sube un archivo primero.")
                with col_b_act2:
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
                            
            elif st.session_state.herramienta_activa == "Elementos":
                st.markdown("##### Elementos")
                st.caption("Gráficos de Pixel Thread")
            elif st.session_state.herramienta_activa == "Texto":
                st.markdown("##### Texto")
                st.text_input("Contenido", "Pixel Thread")
            elif st.session_state.herramienta_activa == "IA":
                st.markdown("##### Logo IA")
                st.text_area("Prompt", "Oso urbano bordado")

    # 3. Lienzo Central Organizado por Piezas (Frente, Espalda, Cuello, Mangas)
    with col_centro:
        with st.container(border=True):
            
            def render_pieza_html(p_data, p_tipo):
                if not p_data:
                    return "<div style='color: #666; font-size: 10px; border: 1px dashed #444; width:100%; height:100%; display:flex; align-items:center; justify-content:center;'>Vacío</div>"
                if p_tipo == "svg":
                    if "<svg" in p_data and "width=" not in p_data:
                        p_data = p_data.replace("<svg", '<svg width="100%" height="100%"')
                    return f"<div style='width:100%; height:100%; display:flex; justify-content:center; align-items:center;'>{base64.b64decode(p_data).decode('utf-8', errors='ignore')}</div>"
                else:
                    return f"<div style='width:100%; height:100%; display:flex; justify-content:center; align-items:center;'><img src='data:image/jpeg;base64,{p_data}' style='max-width:100%; max-height:100%; object-contain;'/></div>"

            f_b64 = piezas.get("frente", {}).get("b64", "")
            f_tipo = piezas.get("frente", {}).get("tipo", "raster")
            
            e_b64 = piezas.get("espalda", {}).get("b64", "")
            e_tipo = piezas.get("espalda", {}).get("tipo", "raster")
            
            c_b64 = piezas.get("cuello", {}).get("b64", "")
            c_tipo = piezas.get("cuello", {}).get("tipo", "raster")
            
            mi_b64 = piezas.get("manga_izq", {}).get("b64", "")
            mi_tipo = piezas.get("manga_izq", {}).get("tipo", "raster")
            
            md_b64 = piezas.get("manga_der", {}).get("b64", "")
            md_tipo = piezas.get("manga_der", {}).get("tipo", "raster")

            canvas_layout_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body, html {{ margin: 0; padding: 0; width: 100%; height: 100%; background-color: #181818; overflow: hidden; }}
                    .viewport {{ width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; }}
                    .zoom-container {{ transform: scale({st.session_state.zoom / 100}); transform-origin: center; display: flex; gap: 15px; align-items: center; justify-content: center; width: 100%; height: 100%; }}
                    .pieza-box {{ background: #222; border-radius: 4px; border: 1px solid #333; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 4px; }}
                    .label {{ font-size: 9px; color: #aaa; margin-top: 2px; text-align: center; }}
                    .col-grande {{ width: 130px; height: 320px; }}
                    .col-derecha {{ display: flex; flex-direction: column; gap: 10px; width: 110px; height: 320px; justify-content: space-between; }}
                    .sub-pieza {{ width: 100%; flex: 1; }}
                </style>
            </head>
            <body>
                <div class="viewport">
                    <div class="zoom-container">
                        <!-- Frente -->
                        <div class="pieza-box col-grande">
                            <div style="width:100%; height: 92%;">
                                {render_pieza_html(f_b64, f_tipo)}
                            </div>
                            <div class="label">Frente</div>
                        </div>
                        <!-- Espalda -->
                        <div class="pieza-box col-grande">
                            <div style="width:100%; height: 92%;">
                                {render_pieza_html(e_b64, e_tipo)}
                            </div>
                            <div class="label">Espalda</div>
                        </div>
                        <!-- Columna Derecha: Cuello y Mangas -->
                        <div class="col-derecha">
                            <div class="pieza-box sub-pieza" style="height: 28%;">
                                <div style="width:100%; height: 85%;">
                                    {render_pieza_html(c_b64, c_tipo)}
                                </div>
                                <div class="label">Cuello</div>
                            </div>
                            <div class="pieza-box sub-pieza" style="height: 33%;">
                                <div style="width:100%; height: 85%;">
                                    {render_pieza_html(mi_b64, mi_tipo)}
                                </div>
                                <div class="label">Manga Izquierda</div>
                            </div>
                            <div class="pieza-box sub-pieza" style="height: 33%;">
                                <div style="width:100%; height: 85%;">
                                    {render_pieza_html(md_b64, md_tipo)}
                                </div>
                                <div class="label">Manga Derecha</div>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            st.components.v1.html(canvas_layout_html, height=450)

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
    
    with st.expander("👕 Configurar Patrón por Piezas y Modelo 3D del Estudio", expanded=True):
        config_actual = obtener_configuracion_activa()
        nuevo_nombre = st.text_input("Nombre del Modelo / Prenda", config_actual.get("nombre_modelo", "Camisa Estándar"))
        nueva_url_3d = st.text_input("URL del Modelo 3D (.glb)", config_actual.get("modelo_3d_url", ""))
        
        st.markdown("---")
        st.markdown("##### Subir Archivos para Cada Parte del Patrón")
        
        up_frente = st.file_uploader("Frente", type=["svg", "png", "jpg", "jpeg"], key="up_f")
        up_espalda = st.file_uploader("Espalda", type=["svg", "png", "jpg", "jpeg"], key="up_e")
        up_cuello = st.file_uploader("Cuello", type=["svg", "png", "jpg", "jpeg"], key="up_c")
        up_manga_izq = st.file_uploader("Manga Izquierda", type=["svg", "png", "jpg", "jpeg"], key="up_mi")
        up_manga_der = st.file_uploader("Manga Derecha", type=["svg", "png", "jpg", "jpeg"], key="up_md")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("💾 Guardar Configuración de Piezas"):
                try:
                    piezas_actuales = config_actual.get("piezas", {
                        "frente": {"b64": "", "tipo": "raster"},
                        "espalda": {"b64": "", "tipo": "raster"},
                        "cuello": {"b64": "", "tipo": "raster"},
                        "manga_izq": {"b64": "", "tipo": "raster"},
                        "manga_der": {"b64": "", "tipo": "raster"}
                    })
                    
                    if up_frente:
                        b64, tipo = procesar_archivo_subido(up_frente)
                        piezas_actuales["frente"] = {"b64": b64, "tipo": tipo}
                    if up_espalda:
                        b64, tipo = procesar_archivo_subido(up_espalda)
                        piezas_actuales["espalda"] = {"b64": b64, "tipo": tipo}
                    if up_cuello:
                        b64, tipo = procesar_archivo_subido(up_cuello)
                        piezas_actuales["cuello"] = {"b64": b64, "tipo": tipo}
                    if up_manga_izq:
                        b64, tipo = procesar_archivo_subido(up_manga_izq)
                        piezas_actuales["manga_izq"] = {"b64": b64, "tipo": tipo}
                    if up_manga_der:
                        b64, tipo = procesar_archivo_subido(up_manga_der)
                        piezas_actuales["manga_der"] = {"b64": b64, "tipo": tipo}
                    
                    db.collection("config_estudio").document("modelo_actual").set({
                        "nombre_modelo": nuevo_nombre,
                        "modelo_3d_url": nueva_url_3d,
                        "piezas": piezas_actuales,
                        "actualizado": datetime.now()
                    })
                    st.success("¡Todas las piezas del patrón fueron guardadas con éxito!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
        with col_btn2:
            if st.button("🗑️ Limpiar Todas las Piezas"):
                try:
                    db.collection("config_estudio").document("modelo_actual").update({
                        "piezas": {
                            "frente": {"b64": "", "tipo": "raster"},
                            "espalda": {"b64": "", "tipo": "raster"},
                            "cuello": {"b64": "", "tipo": "raster"},
                            "manga_izq": {"b64": "", "tipo": "raster"},
                            "manga_der": {"b64": "", "tipo": "raster"}
                        }
                    })
                    st.success("¡Patrones limpiados correctamente!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

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
