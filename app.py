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
        "coordenadas_partes": {
            "Frente": {"base_x": 512, "base_y": 512},
            "Espalda": {"base_x": 512, "base_y": 512},
            "Cuello": {"base_x": 512, "base_y": 200},
            "Manga Izquierda": {"base_x": 200, "base_y": 512},
            "Manga Derecha": {"base_x": 824, "base_y": 512}
        }
    }

def generar_textura_3d(imagen_subida_b64, escala=300, offset_x=0, offset_y=0, parte="Frente"):
    try:
        if not imagen_subida_b64:
            return ""
        
        config = obtener_configuracion_activa()
        coords = config.get("coordenadas_partes", {}).get(parte, {"base_x": 512, "base_y": 512})
        
        decoded_elem = base64.b64decode(imagen_subida_b64)
        img_elem = Image.open(BytesIO(decoded_elem)).convert("RGBA")
        
        # Lienzo base de la textura UV (1024x1024) en blanco
        img_base = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255))
        
        # Redimensionar según el tamaño especificado
        img_elem = img_elem.resize((escala, escala))
        
        # Posición base de la parte seleccionada + desplazamiento manual (offset)
        ex = (coords["base_x"] - escala // 2) + offset_x
        ey = (coords["base_y"] - escala // 2) + offset_y
        
        img_base.paste(img_elem, (max(0, ex), max(0, ey)), img_elem)

        buffered = BytesIO()
        img_base.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception:
        return ""

params = st.query_params
if "modo_vista" not in st.session_state: 
    st.session_state.modo_vista = params.get("seccion", "Estudio")
if "user" not in st.session_state: 
    st.session_state.user = params.get("user", "eric")
if "herramienta_activa" not in st.session_state:
    st.session_state.herramienta_activa = "Editar"
if "imagen_activa_b64" not in st.session_state:
    st.session_state.imagen_activa_b64 = ""

def actualizar_url(vista, user):
    st.session_state.modo_vista = vista
    st.session_state.user = user
    st.query_params.update({"seccion": vista, "user": user})
    st.rerun()

# Añadido tu nombre legal y variaciones para garantizar acceso al Panel Admin
ADMINS_AUTORIZADOS = ["pixel2580", "eric", "eric ramon espinal cruz"]

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
                    st.markdown("<div style='font-size: 12px; color: #aaa; margin-top: 4px;'>Vista previa:</div>", unsafe_allow_html=True)
                    try:
                        if up_file.name.lower().endswith(('png', 'jpg', 'jpeg')):
                            st.image(up_file, width=140)
                        elif up_file.name.lower().endswith('svg'):
                            st.caption("📄 Archivo SVG cargado")
                    except Exception:
                        pass

                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                st.markdown("<div style='font-size: 14px; font-weight: bold;'>Ubicación en la Camiseta</div>", unsafe_allow_html=True)
                parte_seleccionada = st.selectbox("Seleccionar Parte", ["Frente", "Espalda", "Cuello", "Manga Izquierda", "Manga Derecha"])

                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                st.markdown("<div style='font-size: 14px; font-weight: bold;'>Transformación Manual</div>", unsafe_allow_html=True)
                
                escala_logo = st.slider("Tamaño del Diseño", min_value=50, max_value=600, value=200, step=10)
                
                col_x, col_y = st.columns(2)
                with col_x:
                    mover_x = st.number_input("Eje X", value=0, step=10)
                with col_y:
                    mover_y = st.number_input("Eje Y", value=0, step=10)

                st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                
                if st.button("✨ Aplicar al Modelo 3D", key="btn_aplicar_3d"):
                    if up_file:
                        try:
                            b64, _ = procesar_archivo_subido(up_file)
                            st.session_state.imagen_activa_b64 = b64
                            st.session_state.escala_logo = escala_logo
                            st.session_state.mover_x = mover_x
                            st.session_state.mover_y = mover_y
                            st.session_state.parte_seleccionada = parte_seleccionada
                            st.success("¡Textura aplicada con éxito!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
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
            
            e_val = st.session_state.get("escala_logo", 200)
            x_val = st.session_state.get("mover_x", 0)
            y_val = st.session_state.get("mover_y", 0)
            p_val = st.session_state.get("parte_seleccionada", "Frente")
            
            textura_b64 = generar_textura_3d(st.session_state.imagen_activa_b64, e_val, x_val, y_val, p_val)

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
    
    with st.expander("👕 Configurar Coordenadas UV por Parte de la Camiseta", expanded=True):
        config_actual = obtener_configuracion_activa()
        nuevo_nombre = st.text_input("Nombre del Modelo / Prenda", config_actual.get("nombre_modelo", "Camisa Estándar"))
        nuevo_uid = st.text_input("Sketchfab Model UID", config_actual.get("sketchfab_uid", SKETCHFAB_UID))
        
        st.markdown("### Coordenadas del Mapa UV (Lienzo 1024x1024)")
        coords_actuales = config_actual.get("coordenadas_partes", {
            "Frente": {"base_x": 512, "base_y": 512},
            "Espalda": {"base_x": 512, "base_y": 512},
            "Cuello": {"base_x": 512, "base_y": 200},
            "Manga Izquierda": {"base_x": 200, "base_y": 512},
            "Manga Derecha": {"base_x": 824, "base_y": 512}
        })
        
        nuevas_coords = {}
        for parte in ["Frente", "Espalda", "Cuello", "Manga Izquierda", "Manga Derecha"]:
            st.markdown(f"**{parte}**")
            col_cx, col_cy = st.columns(2)
            with col_cx:
                bx = st.number_input(f"Base X ({parte})", value=coords_actuales.get(parte, {}).get("base_x", 512), step=10, key=f"bx_{parte}")
            with col_cy:
                by = st.number_input(f"Base Y ({parte})", value=coords_actuales.get(parte, {}).get("base_y", 512), step=10, key=f"by_{parte}")
            nuevas_coords[parte] = {"base_x": bx, "base_y": by}
        
        if st.button("💾 Guardar Configuración y Coordenadas 3D"):
            try:
                db.collection("config_estudio").document("modelo_actual").set({
                    "nombre_modelo": nuevo_nombre,
                    "sketchfab_uid": nuevo_uid,
                    "coordenadas_partes": nuevas_coords,
                    "actualizado": datetime.now()
                }, merge=True)
                st.success("¡Configuración y mapeo guardados con éxito!")
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
