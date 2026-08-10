from io import BytesIO
import base64
from PIL import Image
import streamlit as st
import streamlit.components.v1 as components

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Pixel Thread - Personalizador 3D", layout="wide")

# --- SIMULACIÓN DE BASE DE DATOS / CONFIGURACIÓN ---
def obtener_configuracion_activa():
    return {
        "coordenadas_partes": {
            "Frente": {"base_x": 250, "base_y": 500},
            "Espalda": {"base_x": 750, "base_y": 500},
            "Mangas": {"base_x": 512, "base_y": 800}
        },
        "patrones_svg": {
            "Frente": "",
            "Espalda": "",
            "Mangas": ""
        }
    }

def generar_textura_3d(imagen_subida_b64, escala=200, offset_x=0, offset_y=0, parte="Frente"):
    try:
        config = obtener_configuracion_activa() or {}
        coords_dict = config.get("coordenadas_partes", {})
        patrones_svgs = config.get("patrones_svg", {})
        
        # Lienzo base limpio de 1024x1024 con fondo blanco
        img_base = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255))
        
        for nombre_parte, coords in coords_dict.items():
            base_x = coords.get("base_x", 512)
            base_y = coords.get("base_y", 512)
            
            patron_parte = patrones_svgs.get(nombre_parte)
            if patron_parte:
                try:
                    img_patron = Image.open(BytesIO(base64.b64decode(patron_parte))).convert("RGBA")
                    img_base.paste(img_patron, (base_x - img_patron.width // 2, base_y - img_patron.height // 2), img_patron)
                except Exception:
                    pass
            
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

# Pestañas principales para separar la vista de Cliente y el Panel Admin
tab_cliente, tab_admin = st.tabs(["🎨 Personalizador en Vivo", "⚙️ Panel Admin"])

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
        
        # 1. Visor 3D de Sketchfab (Reemplaza 'TU_ID_DE_SKETCHFAB' por el código de tu modelo)
        sketchfab_html = """
        <div style="width: 100%; height: 350px; border-radius: 10px; overflow: hidden; border: 1px solid #ccc;">
            <iframe title="Modelo 3D Prenda" width="100%" height="100%" src="https://sketchfab.com/models/TU_ID_DE_SKETCHFAB/embed" frameborder="0" allowvr allow="autoplay; fullscreen; xr-spatial-tracking"></iframe>
        </div>
        """
        components.html(sketchfab_html, height=360)
        
        st.markdown("---")
        
        # 2. Vista previa del mapa UV unificado generado
        if textura_resultado_b64:
            imagen_decodificada = base64.b64decode(textura_resultado_b64)
            st.image(BytesIO(imagen_decodificada), caption="Mapa UV Texturizado (1024x1024)", use_container_width=True)
        else:
            st.info("Sube una imagen para ver el mapa UV generado.")

with tab_admin:
    st.header("Panel de Administración y Configuración UV")
    st.write("Aquí puedes administrar los parámetros internos del sistema de mapeo 3D para Pixel Thread.")
    
    config_actual = obtener_configuracion_activa()
    st.json(config_actual)
    
    st.success("El panel admin está activo. Puedes configurar aquí la persistencia de coordenadas o base de datos de moldes.")
