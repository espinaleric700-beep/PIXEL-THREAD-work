from io import BytesIO
import base64
from PIL import Image
import streamlit as st
import streamlit.components.v1 as components

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Pixel Thread - Personalizador 3D", layout="wide")

# --- GESTIÓN DE ESTADO (SESSION STATE) PARA CONFIGURACIÓN DINÁMICA ---
if "coordenadas_partes" not in st.session_state:
    st.session_state.coordenadas_partes = {
        "Frente": {"base_x": 250, "base_y": 500},
        "Espalda": {"base_x": 750, "base_y": 500},
        "Mangas": {"base_x": 512, "base_y": 800}
    }

if "sketchfab_url" not in st.session_state:
    st.session_state.sketchfab_url = ""

def generar_textura_3d(imagen_subida_b64, escala=200, offset_x=0, offset_y=0, parte="Frente"):
    try:
        coords_dict = st.session_state.coordenadas_partes
        
        # Lienzo base limpio de 1024x1024 con fondo blanco
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

tab_cliente, tab_admin = st.tabs(["🎨 Personalizador en Vivo", "⚙️ Panel Admin de Coordenadas"])

with tab_cliente:
    col_panel, col_visor = st.columns(2, gap="large")

    with col_panel:
        st.header("Panel de Control")
        parte_seleccionada = st.selectbox("Selecciona la parte de la prenda", ["Frente", "Espalda", "Mangas"])
        escala_logo = st.slider("Tamaño del diseño", 50, 500, 200)
        offset_x = st.slider("Mover Horizontal (X)", -300, 300, 0)
        offset_y = st.slider("Mover Vertical (Y)", -300, 300, 0)
        
        archivo_subido = st.file_uploader(f"Sube el diseño para: {parte_seleccionada}", type=["png", "jpg", "jpeg", "svg"])

    # Procesar imagen cargada
    imagen_b64 = ""
    if archivo_subido is not None:
        bytes_imagen = archivo_subido.read()
        imagen_b64 = base64.b64encode(bytes_imagen).decode("utf-8")

    # Generar textura
    textura_resultado_b64 = generar_textura_3d(
        imagen_subida_b64=imagen_b64, 
        escala=escala_logo, 
        offset_x=offset_x, 
        offset_y=offset_y, 
        parte=parte_seleccionada
    )

    with col_visor:
        st.header("Visor 3D en Tiempo Real")
        
        # Visor de Sketchfab seguro (Si no hay enlace válido, muestra una guía clara en vez de Error 404)
        if st.session_state.sketchfab_url:
            sketchfab_html = f"""
            <div style="width: 100%; height: 350px; border-radius: 10px; overflow: hidden; border: 1px solid #ccc;">
                <iframe title="Modelo 3D Prenda" width="100%" height="100%" src="{st.session_state.sketchfab_url}" frameborder="0" allowvr allow="autoplay; fullscreen; xr-spatial-tracking"></iframe>
            </div>
            """
            components.html(sketchfab_html, height=360)
        else:
            st.warning("⚠️ No has configurado el enlace de Sketchfab. Ve a la pestaña **Panel Admin** para ingresarlo.")
        
        st.markdown("---")
        
        # Vista previa del mapa UV unificado generado
        if textura_resultado_b64:
            imagen_decodificada = base64.b64decode(textura_resultado_b64)
            st.image(BytesIO(imagen_decodificada), caption="Mapa UV Texturizado en Tiempo Real (1024x1024)", use_container_width=True)
        else:
            st.info("Sube una imagen para ver el mapa UV generado.")

with tab_admin:
    st.header("⚙️ Panel de Administración y Configuración")
    st.write("Modifica las posiciones base de las partes de la prenda en el mapa UV y conecta tu modelo 3D.")
    
    st.subheader("🔗 Configuración del Modelo 3D (Sketchfab)")
    url_input = st.text_input("Enlace Embed de Sketchfab (ej. https://sketchfab.com/models/.../embed)", value=st.session_state.sketchfab_url)
    if st.button("Guardar Enlace 3D"):
        st.session_state.sketchfab_url = url_input
        st.success("¡Enlace de Sketchfab actualizado correctamente!")

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
        
    if st.button("Actualizar Coordenadas UV"):
        st.success("¡Coordenadas guardadas e integradas con éxito en el personalizador!")
