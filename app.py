from io import BytesIO
import base64
from PIL import Image
import streamlit as st
import streamlit.components.v1 as components
import requests

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
else:
    partes_necesarias = {
        "Frente": {"base_x": 250, "base_y": 500},
        "Espalda": {"base_x": 750, "base_y": 500},
        "Mangas": {"base_x": 512, "base_y": 800},
        "Cuello": {"base_x": 512, "base_y": 200}
    }
    for p, vals in partes_necesarias.items():
        if p not in st.session_state.coordenadas_partes:
            st.session_state.coordenadas_partes[p] = vals

if "mapeo_archivos" not in st.session_state:
    st.session_state.mapeo_archivos = {
        "Frente": None,
        "Espalda": None,
        "Mangas": None,
        "Cuello": None
    }

if "sketchfab_token" not in st.session_state:
    st.session_state.sketchfab_token = "52e167c5a6024ee8b9b8fb8b9a7a89fc"

if "modelo_seleccionado_uid" not in st.session_state:
    st.session_state.modelo_seleccionado_uid = ""

@st.cache_data(ttl=600)
def obtener_modelos_sketchfab(token):
    """Extrae directamente todos los modelos desde la API oficial de Sketchfab."""
    if not token:
        return []
    
    headers = {"Authorization": f"Token {token}"}
    url = "https://api.sketchfab.com/v3/me/models"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("results", [])
        else:
            return []
    except Exception:
        return []

def generar_textura_3d(imagen_subida_b64, escala=200, offset_x=0, offset_y=0, parte="Frente"):
    try:
        coords_dict = st.session_state.coordenadas_partes
        img_base = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255))
        
        for nombre_parte, coords in coords_dict.items():
            base_x = coords.get("base_x", 512)
            base_y = coords.get("base_y", 512)
            
            if nombre_parte == parte and imagen_subida_b64:
                decoded_elem = base64.b64decode(imagen_subida_b64)
                img_elem = Image.open(BytesIO(decoded_elem)).convert("RGBA")
                img_elem.thumbnail((escala, escala))
                
                ex = (base_x - img_elem.width // 2) + offset_x
                ey = (base_y - img_elem.height // 2) + offset_y
                
                img_base.paste(img_elem, (ex, ey), img_elem)

        buffered = BytesIO()
        img_base.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"Error generando textura: {e}")
        return ""

# --- INTERFAZ PRINCIPAL ---
st.title("Personalizador 3D - Pixel Thread")

tab_cliente, tab_admin = st.tabs(["🎨 Personalizador en Vivo", "⚙️ Panel Admin y API Sketchfab"])

with tab_cliente:
    col_panel, col_visor = st.columns(2, gap="large")

    with col_panel:
        st.header("Panel de Control")
        parte_seleccionada = st.selectbox("Selecciona la parte de la prenda", ["Frente", "Espalda", "Mangas", "Cuello"])
        escala_logo = st.slider("Tamaño del diseño", 50, 500, 200)
        offset_x = st.slider("Mover Horizontal (X)", -300, 300, 0)
        offset_y = st.slider("Mover Vertical (Y)", -300, 300, 0)
        
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
        parte=parte_seleccionada
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
            st.warning("⚠️ Selecciona un modelo desde la pestaña **Panel Admin y API Sketchfab** para visualizarlo.")
        
        st.markdown("---")
        
        if textura_resultado_b64:
            imagen_decodificada = base64.b64decode(textura_resultado_b64)
            st.image(BytesIO(imagen_decodificada), caption="Mapa UV Texturizado en Tiempo Real (1024x1024)", use_container_width=True)
        else:
            st.info("Sube una imagen para ver el mapa UV generado.")

with tab_admin:
    st.header("⚙️ Configuración y Gestión del Sistema")
    
    # --- SECCIÓN DE ARCHIVOS DE MAPEO CON SOPORTE SVG ---
    st.subheader("🗺️ Archivos para el Mapeo de Ubicación (UV Mapping)")
    st.write("Sube aquí los archivos o guías de imagen (PNG, JPG o SVG) correspondientes para configurar las zonas del modelo 3D:")
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        st.markdown("**Frente**")
        file_frente = st.file_uploader("Subir Frente", type=["png", "jpg", "jpeg", "svg"], key="map_frente")
        if file_frente:
            st.session_state.mapeo_archivos["Frente"] = file_frente.name
            st.success("Cargado")
            
    with col_m2:
        st.markdown("**Espalda**")
        file_espalda = st.file_uploader("Subir Espalda", type=["png", "jpg", "jpeg", "svg"], key="map_espalda")
        if file_espalda:
            st.session_state.mapeo_archivos["Espalda"] = file_espalda.name
            st.success("Cargado")
            
    with col_m3:
        st.markdown("**Mangas**")
        file_mangas = st.file_uploader("Subir Mangas", type=["png", "jpg", "jpeg", "svg"], key="map_mangas")
        if file_mangas:
            st.session_state.mapeo_archivos["Mangas"] = file_mangas.name
            st.success("Cargado")
            
    with col_m4:
        st.markdown("**Cuello**")
        file_cuello = st.file_uploader("Subir Cuello", type=["png", "jpg", "jpeg", "svg"], key="map_cuello")
        if file_cuello:
            st.session_state.mapeo_archivos["Cuello"] = file_cuello.name
            st.success("Cargado")

    st.markdown("---")
    st.subheader("⚙️ Extracción de Modelos desde la API de Sketchfab")
    
    token_input = st.text_input("Token de API de Sketchfab", type="password", value=st.session_state.sketchfab_token)
    if st.button("Actualizar Token"):
        st.session_state.sketchfab_token = token_input
        st.cache_data.clear()
        st.success("¡Token actualizado con éxito!")

    st.markdown("---")
    st.subheader("📦 Modelos Disponibles en tu Cuenta")
    
    modelos = obtener_modelos_sketchfab(st.session_state.sketchfab_token)
    
    if modelos:
        st.success(f"¡Se extrajeron {len(modelos)} modelos correctamente desde la API!")
        cols = st.columns(3)
        for idx, modelo in enumerate(modelos):
            uid = modelo.get("uid")
            name = modelo.get("name")
            
            with cols[idx % 3]:
                st.markdown(f"**{name}**")
                preview_html = f"""
                <div style="width: 100%; height: 220px; border-radius: 8px; overflow: hidden; border: 1px solid #ddd; margin-bottom: 10px;">
                    <iframe title="{name}" width="100%" height="100%" src="https://sketchfab.com/models/{uid}/embed" frameborder="0" allowvr allow="autoplay; fullscreen; xr-spatial-tracking"></iframe>
                </div>
                """
                components.html(preview_html, height=230)
                
                is_selected = (st.session_state.modelo_seleccionado_uid == uid)
                if st.button("Seleccionar Modelo" if not is_selected else "✅ Modelo Activo", key=f"api_model_{uid}"):
                    st.session_state.modelo_seleccionado_uid = uid
                    st.rerun()
    else:
        st.error("No se pudieron extraer los modelos. Comprueba que tu token sea válido.")

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
