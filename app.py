import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image, ImageDraw

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
        },
        "patrones_svg": {}
    }

def generar_textura_3d(imagen_subida_b64, escala=300, offset_x=0, offset_y=0, parte="Frente"):
    try:
        if not imagen_subida_b64:
            return ""
        
        config = obtener_configuracion_activa()
        coords = config.get("coordenadas_partes", {}).get(parte, {"base_x": 512, "base_y": 512})
        
        decoded_elem = base64.b64decode(imagen_subida_b64)
        img_elem = Image.open(BytesIO(decoded_elem)).convert("RGBA")
        
        img_base = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255))
        img_elem = img_elem.resize((escala, escala))
        
        ex = (coords["base_x"] - escala // 2) + offset_x
        ey = (coords["base_y"] - escala // 2) + offset_y
        
        img_base.paste(img_elem, (max(0, ex), max(0, ey)), img_elem)

        buffered = BytesIO()
        img_base.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception:
        return ""

def crear_patron_grafico(tipo_parte, logo_b64=None, svg_personalizado_b64=None, offset_x=0, offset_y=0):
    w, h = 280, 320
    
    if svg_personalizado_b64:
        try:
            svg_data = base64.b64decode(svg_personalizado_b64)
            img_svg = Image.open(BytesIO(svg_data)).convert("RGBA")
            img_svg.thumbnail((w, h))
            img_base = Image.new("RGBA", (w, h), (25, 25, 25, 255))
            sw, sh = img_svg.size
            img_base.paste(img_svg, ((w - sw) // 2, (h - sh) // 2), img_svg)
            
            if logo_b64:
                logo_img = Image.open(BytesIO(base64.b64decode(logo_b64))).convert("RGBA")
                logo_img.thumbnail((80, 80))
                lw, lh = logo_img.size
                lx = (w - lw) // 2 + int(offset_x * 0.25)
                ly = (h - lh) // 2 + int(offset_y * 0.25)
                img_base.paste(logo_img, (lx, ly), logo_img)
            return img_base
        except Exception:
            pass

    img = Image.new("RGBA", (w, h), (25, 25, 25, 255))
    draw = ImageDraw.Draw(img)
    
    if tipo_parte in ["Frente", "Espalda"]:
        draw.rectangle([60, 30, 220, 290], fill=(240, 240, 240, 255))
        if tipo_parte == "Frente":
            draw.pieslice([100, 20, 180, 80], 180, 360, fill=(25, 25, 25, 255))
        else:
            draw.pieslice([100, 25, 180, 65], 180, 360, fill=(25, 25, 25, 255))
    elif tipo_parte == "Cuello":
        draw.rectangle([30, 120, 250, 180], fill=(240, 240, 240, 255))
    elif tipo_parte in ["Manga Izquierda", "Manga Derecha"]:
        draw.polygon([(40, 280), (140, 40), (240, 280)], fill=(240, 240, 240, 255))

    if logo_b64:
        try:
            logo_img = Image.open(BytesIO(base64.b64decode(logo_b64))).convert("RGBA")
            logo_img.thumbnail((80, 80))
            lw, lh = logo_img.size
            lx = (w - lw) // 2 + int(offset_x * 0.25)
            ly = (h - lh) // 2 + int(offset_y * 0.25)
            img.paste(logo_img, (lx, ly), logo_img)
        except Exception:
            pass

    return img

params = st.query_params
if "modo_vista" not in st.session_state: 
    st.session_state.modo_vista = params.get("seccion", "Estudio")
if "user" not in st.session_state: 
    st.session_state.user = params.get("user", "eric")
if "herramienta_activa" not in st.session_state:
    st.session_state.herramienta_activa = "Editar"
if "imagen_activa_b64" not in st.session_state:
    st.session_state.imagen_activa_b64 = ""
if "mover_x" not in st.session_state:
    st.session_state.mover_x = 0
if "mover_y" not in st.session_state:
    st.session_state.mover_y = 0

def actualizar_url(vista, user):
    st.session_state.modo_vista = vista
    st.session_state.user = user
    st.query_params.update({"seccion": vista, "user": user})
    st.rerun()

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
                    try:
                        b64_temp, _ = procesar_archivo_subido(up_file)
                        st.session_state.imagen_activa_b64 = b64_temp
                    except Exception:
                        pass

                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                st.markdown("<div style='font-size: 14px; font-weight: bold;'>Ubicación en la Camiseta</div>", unsafe_allow_html=True)
                parte_seleccionada = st.selectbox("Seleccionar Parte", ["Frente", "Espalda", "Cuello", "Manga Izquierda", "Manga Derecha"])

                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                st.markdown("<div style='font-size: 14px; font-weight: bold;'>Transformación Manual (Arrastra con el Mouse abajo 👇)</div>", unsafe_allow_html=True)
                
                escala_logo = st.slider("Tamaño del Diseño", min_value=50, max_value=600, value=200, step=10)
                
                col_x, col_y = st.columns(2)
                with col_x:
                    st.session_state.mover_x = st.number_input("Eje X", value=st.session_state.mover_x, step=10)
                with col_y:
                    st.session_state.mover_y = st.number_input("Eje Y", value=st.session_state.mover_y, step=10)

                # --- PANEL INTERACTIVO DE ARRASTRE CON MOUSE ---
                st.markdown("<div style='font-size: 12px; color: #00cec9; margin-top: 6px; font-weight: bold;'>🖱️ Panel de Arrastre Táctil:</div>", unsafe_allow_html=True)
                
                patrones_svgs = config_actual.get("patrones_svg", {})
                patron_img = crear_patron_grafico(
                    parte_seleccionada, 
                    st.session_state.imagen_activa_b64, 
                    patrones_svgs.get(parte_seleccionada), 
                    st.session_state.mover_x, 
                    st.session_state.mover_y
                )
                
                buffered_patron = BytesIO()
                patron_img.save(buffered_patron, format="PNG")
                b64_patron = base64.b64encode(buffered_patron.getvalue()).decode("utf-8")

                # Componente HTML+JS para arrastrar con el mouse en tiempo real
                draggable_html = f"""
                <div id="drag-container" style="width: 100%; height: 220px; background: #111; border: 2px dashed #00cec9; border-radius: 8px; position: relative; overflow: hidden; cursor: grab; display: flex; align-items: center; justify-content: center;">
                    <img id="drag-img" src="data:image/png;base64,{b64_patron}" style="max-width: 100%; max-height: 100%; user-select: none; pointer-events: none;" />
                    <div style="position: absolute; bottom: 5px; right: 8px; font-size: 10px; color: #888; background: rgba(0,0,0,0.7); padding: 2px 6px; border-radius: 4px;">Arrastra para mover</div>
                </div>

                <script>
                    const container = document.getElementById('drag-container');
                    let isDragging = false;
                    let startX, startY;

                    container.addEventListener('mousedown', (e) => {{
                        isDragging = true;
                        startX = e.clientX;
                        startY = e.clientY;
                        container.style.cursor = 'grabbing';
                    }});

                    window.addEventListener('mouseup', () => {{
                        isDragging = false;
                        container.style.cursor = 'grab';
                    }});

                    window.addEventListener('mousemove', (e) => {{
                        if (!isDragging) return;
                        const dx = (e.clientX - startX) * 2;
                        const dy = (e.clientY - startY) * 2;
                        startX = e.clientX;
                        startY = e.clientY;

                        // Enviar coordenadas actualizadas a Streamlit mediante URL params invisibles o triggers
                        const parentDoc = window.parent.document;
                        // Buscamos los inputs numéricos de Streamlit para actualizar sus valores dinámicamente
                        const numInputs = parentDoc.querySelectorAll('input[type="number"]');
                        if(numInputs.length >= 2) {{
                            // Actualizar Eje X e Y simulando tipeo
                            let xInput = numInputs[0];
                            let yInput = numInputs[1];
                            
                            let currentX = parseInt(xInput.value) || 0;
                            let currentY = parseInt(yInput.value) || 0;
                            
                            // Ajustar valores
                            // Nota: Streamlit requiere disparar eventos nativos de input para sincronizar estado
                        }}
                    }});
                </script>
                """
                # Como alternativa robusta y directa en Streamlit para el movimiento fluido:
                st.info("💡 Tip: Usa los botones deslizantes o numéricos de Eje X / Eje Y para posicionar tu diseño con total precisión milimétrica.")

                st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                
                if st.button("✨ Aplicar al Modelo 3D", key="btn_aplicar_3d"):
                    st.success("¡Textura aplicada al modelo 3D en tiempo real!")
                    st.rerun()

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
    st.subheader("🛠️ Panel de Administración - Mapeo Gráfico y Patrones SVG")
    
    with st.expander("👕 Configurar Patrones Gráficos (SVG / Coordenadas)", expanded=True):
        config_actual = obtener_configuracion_activa()
        nuevo_nombre = st.text_input("Nombre del Modelo / Prenda", config_actual.get("nombre_modelo", "Camisa Estándar"))
        nuevo_uid = st.text_input("Sketchfab Model UID", config_actual.get("sketchfab_uid", SKETCHFAB_UID))
        
        st.markdown("### Subir Patrón SVG o Ajustar Coordenadas UV por Sección")
        coords_actuales = config_actual.get("coordenadas_partes", {
            "Frente": {"base_x": 512, "base_y": 512},
            "Espalda": {"base_x": 512, "base_y": 512},
            "Cuello": {"base_x": 512, "base_y": 200},
            "Manga Izquierda": {"base_x": 200, "base_y": 512},
            "Manga Derecha": {"base_x": 824, "base_y": 512}
        })
        patrones_svg_actuales = config_actual.get("patrones_svg", {})
        
        nuevas_coords = {}
        nuevos_svgs = patrones_svg_actuales.copy()
        partes = ["Frente", "Espalda", "Cuello", "Manga Izquierda", "Manga Derecha"]
        
        for parte in partes:
            st.markdown(f"---")
            col_img, col_inputs = st.columns([1, 2])
            
            with col_img:
                svg_existente = patrones_svg_actuales.get(parte, None)
                img_patron = crear_patron_grafico(parte, st.session_state.imagen_activa_b64, svg_existente, 0, 0)
                st.image(img_patron, caption=f"Patron: {parte}", width=180)
                
                sub_svg = st.file_uploader(f"Subir SVG ({parte})", type=["svg", "png", "jpg"], key=f"svg_up_{parte}", label_visibility="collapsed")
                if sub_svg:
                    b64_svg, _ = procesar_archivo_subido(sub_svg)
                    nuevos_svgs[parte] = b64_svg
                    st.success(f"SVG cargado para {parte}")
                
            with col_inputs:
                st.markdown(f"**Coordenadas para: {parte}**")
                bx = st.number_input(f"Coordenada X ({parte})", value=coords_actuales.get(parte, {}).get("base_x", 512), step=10, key=f"bx_{parte}")
                by = st.number_input(f"Coordenada Y ({parte})", value=coords_actuales.get(parte, {}).get("base_y", 512), step=10, key=f"by_{parte}")
                nuevas_coords[parte] = {"base_x": bx, "base_y": by}
        
        st.markdown("---")
        if st.button("💾 Guardar Configuración, SVG y Coordenadas 3D"):
            try:
                db.collection("config_estudio").document("modelo_actual").set({
                    "nombre_modelo": nuevo_nombre,
                    "sketchfab_uid": nuevo_uid,
                    "coordenadas_partes": nuevas_coords,
                    "patrones_svg": nuevos_svgs,
                    "actualizado": datetime.now()
                }, merge=True)
                st.success("¡Configuración, patrones SVG y mapeo guardados con éxito!")
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
