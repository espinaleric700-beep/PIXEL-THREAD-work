import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image
import requests

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

# --- FUNCIONES AUXILIARES Y DE SKETCHFAB ---
SKETCHFAB_API_KEY = "52e167c5a6024ee8b9b8fb8b9a7a89fc"

def buscar_modelos_sketchfab(query="shirt"):
    url = f"https://api.sketchfab.com/v3/search?type=models&q={query}&downloadable=true"
    headers = {"Authorization": f"Token {SKETCHFAB_API_KEY}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get("results", [])
    except Exception:
        pass
    return []

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
                b_cont = buffered.getvalue()
                return base64.b64encode(b_cont).decode("utf-8"), "png_trans"
            else:
                buffered = BytesIO()
                img.save(buffered, format="JPEG", quality=85)
                b_cont = buffered.getvalue()
        except Exception:
            pass
            
    return base64.b64encode(b_cont).decode("utf-8"), "raster"

def generar_textura_3d_frente(pieza_frente):
    """Combina el fondo del frente y los elementos posicionados para aplicarlos al visor 3D"""
    try:
        base_b64 = pieza_frente.get("b64", "")
        base_tipo = pieza_frente.get("tipo", "raster")
        elementos = pieza_frente.get("elementos", [])

        img_base = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255))
        
        if base_b64 and base_tipo != "svg":
            try:
                decoded_base = base64.b64decode(base_b64)
                img_bg = Image.open(BytesIO(decoded_base)).convert("RGBA")
                img_bg = img_bg.resize((1024, 1024))
                img_base.paste(img_bg, (0, 0), img_bg)
            except Exception:
                pass

        for elem in elementos:
            e_b64 = elem.get("b64", "")
            e_tipo = elem.get("tipo", "raster")
            if e_b64 and e_tipo != "svg":
                try:
                    decoded_elem = base64.b64decode(e_b64)
                    img_elem = Image.open(BytesIO(decoded_elem)).convert("RGBA")
                    
                    w_pct = elem.get("ancho", 80)
                    h_pct = elem.get("alto", 80)
                    ew = int((w_pct / 100.0) * 500)
                    eh = int((h_pct / 100.0) * 500)
                    img_elem = img_elem.resize((max(30, ew), max(30, eh)))
                    
                    x_pct = elem.get("x", 50)
                    y_pct = elem.get("y", 50)
                    ex = int((x_pct / 100.0) * 1024) - (img_elem.width // 2)
                    ey = int((y_pct / 100.0) * 1024) - (img_elem.height // 2)
                    
                    img_base.paste(img_elem, (ex, ey), img_elem)
                except Exception:
                    pass

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
        "modelo_3d_url": "",
        "sketchfab_uid": "",
        "piezas": {
            "frente": {"b64": "", "tipo": "raster", "elementos": []},
            "espalda": {"b64": "", "tipo": "raster", "elementos": []},
            "cuello": {"b64": "", "tipo": "raster", "elementos": []},
            "manga_izq": {"b64": "", "tipo": "raster", "elementos": []},
            "manga_der": {"b64": "", "tipo": "raster", "elementos": []}
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
                    if st.button("📌 Agregar al Patrón", key="btn_aplicar_patron"):
                        if up_file:
                            try:
                                b64, tipo = procesar_archivo_subido(up_file)
                                if parte_destino not in piezas:
                                    piezas[parte_destino] = {"b64": "", "tipo": "raster", "elementos": []}
                                if "elementos" not in piezas[parte_destino]:
                                    piezas[parte_destino]["elementos"] = []
                                
                                nuevo_elemento = {
                                    "id": f"elem_{int(datetime.now().timestamp())}",
                                    "b64": b64,
                                    "tipo": tipo,
                                    "x": 50,
                                    "y": 50,
                                    "ancho": 80,
                                    "alto": 80,
                                    "rotacion": 0
                                }
                                piezas[parte_destino]["elementos"].append(nuevo_elemento)
                                
                                db.collection("config_estudio").document("modelo_actual").update({
                                    "piezas": piezas
                                })
                                st.success("¡Imagen agregada al patrón y al mockup 3D!")
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

                # Sección para eliminar elementos subidos
                st.markdown("---")
                st.markdown("<div style='font-size: 12px; font-weight: bold;'>Eliminar Elementos Subidos</div>", unsafe_allow_html=True)
                
                elementos_totales = []
                for p_key, p_val in piezas.items():
                    if isinstance(p_val, dict):
                        for el in p_val.get("elementos", []):
                            elementos_totales.append((p_key, el))
                
                if elementos_totales:
                    sel_idx = st.selectbox("Seleccionar Elemento a Borrar", range(len(elementos_totales)), format_func=lambda i: f"{elementos_totales[i][0].upper()} - {elementos_totales[i][1]['id']}")
                    p_target, el_target = elementos_totales[sel_idx]
                    
                    if st.button("🗑️ Eliminar Elemento Seleccionado", key=f"del_elem_{el_target['id']}"):
                        try:
                            piezas[p_target]["elementos"] = [el for el in piezas[p_target]["elementos"] if el["id"] != el_target["id"]]
                            db.collection("config_estudio").document("modelo_actual").update({"piezas": piezas})
                            st.success("¡Elemento eliminado!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al eliminar: {e}")
                else:
                    st.caption("No hay elementos en el patrón.")
                            
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
            
            def render_capas_pieza(p_dict, p_nombre_pieza):
                if not isinstance(p_dict, dict):
                    base_b64 = p_dict
                    base_tipo = "raster"
                    elementos = []
                else:
                    base_b64 = p_dict.get("b64", "")
                    base_tipo = p_dict.get("tipo", "raster")
                    elementos = p_dict.get("elementos", [])

                html_base = ""
                if base_b64:
                    if base_tipo == "svg":
                        html_base = f"<div style='width:100%; height:100%; display:flex; justify-content:center; align-items:center;'>{base64.b64decode(base_b64).decode('utf-8', errors='ignore')}</div>"
                    else:
                        mime = "image/png" if base_tipo == "png_trans" else "image/jpeg"
                        html_base = f"<div style='width:100%; height:100%; display:flex; justify-content:center; align-items:center;'><img src='data:{mime};base64,{base_b64}' style='max-width:100%; max-height:100%; object-fit:contain;'/></div>"
                else:
                    html_base = "<div style='background-color: #ffffff; width: 75%; height: 85%; border-radius: 4px; opacity: 0.9;'></div>"

                html_elementos = ""
                for idx, elem in enumerate(elementos):
                    e_id = elem.get("id", f"elem_{idx}")
                    e_b64 = elem.get("b64", "")
                    e_tipo = elem.get("tipo", "raster")
                    posX = elem.get("x", 50)
                    posY = elem.get("y", 50)
                    ancho = elem.get("ancho", 80)
                    alto = elem.get("alto", 80)
                    rotacion = elem.get("rotacion", 0)

                    contenido_elem = ""
                    if e_tipo == "svg":
                        contenido_elem = base64.b64decode(e_b64).decode('utf-8', errors='ignore')
                    else:
                        mime_e = "image/png" if e_tipo == "png_trans" else "image/jpeg"
                        contenido_elem = f"<img src='data:{mime_e};base64,{e_b64}' style='width: 100%; height: 100%; object-fit: contain; pointer-events: none;'/>"

                    html_elementos += f"""
                    <div class='draggable-item' id='item_{p_nombre_pieza}_{e_id}' 
                         style='position: absolute; left: {posX}%; top: {posY}%; transform: translate(-50%, -50%) rotate({rotacion}deg); width: {ancho}px; height: {alto}px; cursor: grab; z-index: 10; border: 1px dashed rgba(0,206,201,0.7); background: rgba(0,0,0,0.1);'
                         onmousedown='startDrag(event, "{p_nombre_pieza}", "{e_id}")'>
                        {contenido_elem}
                        <div class='resize-handle' style='position: absolute; right: -4px; bottom: -4px; width: 10px; height: 10px; background: #00cec9; cursor: se-resize; z-index: 15;'
                             onmousedown='startResize(event, "{p_nombre_pieza}", "{e_id}")'></div>
                    </div>
                    """

                return f"""
                <div class='drop-zone' id='zone_{p_nombre_pieza}' style='position: relative; width: 100%; height: 100%; overflow: hidden; display: flex; justify-content: center; align-items: center;'>
                    <div style='position: absolute; width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; z-index: 1;'>
                        {html_base}
                    </div>
                    <div style='position: absolute; width: 100%; height: 100%; z-index: 5; overflow: hidden;'>
                        {html_elementos}
                    </div>
                </div>
                """

            p_frente = piezas.get("frente", {})
            p_espalda = piezas.get("espalda", {})
            p_cuello = piezas.get("cuello", {})
            p_manga_izq = piezas.get("manga_izq", {})
            p_manga_der = piezas.get("manga_der", {})

            canvas_layout_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body, html {{ margin: 0; padding: 0; width: 100%; height: 100%; background-color: #181818; overflow: hidden; }}
                    .viewport {{ width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; }}
                    .zoom-container {{ transform: scale({st.session_state.zoom / 100}); transform-origin: center; display: flex; gap: 15px; align-items: center; justify-content: center; width: 100%; height: 100%; }}
                    .pieza-box {{ background: #222; border-radius: 4px; border: 1px solid #333; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 4px; position: relative; overflow: hidden; }}
                    .label {{ font-size: 9px; color: #aaa; margin-top: 2px; text-align: center; }}
                    .col-grande {{ width: 130px; height: 320px; }}
                    .col-derecha {{ display: flex; flex-direction: column; gap: 10px; width: 110px; height: 320px; justify-content: space-between; }}
                    .sub-pieza {{ width: 100%; flex: 1; }}
                </style>
                <script>
                    let activeItem = null;
                    let activeZone = null;
                    let startX = 0, startY = 0;
                    let isResizing = false;
                    let startWidth = 0, startHeight = 0;

                    function startDrag(e, piezaName, elemId) {{
                        if (isResizing) return;
                        e.preventDefault();
                        activeItem = document.getElementById('item_' + piezaName + '_' + elemId);
                        activeZone = document.getElementById('zone_' + piezaName);
                        activeItem.style.cursor = 'grabbing';
                        
                        startX = e.clientX;
                        startY = e.clientY;

                        document.onmousemove = elementDrag;
                        document.onmouseup = closeDragElement;
                    }}

                    function elementDrag(e) {{
                        e.preventDefault();
                        if (!activeItem || !activeZone) return;

                        const rect = activeZone.getBoundingClientRect();
                        const dx = e.clientX - startX;
                        const dy = e.clientY - startY;

                        startX = e.clientX;
                        startY = e.clientY;

                        let currentLeft = activeItem.offsetLeft + dx;
                        let currentTop = activeItem.offsetTop + dy;

                        let percentX = (currentLeft / rect.width) * 100;
                        let percentY = (currentTop / rect.height) * 100;

                        activeItem.style.left = percentX + '%';
                        activeItem.style.top = percentY + '%';
                    }}

                    function startResize(e, piezaName, elemId) {{
                        e.stopPropagation();
                        e.preventDefault();
                        isResizing = true;
                        activeItem = document.getElementById('item_' + piezaName + '_' + elemId);
                        
                        startX = e.clientX;
                        startY = e.clientY;
                        startWidth = activeItem.offsetWidth;
                        startHeight = activeItem.offsetHeight;

                        document.onmousemove = elementResize;
                        document.onmouseup = closeResizeElement;
                    }}

                    function elementResize(e) {{
                        e.preventDefault();
                        if (!activeItem) return;

                        const dx = e.clientX - startX;
                        const dy = e.clientY - startY;

                        let newWidth = Math.max(20, startWidth + dx);
                        let newHeight = Math.max(20, startHeight + dy);

                        activeItem.style.width = newWidth + 'px';
                        activeItem.style.height = newHeight + 'px';
                    }}

                    function closeResizeElement() {{
                        isResizing = false;
                        if (activeItem) {{
                            activeItem.style.cursor = 'grab';
                        }}
                        document.onmousemove = null;
                        document.onmouseup = null;
                    }}

                    function closeDragElement() {{
                        if (activeItem) {{
                            activeItem.style.cursor = 'grab';
                        }}
                        document.onmousemove = null;
                        document.onmouseup = null;
                    }}
                </script>
            </head>
            <body>
                <div class="viewport">
                    <div class="zoom-container">
                        <!-- Frente -->
                        <div class="pieza-box col-grande">
                            <div style="width:100%; height: 92%;">
                                {render_capas_pieza(p_frente, "frente")}
                            </div>
                            <div class="label">Frente</div>
                        </div>
                        <!-- Espalda -->
                        <div class="pieza-box col-grande">
                            <div style="width:100%; height: 92%;">
                                {render_capas_pieza(p_espalda, "espalda")}
                            </div>
                            <div class="label">Espalda</div>
                        </div>
                        <!-- Columna Derecha: Cuello y Mangas -->
                        <div class="col-derecha">
                            <div class="pieza-box sub-pieza" style="height: 28%;">
                                <div style="width:100%; height: 85%;">
                                    {render_capas_pieza(p_cuello, "cuello")}
                                </div>
                                <div class="label">Cuello</div>
                            </div>
                            <div class="pieza-box sub-pieza" style="height: 33%;">
                                <div style="width:100%; height: 85%;">
                                    {render_capas_pieza(p_manga_izq, "manga_izq")}
                                </div>
                                <div class="label">Manga Izquierda</div>
                            </div>
                            <div class="pieza-box sub-pieza" style="height: 33%;">
                                <div style="width:100%; height: 85%;">
                                    {render_capas_pieza(p_manga_der, "manga_der")}
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

    # 4. Panel Derecho (Visor 3D Interactivo con Three.js)
    with col_right:
        with st.container(border=True):
            textura_frente_b64 = generar_textura_3d_frente(p_frente)

            # Visor 3D interactivo garantizado usando Three.js integrado
            threejs_viewer_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ margin: 0; background-color: #141414; overflow: hidden; }}
                    #canvas3d {{ width: 100%; height: 160px; display: block; }}
                </style>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
            </head>
            <body>
                <div id="canvas3d"></div>
                <script>
                    const container = document.getElementById('canvas3d');
                    const scene = new THREE.Scene();
                    scene.background = new THREE.Color(0x141414);

                    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
                    camera.position.z = 3.8;

                    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
                    renderer.setSize(container.clientWidth, container.clientHeight);
                    container.appendChild(renderer.domElement);

                    // Luces ambientales y direccionales para dar relieve
                    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
                    scene.add(ambientLight);

                    const dirLight = new THREE.DirectionalLight(0xffffff, 0.6);
                    dirLight.position.set(5, 5, 5);
                    scene.add(dirLight);

                    // Grupo para rotar el modelo en 3D
                    const modelGroup = new THREE.Group();
                    scene.add(modelGroup);

                    // Crear la geometría de la camisa / panel frontal 3D texturizado
                    const geometry = new THREE.PlaneGeometry(1.8, 2.2);
                    const material = new THREE.MeshStandardMaterial({{ color: 0xffffff, roughness: 0.4 }});
                    const mesh = new THREE.Mesh(geometry, material);
                    modelGroup.add(mesh);

                    // Cargar la textura en tiempo real desde Base64
                    const b64Data = "{textura_frente_b64}";
                    if (b64Data) {{
                        const textureLoader = new THREE.TextureLoader();
                        textureLoader.load('data:image/png;base64,' + b64Data, function(texture) {{
                            texture.generateMipmaps = true;
                            texture.minFilter = THREE.LinearMipmapLinearFilter;
                            material.map = texture;
                            material.needsUpdate = true;
                        }});
                    }}

                    // Interactividad de rotación con mouse / touch
                    let isDragging = false;
                    let previousMousePosition = {{ x: 0, y: 0 }};

                    container.addEventListener('mousedown', (e) => {{
                        isDragging = true;
                        previousMousePosition = {{ x: e.clientX, y: e.clientY }};
                    }});

                    window.addEventListener('mousemove', (e) => {{
                        if (!isDragging) return;
                        const deltaX = e.clientX - previousMousePosition.x;
                        const deltaY = e.clientY - previousMousePosition.y;

                        modelGroup.rotation.y += deltaX * 0.01;
                        modelGroup.rotation.x += deltaY * 0.01;

                        previousMousePosition = {{ x: e.clientX, y: e.clientY }};
                    }});

                    window.addEventListener('mouseup', () => {{ isDragging = false; }});

                    // Animación de rotación automática suave si no se interactúa
                    function animate() {{
                        requestAnimationFrame(animate);
                        if (!isDragging) {{
                            modelGroup.rotation.y += 0.005;
                        }}
                        renderer.render(scene, camera);
                    }}
                    animate();
                </script>
            </body>
            </html>
            """
            st.components.v1.html(threejs_viewer_html, height=170)

            st.markdown("<div style='font-size: 12px; font-weight: bold; margin-top: 4px;'>Color de Base</div>", unsafe_allow_html=True)
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
    
    with st.expander("👕 Configurar Patrón Base por Piezas", expanded=True):
        config_actual = obtener_configuracion_activa()
        nuevo_nombre = st.text_input("Nombre del Modelo / Prenda", config_actual.get("nombre_modelo", "Camisa Estándar"))
        
        st.markdown("---")
        st.markdown("##### Subir Imágenes Base de las Piezas del Patrón")
        
        up_frente = st.file_uploader("Frente", type=["svg", "png", "jpg", "jpeg"], key="up_f")
        up_espalda = st.file_uploader("Espalda", type=["svg", "png", "jpg", "jpeg"], key="up_e")
        up_cuello = st.file_uploader("Cuello", type=["svg", "png", "jpg", "jpeg"], key="up_c")
        up_manga_izq = st.file_uploader("Manga Izquierda", type=["svg", "png", "jpg", "jpeg"], key="up_mi")
        up_manga_der = st.file_uploader("Manga Derecha", type=["svg", "png", "jpg", "jpeg"], key="up_md")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("💾 Guardar Patrón Base"):
                try:
                    piezas_actuales = config_actual.get("piezas", {})
                    
                    def actualizar_pieza_base(up_f, key_name):
                        if up_f:
                            b64, tipo = procesar_archivo_subido(up_f)
                            if key_name not in piezas_actuales:
                                piezas_actuales[key_name] = {"b64": "", "tipo": "raster", "elementos": []}
                            piezas_actuales[key_name]["b64"] = b64
                            piezas_actuales[key_name]["tipo"] = tipo

                    actualizar_pieza_base(up_frente, "frente")
                    actualizar_pieza_base(up_espalda, "espalda")
                    actualizar_pieza_base(up_cuello, "cuello")
                    actualizar_pieza_base(up_manga_izq, "manga_izq")
                    actualizar_pieza_base(up_manga_der, "manga_der")
                    
                    db.collection("config_estudio").document("modelo_actual").set({
                        "nombre_modelo": nuevo_nombre,
                        "piezas": piezas_actuales,
                        "actualizado": datetime.now()
                    }, merge=True)
                    st.success("¡Patrón base guardado con éxito!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
        with col_btn2:
            if st.button("🗑️ Limpiar Elementos de Diseño"):
                try:
                    piezas_actuales = config_actual.get("piezas", {})
                    for p in piezas_actuales.values():
                        if isinstance(p, dict):
                            p["elementos"] = []
                    db.collection("config_estudio").document("modelo_actual").update({
                        "piezas": piezas_actuales
                    })
                    st.success("¡Elementos de diseño limpiados correctamente!")
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
    except Exception as e:
        st.error(f"Error al cargar pedidos: {e}")
