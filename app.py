from io import BytesIO
import base64
from PIL import Image, ImageOps, ImageDraw
import streamlit as st
import streamlit.components.v1 as components
import requests

# Intentar importar soporte SVG si está disponible
try:
    import cairosvg
    SVG_SUPPORT = True
except ImportError:
    SVG_SUPPORT = False

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Pixel Thread - Personalizador 3D", layout="wide")

# --- GESTIÓN DE ESTADO (SESSION STATE) ---
if "coordenadas_partes" not in st.session_state:
    st.session_state.coordenadas_partes = {
        "Frente": {"base_x": 512, "base_y": 512, "offset_x": 0, "offset_y": 0},
        "Espalda": {"base_x": 512, "base_y": 1536, "offset_x": 0, "offset_y": 0},
        "Mangas": {"base_x": 1536, "base_y": 512, "offset_x": 0, "offset_y": 0},
        "Cuello": {"base_x": 1536, "base_y": 1536, "offset_x": 0, "offset_y": 0}
    }

if "mapeo_archivos_bytes" not in st.session_state:
    st.session_state.mapeo_archivos_bytes = {
        "Frente": None,
        "Espalda": None,
        "Mangas": None,
        "Cuello": None
    }

if "sketchfab_token" not in st.session_state:
    st.session_state.sketchfab_token = "52e167c5a6024ee8b9b8fb8b9a7a89fc"

if "modelo_seleccionado_uid" not in st.session_state:
    st.session_state.modelo_seleccionado_uid = ""

# --- FUNCIONES DE APOYO ---
@st.cache_data(ttl=600)
def obtener_modelos_sketchfab(token):
    if not token:
        return []
    headers = {"Authorization": f"Token {token}"}
    url = "https://api.sketchfab.com/v3/me/models"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("results", [])
        else:
            return []
    except Exception:
        return []

def abrir_imagen_guia(file_bytes, filename, target_size=(1024, 1024)):
    if not file_bytes:
        return Image.new("RGBA", target_size, (255, 255, 255, 0))
    try:
        if filename and filename.lower().endswith(".svg"):
            if SVG_SUPPORT:
                png_bytes = cairosvg.svg2png(bytestring=file_bytes, output_width=target_size[0], output_height=target_size[1])
                return Image.open(BytesIO(png_bytes)).convert("RGBA")
            else:
                return Image.new("RGBA", target_size, (255, 255, 255, 0))
        else:
            img = Image.open(BytesIO(file_bytes)).convert("RGBA")
            return ImageOps.contain(img, target_size, Image.Resampling.LANCZOS)
    except Exception:
        return Image.new("RGBA", target_size, (255, 255, 255, 0))

