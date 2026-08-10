from io import BytesIO
import base64
from PIL import Image, ImageOps
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
        "Frente": {"base_x": 250, "base_y": 500},
        "Espalda": {"base_x": 750, "base_y": 500},
        "Mangas": {"base_x": 512, "base_y": 800},
        "Cuello": {"base_x": 512, "base_y": 200}
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

def abrir_imagen_guia(file_bytes, filename):
    if not file_bytes:
        return Image.new("RGBA", (1024, 1024), (255, 255, 255, 0))
    try:
        if filename and filename.lower().endswith(".svg"):
            if SVG_SUPPORT:
                png_bytes = cairosvg.svg2png(bytestring=file_bytes, output_width=1024, output_height=1024)
                return Image.open(BytesIO(png_bytes)).convert("RGBA")
            else:
                return Image.new("RGBA", (1024, 1024), (255, 255, 255, 0))
        else:
            img = Image.open(BytesIO(file_bytes)).convert("RGBA")
            return ImageOps.contain(img, (1024, 1024), Image.Resampling.LANCZOS)
    except Exception:
        return Image.new("RGBA", (1024, 1024), (255, 255, 255, 0))

def generar_textura_3d(imagen_subida_b64, escala=200, offset_x=0, offset_y=0, parte_activa="Frente"):
    try:
        coords_dict = st.session_state.coordenadas_partes
        
        # 1. Cargar o crear el lienzo base con fondo transparente
        datos_guia = st.session_state.mapeo_archivos_bytes.get(parte_activa)
        if datos_guia:
            file_bytes, filename = datos_guia
            img_base = abrir_imagen_guia(file_bytes, filename)
        else:
            img_base = Image.new("RGBA", (1024, 1024), (255, 255, 255, 0))

        # 2. Procesar el diseño subido (logo)
        if imagen_subida_b64:
            decoded_elem = base64.b64decode(imagen_subida_b64)
            img_elem = Image.open(BytesIO(decoded_elem)).convert("RGBA")
            
            # CORRECCIÓN CRÍTICA: Asegurar que el logo se escale correctamente antes del centrado
            # Usamos ImageOps.contain para preservar la relación de aspecto y el tamaño máximo
            img_elem = ImageOps.contain(img_elem, (escala, escala), Image.Resampling.LANCZOS)
            
            # 3. Obtener coordenadas base y aplicar offsets
            coords = coords_dict.get(parte_activa, {"base_x": 512, "base_y": 512})
            base_x = coords.get("base_x", 512)
            base_y = coords.get("base_y", 512)
            
            # 4. Calcular la posición final centrada y con offset
            pos_x = (base_x - img_elem.width // 2) + offset_x
            pos_y = (base_y - img_elem.height // 2) + offset_y
            
            # 5. Pegar el logo sobre la guía base usando el canal alfa para transparencia
            img_base.alpha_composite(img_elem, (pos_x, pos_y))

        buffered = BytesIO()
        img_base.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"Error generando textura: {e}")
        return ""

# --- INTERFAZ PRINCIPAL ---
st.title("Personalizador 3D - Pixel Thread")

tab_cliente, tab_admin = st.tabs(["🎨 Personalizador en Vivo", "⚙️ Panel Admin y Configuración UV"])

with tab_cliente:
    col_panel, col_visor = st.columns(2, gap="large")

    with col_panel:
        st.header("Panel de Control")
        parte_seleccionada = st.selectbox("Selecciona la parte de la prenda", ["Frente", "Espalda", "Mangas", "Cuello"])
        escala_logo = st.slider("Tamaño del diseño", 50, 800, 200) # Rango aumentado para mayor flexibilidad
        offset_x = st.slider("Mover Horizontal (X)", -500, 500, 0)
        offset_y = st.slider("Mover Vertical (Y)", -500, 500, 0)
        
        archivo_subido = st.file_uploader(f"Sube el diseño para: {parte_seleccionada}", type=["png", "jpg", "jpeg", "svg"])

    imagen_b64 = ""
    if archivo_subido is not None:
        bytes_imagen = archivo_subido.read()
        imagen_b64 = base64.b64encode(bytes_imagen).decode("utf-8")

    textura_resultado_b64 = generar_textura_3d(
        imagen_subida_b64=imagen_b64, 
        escala=escala_logo, 
        offset_x=offset_x, 
        offset_y=offset_y, 
        parte_activa=parte_seleccionada
    )

    with col_visor:
        st.header("Visor 3D en Tiempo Real")
        
        if st.session_state.modelo_seleccionado_uid:
            sketchfab_html = f"""
            <div style="width: 100%; height: 350px; border-radius: 10px; overflow: hidden; border: 1px solid #ccc;">
                <iframe title="Modelo 3D Sketchfab" width="100%" height="100%" src="https://sketchfab.com/models/{st.session_state.modelo_seleccionado_uid}/embed" frameborder="0" allowvr allow="autoplay; fullscreen; xr-spatial-tracking"></iframe>
            </div>
            """
            components.html(sketchfab_html, height=360)
        else:
            st.warning("⚠️ Selecciona un modelo desde la pestaña **Panel Admin y Configuración UV** para visualizarlo.")
        
        st.markdown("---")
        
        if textura_resultado_b64:
            imagen_decodificada = base64.b64decode(textura_resultado_b64)
            st.image(BytesIO(imagen_decodificada), caption=f"Mapa UV Sincronizado ({parte_seleccionada}) - 1024x1024", use_container_width=True)
        else:
            st.info("Sube una imagen para ver el mapa UV generado.")

with tab_admin:
    st.header("⚙️ Configuración y Gestión del Sistema")
    st.write("Sube los archivos de guía (PNG, JPG o SVG). Estos se sincronizarán con las coordenadas del visor:")
    
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
    st.subheader("📍 Coordenadas Base del Mapa UV (1024x1024)")
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.markdown("**Frente**")
        st.session_state.coordenadas_partes["Frente"]["base_x"] = st.number_input("Frente X", 0, 1024, st.session_state.coordenadas_partes["Frente"]["base_x"])
        st.session_state.coordenadas_partes["Frente"]["base_y"] = st.number_input("Frente Y", 0, 1024, st.session_state.coordenadas_partes["Frente"]["base_y"])
    with col_b:
        st.markdown("**Espalda**")
        st.session_state.coordenadas_partes["Espalda"]["base_x"] = st.number_input("Espalda X", 0, 1024, st.session_state.coordenadas_partes["Espalda"]["base_x"])
        st.session_state.coordenadas_partes["Espalda"]["base_y"] = st.number_input("Espalda Y", 0, 1024, st.session_state.coordenadas_partes["Espalda"]["base_y"])
    with col_c:
        st.markdown("**Mangas**")
        st.session_state.coordenadas_partes["Mangas"]["base_x"] = st.number_input("Mangas X", 0, 1024, st.session_state.coordenadas_partes["Mangas"]["base_x"])
        st.session_state.coordenadas_partes["Mangas"]["base_y"] = st.number_input("Mangas Y", 0, 1024, st.session_state.coordenadas_partes["Mangas"]["base_y"])
    with col_d:
        st.markdown("**Cuello**")
        st.session_state.coordenadas_partes["Cuello"]["base_x"] = st.number_input("Cuello X", 0, 1024, st.session_state.coordenadas_partes["Cuello"]["base_x"])
        st.session_state.coordenadas_partes["Cuello"]["base_y"] = st.number_input("Cuello Y", 0, 1024, st.session_state.coordenadas_partes["Cuello"]["base_y"])
