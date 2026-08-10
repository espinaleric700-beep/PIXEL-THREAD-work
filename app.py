import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Pixel Thread - Mockups 3D",
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

def generar_textura_3d(imagen_subida_b64, escala=300, offset_x=0, offset_y=0):
    try:
        if not imagen_subida_b64:
            return ""
        
        decoded_elem = base64.b64decode(imagen_subida_b64)
        img_elem = Image.open(BytesIO(decoded_elem)).convert("RGBA")
        
        # Lienzo base de la textura UV (1024x1024) en blanco
        img_base = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255))
        
        # Redimensionar según el tamaño especificado
        img_elem = img_elem.resize((escala, escala))
        
        # Calcular posición centrada más los desplazamientos manuales
        ex = (1024 - escala) // 2 + offset_x
        ey = (1024 - escala) // 2 + offset_y
        
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
if "herramienta_activa" not in st.session_state:
    st.session_state.herramienta_activa = "Editar"
if "imagen_activa_b64" not in st.session_state:
    st.session_state.imagen_activa_b64 = ""

# Estados para la posición manual interactiva
if "pos_x" not in st.session_state:
    st.session_state.pos_x = 0
if "pos_y" not in st.session_state:
    st.session_state.pos_y = 0
if "tamano_logo" not in st.session_state:
    st.session_state.tamano_logo = 300

def actualizar_url(vista, user):
    st.session_state.modo_vista = vista
    st.session_state.user = user
    st.query_params.update({"seccion": vista, "user": user})
    st.rerun()

ADMINS_AUTORIZADOS = ["pixel2580", "eric"]

# --- BARRA SUPERIOR ---
top_c1, top_c2, top_c3 = st.columns([3, 6, 3])
with top_c1:
    st.markdown("<h4 style='margin: 0; color: #fff; font-size: 16px;'>⚡ Pixel Thread - Estudio 3D</h4>", unsafe_allow_html=True)
with top_c2:
    if st.session_state.user.strip().lower() in [a.lower() for a in ADMINS_AUTORIZADOS]:
        if st.button("🛠️ Panel Admin", key="btn_admin_top"):
            actualizar_url("Admin" if st.session_state.modo_vista != "Admin" else "Estudio", st.session_state.user)
with top_c3:
    if st.button("Guardar Proyecto", key="btn_save_top"):
        st.session_state.guardar_trigger = True

st.markdown("<div style='margin-bottom: 6px;'></div>", unsafe_allow_html=True)

