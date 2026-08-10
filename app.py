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
        "Mangas": {"base_x": 512, "base_y": 800}
    }

# Token de Sketchfab configurado por defecto
if "sketchfab_token" not in st.session_state:
    st.session_state.sketchfab_token = "52e167c5a6024ee8b9b8fb8b9a7a89fc"

if "modelo_seleccionado_uid" not in st.session_state:
    st.session_state.modelo_seleccionado_uid = ""

def obtener_modelos_sketchfab(token):
    """Consulta la API de Sketchfab para obtener los modelos del usuario."""
    if not token:
        return []
    
    headers = {"Authorization": f"Token {token}"}
    url = "https://api.sketchfab.com/v3/me/models"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get("results", [])
        else:
            st.error(f"Error al conectar con Sketchfab (Código {response.status_code}): Verifica tu token.")
            return []
    except Exception as e:
        st.error(f"Excepción en la conexión con la API: {e}")
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
        parte_seleccionada = st.selectbox("Selecciona la parte de la prenda", ["Frente", "Espalda", "Mangas"])
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
            st.warning("⚠️ No hay ningún modelo seleccionado. Ve a la pestaña **Panel Admin** para elegir uno de tus modelos sincronizados.")
        
        st.markdown("---")
        
        if textura_resultado_b64:
            imagen_decodificada = base64.b64decode(textura_resultado_b64)
            st.image(BytesIO(imagen_decodificada), caption="Mapa UV Texturizado en Tiempo Real (1024x1024)", use_container_width=True)
        else:
            st.info("Sube una imagen para ver el mapa UV generado.")

with tab_admin:
    st.header("⚙️ Conexión con la API de Sketchfab")
    st.write("Tu token de API está configurado. Aquí puedes ver y seleccionar los modelos de tu cuenta.")
    
    token_input = st.text_input("Token de API de Sketchfab", type="password", value=st.session_state.sketchfab_token)
    if st.button("Actualizar Token"):
        st.session_state.sketchfab_token = token_input
        st.success("¡Token actualizado con éxito!")

    if st.session_state.sketchfab_token:
        st.markdown("---")
        st.subheader("📦 Selecciona tu Modelo 3D")
        
        modelos = obtener_modelos_sketchfab(st.session_state.sketchfab_token)
        
        if modelos:
            cols = st.columns(3)
            for idx, modelo in enumerate(modelos):
                uid = modelo.get("uid")
                name = modelo.get("name")
                thumbnails = modelo.get("thumbnails", {}).get("images", [])
                thumb_url = thumbnails[0]["url"] if thumbnails else ""
                
                with cols[idx % 3]:
                    if thumb_url:
                        st.image(thumb_url, caption=name, use_container_width=True)
                    else:
                        st.write(f"**{name}**")
                        
                    is_selected = (st.session_state.modelo_seleccionado_uid == uid)
                    if st.button("Seleccionar Modelo" if not is_selected else "✅ Seleccionado", key=f"btn_{uid}"):
                        st.session_state.modelo_seleccionado_uid = uid
                        st.rerun()
        else:
            st.info("No se encontraron modelos en tu cuenta de Sketchfab o el token requiere permisos adicionales.")

    st.markdown("---")
    st.subheader("📍 Coordenadas Base del Mapa UV (1024x1024)")
    
    col_a, col_b, col_c = st.columns(3)
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
