from datetime import datetime
import base64
from io import BytesIO
from PIL import Image, ImageOps
from PIL import Image
import requests

# --- CONFIGURACIÓN DE PÁGINA ---
@@ -116,13 +116,13 @@ def procesar_archivo_subido(arch):
return base64.b64encode(b_cont).decode("utf-8"), "raster"

def generar_textura_3d_frente(pieza_frente):
    """Combina el fondo de la pieza del frente y sus elementos superpuestos en una sola imagen para el modelo 3D"""
    """Combina el fondo del frente y los elementos posicionados para aplicarlos al modelo 3D"""
try:
base_b64 = pieza_frente.get("b64", "")
base_tipo = pieza_frente.get("tipo", "raster")
elementos = pieza_frente.get("elementos", [])

        # Crear una imagen base en blanco o con la textura base de 1024x1024
        # Lienzo base de la textura frontal (1024x1024)
img_base = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255))

if base_b64 and base_tipo != "svg":
@@ -134,7 +134,7 @@ def generar_textura_3d_frente(pieza_frente):
except Exception:
pass

        # Superponer cada elemento colocado en el frente
        # Superponer los elementos en las coordenadas relativas guardadas
for elem in elementos:
e_b64 = elem.get("b64", "")
e_tipo = elem.get("tipo", "raster")
@@ -143,12 +143,11 @@ def generar_textura_3d_frente(pieza_frente):
decoded_elem = base64.b64decode(e_b64)
img_elem = Image.open(BytesIO(decoded_elem)).convert("RGBA")

                    # Calcular tamaño y posición aproximada en base al porcentaje guardado
w_pct = elem.get("ancho", 80)
h_pct = elem.get("alto", 80)
                    ew = int((w_pct / 100.0) * 400)
                    eh = int((h_pct / 100.0) * 400)
                    img_elem = img_elem.resize((max(20, ew), max(20, eh)))
                    ew = int((w_pct / 100.0) * 500)
                    eh = int((h_pct / 100.0) * 500)
                    img_elem = img_elem.resize((max(30, ew), max(30, eh)))

x_pct = elem.get("x", 50)
y_pct = elem.get("y", 50)
@@ -609,7 +608,7 @@ def render_capas_pieza(p_dict, p_nombre_pieza):
with st.container(border=True):
sketchfab_uid = config_actual.get("sketchfab_uid", "")

            # Generar la textura combinada del frente
            # Generar textura optimizada del frente
textura_frente_b64 = generar_textura_3d_frente(p_frente)

if sketchfab_uid:
@@ -626,7 +625,7 @@ def render_capas_pieza(p_dict, p_nombre_pieza):
               """
st.components.v1.html(iframe_html, height=170)
else:
                # Script con soporte de Blob URL para texturas dinámicas en model-viewer
                # Script de model-viewer optimizado para inyectar la textura del frente en tiempo real
model_html = f"""
               <!DOCTYPE html>
               <html>
@@ -662,10 +661,10 @@ def render_capas_pieza(p_dict, p_nombre_pieza):
                               if (material) {{
                                   const texture = await viewer.createTexture(blobUrl);
                                   material.pbrMetallicRoughness.baseColorTexture.setTexture(texture);
                                    console.log("Textura aplicada correctamente al modelo 3D");
                                    console.log("Textura del frente aplicada al modelo 3D con éxito.");
                               }}
                           }} catch (e) {{
                                console.error("Error al aplicar la textura dinámica:", e);
                                console.error("Error al actualizar textura 3D:", e);
                           }}
                       }}
