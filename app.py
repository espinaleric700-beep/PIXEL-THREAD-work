from io import BytesIO
import base64
from PIL import Image
import streamlit as st

# --- SIMULACIÓN DE BASE DE DATOS / CONFIGURACIÓN ---
def obtener_configuracion_activa():
    """
    Retorna la configuración activa con las coordenadas UV y patrones base de cada sección.
    Ajusta estos valores de base_x y base_y según la posición exacta que viste en tu mapa UV de Illustrator/Blender.
    """
    return {
        "coordenadas_partes": {
            "Frente": {"base_x": 250, "base_y": 500},
            "Espalda": {"base_x": 750, "base_y": 500},
            "Mangas": {"base_x": 512, "base_y": 800}
        },
        "patrones_svg": {
            # Aquí puedes guardar opcionalmente tus patrones en base64 si los manejas por código
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
        
        # 1. Creamos el lienzo base limpio de 1024x1024 con fondo blanco
        img_base = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255))
        
        # 2. Iteramos de forma independiente por cada parte (Frente, Espalda, Mangas, etc.)
        for nombre_parte, coords in coords_dict.items():
            base_x = coords.get("base_x", 512)
            base_y = coords.get("base_y", 512)
            
            # Dibujamos la plantilla base o guía correspondiente a esta sección si existe
            patron_parte = patrones_svgs.get(nombre_parte)
            if patron_parte:
                try:
                    img_patron = Image.open(BytesIO(base64.b64decode(patron_parte))).convert("RGBA")
                    img_base.paste(img_patron, (base_x - img_patron.width // 2, base_y - img_patron.height // 2), img_patron)
                except Exception:
                    pass
            
            # Si el usuario está editando activamente esta sección y subió un diseño/logotipo
            if nombre_parte == parte and imagen_subida_b64:
                decoded_elem = base64.b64decode(imagen_subida_b64)
                img_elem = Image.open(BytesIO(decoded_elem)).convert("RGBA")
                img_elem.thumbnail((escala, escala))
                
                # Posicionamos el diseño del usuario respetando su coordenada base + los offsets de ajuste
                ex = (base_x - img_elem.width // 2) + offset_x
                ey = (base_y - img_elem.height // 2) + offset_y
                
                img_base.paste(img_elem, (ex, ey), img_elem)

        # 3. Exportamos el resultado final unificado para el visor 3D
        buffered = BytesIO()
        img_base.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"Error generando textura: {e}")
        return ""

# --- INTERFAZ DE STREAMLIT ---
st.title("Personalizador 3D - Pixel Thread")
st.sidebar.header("Panel de Control")

# Selección de la parte a editar
parte_seleccionada = st.sidebar.selectbox("Selecciona la parte de la prenda", ["Frente", "Espalda", "Mangas"])

# Controles de escala y posición
escala_logo = st.sidebar.slider("Tamaño del diseño", 50, 500, 200)
offset_x = st.sidebar.slider("Mover Horizontal (X)", -300, 300, 0)
offset_y = st.sidebar.slider("Mover Vertical (Y)", -300, 300, 0)

# Subida de archivo de imagen
archivo_subido = st.sidebar.file_uploader(f"Sube el diseño para: {parte_seleccionada}", type=["png", "jpg", "jpeg", "svg"])

imagen_b64 = ""
if archivo_subido is not None:
    bytes_imagen = archivo_subido.read()
    imagen_b64 = base64.b64encode(bytes_imagen).decode("utf-8")

# Generar textura combinada
textura_resultado_b64 = generar_textura_3d(
    imagen_subida_b64=imagen_b64, 
    escala=escala_logo, 
    offset_x=offset_x, 
    offset_y=offset_y, 
    parte=parte_seleccionada
)

if textura_resultado_b64:
    st.subheader("Vista previa del mapa UV unificado (1024x1024)")
    # Mostrar la imagen resultante en pantalla
    imagen_decodificada = base64.b64decode(textura_resultado_b64)
    st.image(BytesIO(imagen_decodificada), caption="Textura aplicada correctamente sin solapamiento", use_column_width=True)
else:
    st.warning("Sube una imagen para comenzar a generar la textura.")