def generar_textura_limpia_3d(imagen_subida_b64, escala=200, offset_x=0, offset_y=0, parte_activa="Frente"):
    try:
        coords_dict = st.session_state.coordenadas_partes
        canvas_size = (2048, 2048)
        img_textura_limpia = Image.new("RGBA", canvas_size, (0, 0, 0, 0))

        if imagen_subida_b64 and parte_activa in coords_dict:
            decoded_elem = base64.b64decode(imagen_subida_b64)
            img_elem = Image.open(BytesIO(decoded_elem)).convert("RGBA")
            img_elem = ImageOps.contain(img_elem, (escala, escala), Image.Resampling.LANCZOS)
            
            coords = coords_dict.get(parte_activa)
            base_x = coords.get("base_x")
            base_y = coords.get("base_y")
            
            pos_x = (base_x - img_elem.width // 2) + offset_x
            pos_y = (base_y - img_elem.height // 2) + offset_y
            
            img_textura_limpia.alpha_composite(img_elem, (pos_x, pos_y))

        buffered = BytesIO()
        img_textura_limpia.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"Error generando textura limpia 3D: {e}")
        return ""

def generar_mapa_uv_visual(imagen_subida_b64, escala=200, offset_x=0, offset_y=0, parte_activa="Frente"):
    try:
        coords_dict = st.session_state.coordenadas_partes
        canvas_size = (2048, 2048)
        part_size = (1024, 1024)
        img_uv_completo = Image.new("RGBA", canvas_size, (255, 255, 255, 0))

        mapping_positions = {
            "Frente": (0, 0),
            "Espalda": (0, 1024),
            "Mangas": (1024, 0),
            "Cuello": (1024, 1024)
        }

        for parte_nombre, pos in mapping_positions.items():
            datos_guia = st.session_state.mapeo_archivos_bytes.get(parte_nombre)
            if datos_guia:
                file_bytes, filename = datos_guia
                img_parte = abrir_imagen_guia(file_bytes, filename, target_size=part_size)
                img_uv_completo.alpha_composite(img_parte, pos)
            else:
                referencia = Image.new("RGBA", part_size, (245, 245, 245, 255))
                draw = ImageDraw.Draw(referencia)
                draw.rectangle([(0, 0), (1023, 1023)], outline=(200, 200, 200), width=2)
                draw.text((512, 512), f"Sin archivo: {parte_nombre}", fill=(150, 150, 150), anchor="mm")
                img_uv_completo.alpha_composite(referencia, pos)

        if imagen_subida_b64 and parte_activa in coords_dict:
            decoded_elem = base64.b64decode(imagen_subida_b64)
            img_elem = Image.open(BytesIO(decoded_elem)).convert("RGBA")
            img_elem = ImageOps.contain(img_elem, (escala, escala), Image.Resampling.LANCZOS)
            
            coords = coords_dict.get(parte_activa)
            base_x = coords.get("base_x")
            base_y = coords.get("base_y")
            
            pos_x = (base_x - img_elem.width // 2) + offset_x
            pos_y = (base_y - img_elem.height // 2) + offset_y
            
            img_uv_completo.alpha_composite(img_elem, (pos_x, pos_y))

        buffered = BytesIO()
        img_uv_completo.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"Error generando mapa UV visual: {e}")
        return ""

# --- INTERFAZ PRINCIPAL ---
st.title("Personalizador 3D - Pixel Thread")

tab_cliente, tab_admin = st.tabs(["🎨 Personalizador en Vivo", "⚙️ Panel Admin y Configuración UV"])

with tab_cliente:
    col_panel, col_visor = st.columns(2, gap="large")

    with col_panel:
        st.header("Panel de Control")
        parte_seleccionada = st.selectbox("Selecciona la parte de la prenda a editar", ["Frente", "Espalda", "Mangas", "Cuello"])
        escala_logo = st.slider("Tamaño del diseño", 50, 800, 200)
        
        # Recuperar offsets actuales de la parte seleccionada
        current_offset_x = st.session_state.coordenadas_partes[parte_seleccionada]["offset_x"]
        current_offset_y = st.session_state.coordenadas_partes[parte_seleccionada]["offset_y"]

        offset_x = st.slider("Mover Horizontal (X)", -500, 500, current_offset_x, key="slider_x")
        offset_y = st.slider("Mover Vertical (Y)", -500, 500, current_offset_y, key="slider_y")

        # Sincronizar cambios del slider al estado
        st.session_state.coordenadas_partes[parte_seleccionada]["offset_x"] = offset_x
        st.session_state.coordenadas_partes[parte_seleccionada]["offset_y"] = offset_y
        
        archivo_subido = st.file_uploader(f"Sube el diseño para: {parte_seleccionada}", type=["png", "jpg", "jpeg", "svg"])

    imagen_b64 = ""
    if archivo_subido is not None:
        bytes_imagen = archivo_subido.read()
        imagen_b64 = base64.b64encode(bytes_imagen).decode("utf-8")

    textura_3d_limpia_b64 = generar_textura_limpia_3d(
        imagen_subida_b64=imagen_b64, 
        escala=escala_logo, 
        offset_x=offset_x, 
        offset_y=offset_y, 
        parte_activa=parte_seleccionada
    )

    mapa_uv_visual_b64 = generar_mapa_uv_visual(
        imagen_subida_b64=imagen_b64, 
        escala=escala_logo, 
        offset_x=offset_x, 
        offset_y=offset_y, 
        parte_activa=parte_seleccionada
    )

    with col_visor:
        st.header("Visor 3D en Tiempo Real")
        
        if st.session_state.modelo_seleccionado_uid and textura_3d_limpia_b64:
            data_url_textura = f"data:image/png;base64,{textura_3d_limpia_b64}"
            
            sketchfab_html = f"""
            <iframe title="Modelo 3D Sketchfab" id="api-frame" width="100%" height="320px" frameborder="0" allowvr allow="autoplay; fullscreen; xr-spatial-tracking"></iframe>
            <script src="https://static.sketchfab.com/api/sketchfab-viewer-1.12.1.js"></script>
            <script>
                var iframe = document.getElementById('api-frame');
                var uid = '{st.session_state.modelo_seleccionado_uid}';
                var client = new Sketchfab(iframe);

                client.init(uid, {{
                    success: function (api) {{
                        api.start();
                        api.addEventListener('viewerready', function () {{
                            api.addTexture('{data_url_textura}', function (err, textureUid) {{
                                if (!err) {{
                                    api.getMaterialList(function (err, materials) {{
                                        if (!err && materials.length > 0) {{
                                            var material = materials[0];
                                            material.channels.AlbedoPBR.texture = {{
                                                uid: textureUid
                                            }};
                                            api.setMaterial(material);
                                        }}
                                    }});
                                }}
                            }});
                        }});
                    }},
                    error: function () {{
                        console.error('Error al inicializar el visor de Sketchfab');
                    }}
                }});
            </script>
            """
            components.html(sketchfab_html, height=330)
        elif st.session_state.modelo_seleccionado_uid:
            st.info("Generando textura 3D...")
        else:
            st.warning("⚠️ Selecciona un modelo desde la pestaña **Panel Admin y Configuración UV** para visualizarlo.")
        
        st.markdown("---")
        st.subheader("🖱️ Arrastra tu Logo en el Mapa UV")
        st.write("Haz clic y arrastra el logo directamente dentro del área para posicionarlo libremente:")

        if mapa_uv_visual_b64:
            # Creamos una interfaz interactiva HTML con JavaScript para arrastrar el elemento con el mouse
            base_coords = st.session_state.coordenadas_partes[parte_seleccionada]
            b_x = base_coords["base_x"]
            b_y = base_coords["base_y"]
            
            # Calcular posición inicial estimada en el visor web interactivo (mapeado a un cuadro de 400x400 píxeles web)
            web_scale_factor = 400 / 2048
            box_left = (b_x + offset_x - escala_logo // 2) * web_scale_factor
            box_top = (b_y + offset_y - escala_logo // 2) * web_scale_factor
            box_w = escala_logo * web_scale_factor
            
            interactive_uv_html = f"""
            <div id="canvas-container" style="position: relative; width: 400px; height: 400px; margin: 0 auto; border: 2px dashed #4F46E5; border-radius: 8px; overflow: hidden; background: #111;">
                <img src="data:image/png;base64,{mapa_uv_visual_b64}" style="width: 100%; height: 100%; pointer-events: none; user-select: none;" />
                <div id="draggable-logo" style="position: absolute; left: {box_left}px; top: {box_top}px; width: {box_w}px; height: {box_w}px; cursor: grab; border: 2px solid #38BDF8; background: rgba(56, 189, 248, 0.2); display: flex; align-items: center; justify-content: center; border-radius: 4px;">
                    <span style="font-size: 10px; color: white; background: rgba(0,0,0,0.6); padding: 2px 4px; border-radius: 3px; pointer-events: none;">🫱 Arrastrar</span>
                </div>
            </div>
            
            <script>
                const container = document.getElementById('canvas-container');
                const logo = document.getElementById('draggable-logo');
                let isDragging = false;
                let startX, startY;
                
                let currentOffsetX = {offset_x};
                let currentOffsetY = {offset_y};
                const baseX = {b_x};
                const baseY = {b_y};
                const scaleFactor = 2048 / 400; // de pixeles web a pixeles reales 2048x2048

                logo.addEventListener('mousedown', (e) => {{
                    isDragging = true;
                    startX = e.clientX;
                    startY = e.clientY;
                    logo.style.cursor = 'grabbing';
                    e.preventDefault();
                }});

                window.addEventListener('mousemove', (e) => {{
                    if (!isDragging) return;
                    const dx = (e.clientX - startX) * scaleFactor;
                    const dy = (e.clientY - startY) * scaleFactor;
                    
                    startX = e.clientX;
                    startY = e.clientY;
                    
                    currentOffsetX += dx;
                    currentOffsetY += dy;

                    // Actualizar posición visual en tiempo real en el cuadro web
                    const newLeft = ((baseX + currentOffsetX - ({escala_logo}/2)) / 2048) * 400;
                    const newTop = ((baseY + currentOffsetY - ({escala_logo}/2)) / 2048) * 400;
                    
                    logo.style.left = newLeft + 'px';
                    logo.style.top = newTop + 'px';
                }});

                window.addEventListener('mouseup', () => {{
                    if (isDragging) {{
                        isDragging = false;
                        logo.style.cursor = 'grab';
                        
                        // Enviar nuevos valores a Streamlit mediante URL parameters o recarga controlada
                        const url = new URL(window.parent.location.href);
                        url.searchParams.set('ox_{parte_seleccionada}', Math.round(currentOffsetX));
                        url.searchParams.set('oy_{parte_seleccionada}', Math.round(currentOffsetY));
                        window.parent.location.href = url.toString();
                    }}
                }});
            </script>
            """
            components.html(interactive_uv_html, height=430)
            
            # Capturar parámetros de la URL si el usuario arrastró el elemento
            query_params = st.query_params
            param_ox = query_params.get(f"ox_{parte_seleccionada}")
            param_oy = query_params.get(f"oy_{parte_seleccionada}")
            
            if param_ox is not None and param_oy is not None:
                try:
                    new_ox = int(param_ox)
                    new_oy = int(param_oy)
                    if new_ox != st.session_state.coordenadas_partes[parte_seleccionada]["offset_x"] or new_oy != st.session_state.coordenadas_partes[parte_seleccionada]["offset_y"]:
                        st.session_state.coordenadas_partes[parte_seleccionada]["offset_x"] = new_ox
                        st.session_state.coordenadas_partes[parte_seleccionada]["offset_y"] = new_oy
                        st.rerun()
                except Exception:
                    pass
        else:
            st.info("Sube una imagen para habilitar el arrastre interactivo.")

with tab_admin:
    st.header("⚙️ Configuración y Gestión del Sistema")
    st.write("Sube los archivos de guía para cada parte de la prenda:")
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.markdown("**Frente**")
        file_frente = st.file_uploader("Subir Frente", type=["png", "jpg", "jpeg", "svg"], key="map_frente")
        if file_frente:
            st.session_state.mapeo_archivos_bytes["Frente"] = (file_frente.getvalue(), file_frente.name)
            st.success("Sincronizado")
    with col_m2:
        st.markdown("**Espalda**")
        file_espalda = st.file_uploader("Subir Espalda", type=["png", "jpg", "jpeg", "svg"], key="map_espalda")
        if file_espalda:
            st.session_state.mapeo_archivos_bytes["Espalda"] = (file_espalda.getvalue(), file_espalda.name)
            st.success("Sincronizado")
    with col_m3:
        st.markdown("**Mangas**")
        file_mangas = st.file_uploader("Subir Mangas", type=["png", "jpg", "jpeg", "svg"], key="map_mangas")
        if file_mangas:
            st.session_state.mapeo_archivos_bytes["Mangas"] = (file_mangas.getvalue(), file_mangas.name)
            st.success("Sincronizado")
    with col_m4:
        st.markdown("**Cuello**")
        file_cuello = st.file_uploader("Subir Cuello", type=["png", "jpg", "jpeg", "svg"], key="map_cuello")
        if file_cuello:
            st.session_state.mapeo_archivos_bytes["Cuello"] = (file_cuello.getvalue(), file_cuello.name)
            st.success("Sincronizado")

    st.markdown("---")
    st.subheader("📦 Modelos Disponibles en tu Cuenta (Sketchfab)")
    
    token_input = st.text_input("Token de API de Sketchfab", type="password", value=st.session_state.sketchfab_token)
    if st.button("Actualizar Token y Buscar Modelos"):
        st.session_state.sketchfab_token = token_input
        st.cache_data.clear()
        st.rerun()

    if st.session_state.sketchfab_token:
        modelos = obtener_modelos_sketchfab(st.session_state.sketchfab_token)
        if modelos:
            cols = st.columns(3)
            for idx, modelo in enumerate(modelos):
                uid = modelo.get("uid")
                name = modelo.get("name")
                with cols[idx % 3]:
                    st.markdown(f"**{name}**")
                    preview_html = f"""
                    <div style="width: 100%; height: 220px; border-radius: 8px; overflow: hidden; border: 1px solid #ddd;">
                        <iframe title="{name}" width="100%" height="100%" src="https://sketchfab.com/models/{uid}/embed" frameborder="0" allowvr allow="autoplay; fullscreen; xr-spatial-tracking"></iframe>
                    </div>
                    """
                    components.html(preview_html, height=230)
                    is_selected = (st.session_state.modelo_seleccionado_uid == uid)
                    if st.button("Seleccionar Modelo" if not is_selected else "✅ Modelo Activo", key=f"api_model_{uid}"):
                        st.session_state.modelo_seleccionado_uid = uid
                        st.rerun()
        else:
            st.info("No se encontraron modelos públicos directos para este token.")

    st.markdown("---")
    st.subheader("📍 Coordenadas Base del Mapa UV (Respecto a 2048x2048)")
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.markdown("**Frente**")
        st.session_state.coordenadas_partes["Frente"]["base_x"] = st.number_input("Frente X", 0, 2048, st.session_state.coordenadas_partes["Frente"]["base_x"])
        st.session_state.coordenadas_partes["Frente"]["base_y"] = st.number_input("Frente Y", 0, 2048, st.session_state.coordenadas_partes["Frente"]["base_y"])
    with col_b:
        st.markdown("**Espalda**")
        st.session_state.coordenadas_partes["Espalda"]["base_x"] = st.number_input("Espalda X", 0, 2048, st.session_state.coordenadas_partes["Espalda"]["base_x"])
        st.session_state.coordenadas_partes["Espalda"]["base_y"] = st.number_input("Espalda Y", 0, 2048, st.session_state.coordenadas_partes["Espalda"]["base_y"])
    with col_c:
        st.markdown("**Mangas**")
        st.session_state.coordenadas_partes["Mangas"]["base_x"] = st.number_input("Mangas X", 0, 2048, st.session_state.coordenadas_partes["Mangas"]["base_x"])
        st.session_state.coordenadas_partes["Mangas"]["base_y"] = st.number_input("Mangas Y", 0, 2048, st.session_state.coordenadas_partes["Mangas"]["base_y"])
    with col_d:
        st.markdown("**Cuello**")
        st.session_state.coordenadas_partes["Cuello"]["base_x"] = st.number_input("Cuello X", 0, 2048, st.session_state.coordenadas_partes["Cuello"]["base_x"])
        st.session_state.coordenadas_partes["Cuello"]["base_y"] = st.number_input("Cuello Y", 0, 2048, st.session_state.coordenadas_partes["Cuello"]["base_y"])