# =========================================================
# VISTA DE ESTUDIO
# =========================================================
if st.session_state.modo_vista == "Estudio":

    config_actual = obtener_configuracion_activa()
    sk_uid = config_actual.get("sketchfab_uid", SKETCHFAB_UID)

    col_iconos, col_panel, col_visor = st.columns([0.6, 3.4, 6.0], gap="small")

    with col_iconos:
        with st.container(border=True):
            if st.button("🎛️", key="ico_edit"): st.session_state.herramienta_activa = "Editar"; st.rerun()
            if st.button("📦", key="ico_mod"): st.session_state.herramienta_activa = "Modelos"; st.rerun()
            if st.button("🎨", key="ico_dis"): st.session_state.herramienta_activa = "Diseno"; st.rerun()
            if st.button("🌄", key="ico_fon"): st.session_state.herramienta_activa = "Fondo"; st.rerun()
            if st.button("✨", key="ico_ia"): st.session_state.herramienta_activa = "IA"; st.rerun()

    with col_panel:
        with st.container(border=True):
            if st.session_state.herramienta_activa == "Editar":
                st.markdown("<div style='font-size: 15px; font-weight: bold;'>Cargar imágenes</div>", unsafe_allow_html=True)
                
                up_file = st.file_uploader("Seleccionar archivo", type=["png", "jpg", "jpeg", "svg"], label_visibility="collapsed")
                
                if up_file:
                    try:
                        b64_temp, _ = procesar_archivo_subido(up_file)
                        st.session_state.imagen_activa_b64 = b64_temp
                    except Exception:
                        pass

                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                st.markdown("<div style='font-size: 14px; font-weight: bold;'>Transformación Manual</div>", unsafe_allow_html=True)
                st.caption("Arrastra la imagen directamente en el cuadro interactivo de abajo o ajusta su tamaño.")

                st.session_state.tamano_logo = st.slider("Tamaño del Diseño", min_value=50, max_value=600, value=st.session_state.tamano_logo, step=10)

                # Vista previa interactiva donde se puede arrastrar el logo con el ratón
                img_src_prev = f"data:image/png;base64,{st.session_state.imagen_activa_b64}" if st.session_state.imagen_activa_b64 else ""
                
                interactive_canvas_html = f"""
                <div id="drop-area" style="width: 100%; height: 220px; background-color: #111; border: 2px dashed #444; border-radius: 8px; position: relative; overflow: hidden; display: flex; align-items: center; justify-content: center;">
                    <div id="drag-item" style="position: absolute; width: {st.session_state.tamano_logo}px; height: {st.session_state.tamano_logo}px; left: calc(50% - {st.session_state.tamano_logo/2}px + {st.session_state.pos_x}px); top: calc(50% - {st.session_state.tamano_logo/2}px + {st.session_state.pos_y}px); cursor: grab; background-image: url('{img_src_prev}'); background-size: contain; background-repeat: no-repeat; background-position: center;"></div>
                    <span style="color: #666; font-size: 11px; pointer-events: none; position: absolute; bottom: 5px;">Arrastra la imagen aquí</span>
                </div>
                <script>
                    const item = document.getElementById('drag-item');
                    const area = document.getElementById('drop-area');
                    let isDragging = false;
                    let startX, startY;
                    let posX = {st.session_state.pos_x};
                    let posY = {st.session_state.pos_y};

                    item.addEventListener('mousedown', (e) => {{
                        isDragging = true;
                        startX = e.clientX - posX;
                        startY = e.clientY - posY;
                        item.style.cursor = 'grabbing';
                        e.preventDefault();
                    }});

                    window.addEventListener('mousemove', (e) => {{
                        if (!isDragging) return;
                        posX = e.clientX - startX;
                        posY = e.clientY - startY;
                        item.style.left = `calc(50% - {st.session_state.tamano_logo/2}px + ${{posX}}px)`;
                        item.style.top = `calc(50% - {st.session_state.tamano_logo/2}px + ${{posY}}px)`;
                    }});

                    window.addEventListener('mouseup', () => {{
                        if (isDragging) {{
                            isDragging = false;
                            item.style.cursor = 'grab';
                            // Enviar posiciones actualizadas a Streamlit mediante URL params ocultas o recarga suave si es necesario
                        }}
                    }});
                </script>
                """
                st.components.v1.html(interactive_canvas_html, height=235)

                # Inputs numéricos sincronizados para posición exacta
                col_px, col_py = st.columns(2)
                with col_px:
                    st.session_state.pos_x = st.number_input("Eje X", value=st.session_state.pos_x, step=5)
                with col_py:
                    st.session_state.pos_y = st.number_input("Eje Y", value=st.session_state.pos_y, step=5)

                st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                
                if st.button("✨ Aplicar al Modelo 3D", key="btn_aplicar_3d"):
                    if st.session_state.imagen_activa_b64:
                        st.success("¡Textura posicionada y aplicada con éxito!")
                        st.rerun()
                    else:
                        st.warning("Selecciona una imagen primero.")

                if st.session_state.imagen_activa_b64:
                    if st.button("🗑️ Quitar Textura"):
                        st.session_state.imagen_activa_b64 = ""
                        st.success("Textura removida.")
                        st.rerun()

                st.markdown("<hr style='margin: 12px 0;'>", unsafe_allow_html=True)
                nombre_proyecto = st.text_input("Nombre del Proyecto", "Proyecto Pixel 3D")
                
                if st.button("🚀 Producción", key="btn_prod"):
                    try:
                        lista_archivos = []
                        if st.session_state.imagen_activa_b64:
                            lista_archivos.append({"nombre": "logo_ajustado.png", "data": st.session_state.imagen_activa_b64})
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

                st.markdown("<hr style='margin: 12px 0;'>", unsafe_allow_html=True)
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

            elif st.session_state.herramienta_activa == "Modelos":
                st.markdown("<div style='font-size: 15px; font-weight: bold;'>Modelos 3D</div>", unsafe_allow_html=True)
                st.info("Modelo activo: Camisa Estándar")
            elif st.session_state.herramienta_activa == "Diseno":
                st.markdown("<div style='font-size: 15px; font-weight: bold;'>Diseño</div>", unsafe_allow_html=True)
                st.text_input("Texto Personalizado", "Pixel Thread")
            elif st.session_state.herramienta_activa == "Fondo":
                st.markdown("<div style='font-size: 15px; font-weight: bold;'>Fondo</div>", unsafe_allow_html=True)
                st.selectbox("Ambiente", ["Oscuro", "Gris", "Claro"])
            elif st.session_state.herramienta_activa == "IA":
                st.markdown("<div style='font-size: 15px; font-weight: bold;'>Diseño IA</div>", unsafe_allow_html=True)
                st.text_area("Prompt", "Logotipo bordado")

    with col_visor:
        with st.container(border=True):
            st.markdown("<div style='font-size: 14px; font-weight: bold; margin-bottom: 8px;'>Visualizador 3D en Vivo</div>", unsafe_allow_html=True)
            
            textura_b64 = generar_textura_3d(st.session_state.imagen_activa_b64, st.session_state.tamano_logo, st.session_state.pos_x, st.session_state.pos_y)

            sketchfab_viewer_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ margin: 0; background-color: #141414; overflow: hidden; }}
                    #sketchfab-iframe {{ width: 100%; height: 580px; border: none; display: block; }}
                </style>
                <script src="https://static.sketchfab.com/api/sketchfab-viewer-1.12.1.js"></script>
            </head>
            <body>
                <iframe id="sketchfab-iframe" src="" allow="autoplay; fullscreen; vr" xr-spatial-tracking execution-while-out-of-viewport execution-while-not-rendered web-share allowfullscreen></iframe>
                
                <script>
                    var iframe = document.getElementById('sketchfab-iframe');
                    var urlid = '{sk_uid}';
                    var client = new Sketchfab(iframe);
                    var base64Tex = "data:image/png;base64,{textura_b64}";

                    client.init(urlid, {{
                        success: function onSuccess(api) {{
                            api.start();
                            api.addEventListener('viewerready', function() {{
                                if ("{textura_b64}" !== "") {{
                                    api.addTexture(base64Tex, function(err, textureUid) {{
                                        if (!err) {{
                                            api.getMaterialList(function(err, materials) {{
                                                if (!err && materials.length > 0) {{
                                                    var material = materials[0];
                                                    material.channels.AlbedoPBR.texture = {{ uid: textureUid }};
                                                    api.setMaterial(material);
                                                }}
                                            }});
                                        }}
                                    }});
                                }}
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
            st.components.v1.html(sketchfab_viewer_html, height=600)

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
