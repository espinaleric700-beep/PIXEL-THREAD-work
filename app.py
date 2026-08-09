import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Pixel Thread - Estudio de Diseño y Maquetas 3D",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS AVANZADOS (INTERFAZ ESTILO EDITOR PROFESIONAL) ---
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
        padding-left: 1.5rem;
        padding-right: 1.5rem;
        padding-top: 1rem;
    }
    
    /* Contenedores principales */
    .editor-layout {
        display: flex;
        gap: 16px;
        height: 780px;
    }
    
    .stButton>button {
        background-color: #00cec9;
        color: #111;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 8px 16px;
    }
    .stButton>button:hover {
        background-color: #01a3a4;
        color: #fff;
    }

    .dot-red {
        height: 10px;
        width: 10px;
        background-color: #ff4b4b;
        border-radius: 50%;
        display: inline-block;
        margin-left: 6px;
        box-shadow: 0 0 8px #ff4b4b;
        vertical-align: middle;
    }
    .dot-green {
        height: 10px;
        width: 10px;
        background-color: #00ff80;
        border-radius: 50%;
        display: inline-block;
        margin-left: 6px;
        box-shadow: 0 0 8px #00ff80;
        vertical-align: middle;
    }
    .dot-blue {
        height: 10px;
        width: 10px;
        background-color: #00bfff;
        border-radius: 50%;
        display: inline-block;
        margin-left: 6px;
        box-shadow: 0 0 8px #00bfff;
        vertical-align: middle;
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

# --- FUNCIONES AUXILIARES DE GESTIÓN Y PROCESAMIENTO ---
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
    
    if nombre_lower.endswith(('png', 'jpg', 'jpeg')):
        try:
            img = Image.open(BytesIO(b_cont))
            img.thumbnail((700, 700))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=70)
            b_cont = buffered.getvalue()
        except Exception:
            pass
            
    return base64.b64encode(b_cont).decode("utf-8")

def limpiar_lista_archivos(raw_data):
    lista_limpia = []
    if not isinstance(raw_data, list):
        return []
    for item in raw_data:
        if isinstance(item, list):
            lista_limpia.extend(limpiar_lista_archivos(item))
        elif isinstance(item, dict) and "nombre" in item and "data" in item:
            lista_limpia.append({"nombre": item["nombre"], "data": item["data"]})
    return lista_limpia

def render_estado_badge(estado):
    if estado == "Pendiente":
        st.markdown("**Estado:** Pendiente <span class='dot-red'></span>", unsafe_allow_html=True)
    elif estado == "En Proceso":
        st.markdown("**Estado:** En Proceso <span class='dot-green'></span>", unsafe_allow_html=True)
    else:
        st.markdown("**Estado:** Completado <span class='dot-blue'></span>", unsafe_allow_html=True)

# --- GESTIÓN DE ESTADOS Y URL ---
params = st.query_params
if "modo_vista" not in st.session_state: 
    st.session_state.modo_vista = params.get("seccion", "Estudio")
if "user" not in st.session_state: 
    st.session_state.user = params.get("user", "ClienteGeneral")
if "herramienta_activa" not in st.session_state:
    st.session_state.herramienta_activa = "Archivos"

def actualizar_url(vista, user):
    st.session_state.modo_vista = vista
    st.session_state.user = user
    st.query_params.update({"seccion": vista, "user": user})
    st.rerun()

ADMINS_AUTORIZADOS = ["pixel2580", "eric"]

# --- BARRA SUPERIOR DE NAVEGACIÓN Y CONTROL ---
col_top1, col_top2, col_top3, col_top4 = st.columns([1, 4, 3, 2])
with col_top1:
    if st.button("✕ Salir"):
        actualizar_url("Estudio", st.session_state.user)
with col_top2:
    st.markdown("<h4 style='margin: 0; color: #fff;'>Subir y Diseñar</h4>", unsafe_allow_html=True)
with col_top3:
    usuario_actual = st.session_state.user.strip().lower()
    if usuario_actual in [adm.lower() for adm in ADMINS_AUTORIZADOS]:
        if st.button("🛠️ Panel Admin"):
            actualizar_url("Admin" if st.session_state.modo_vista != "Admin" else "Estudio", st.session_state.user)
with col_top4:
    if st.button("Guardar Proyecto", use_container_width=True):
        st.session_state.guardar_trigger = True

st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)

# =========================================================
# 1. VISTA DE ESTUDIO Y DISEÑO INTERactivo
# =========================================================
if st.session_state.modo_vista == "Estudio":

    # Estructura principal en 3 columnas: Barra lateral | Lienzo Central | Panel Derecho 3D/Color
    col_nav, col_sidebar_content, col_canvas, col_right = st.columns([0.6, 1.8, 4.6, 2.2], gap="small")

    # --- 1. BARRA DE HERRAMIENTAS LATERAL IZQUIERDA (Iconos estilo Canva) ---
    with col_nav:
        st.markdown("<div style='background-color: #121212; border-radius: 12px; padding: 10px 4px; height: 740px; display: flex; flex-direction: column; align-items: center; gap: 15px;'>", unsafe_allow_html=True)
        
        if st.button("📁\nArchivos", key="btn_h_archivos", use_container_width=True):
            st.session_state.herramienta_activa = "Archivos"
            st.rerun()
        if st.button("🔲\nElementos", key="btn_h_elementos", use_container_width=True):
            st.session_state.herramienta_activa = "Elementos"
            st.rerun()
        if st.button("T\nTexto", key="btn_h_texto", use_container_width=True):
            st.session_state.herramienta_activa = "Texto"
            st.rerun()
        if st.button("✨\nLogo IA", key="btn_h_ia", use_container_width=True):
            st.session_state.herramienta_activa = "IA"
            st.rerun()
            
        st.markdown("</div>", unsafe_allow_html=True)

    # --- 2. PANEL DE OPCIONES DESPLEGABLE SEGÚN HERRAMIENTA SELECCIONADA ---
    with col_sidebar_content:
        st.markdown("<div style='background-color: #1e1e1e; border: 1px solid #333; border-radius: 12px; padding: 15px; height: 740px; overflow-y: auto;'>", unsafe_allow_html=True)
        
        if st.session_state.herramienta_activa == "Archivos":
            st.markdown("#### Archivos Subidos")
            nombre_proyecto = st.text_input("Nombre del Proyecto", "Proyecto Pixel 3D")
            uploaded_file = st.file_uploader("Subir JPG, PNG, SVG, DST", type=["png", "jpg", "jpeg", "svg", "dst", "pes"])
            
            st.markdown("---")
            if st.button("🚀 Enviar a Producción", use_container_width=True):
                if not nombre_proyecto:
                    st.warning("⚠️ Ingresa un nombre de proyecto.")
                else:
                    try:
                        with st.spinner("Guardando en Firebase..."):
                            lista_archivos = []
                            if uploaded_file:
                                b64_data = procesar_archivo_subido(uploaded_file)
                                lista_archivos.append({"nombre": uploaded_file.name, "data": b64_data})

                            data_pedido = {
                                "id": f"PT-{int(datetime.now().timestamp())}",
                                "cliente": st.session_state.user.strip(),
                                "nombre_proyecto": nombre_proyecto,
                                "producto": "ESTUDIO 3D",
                                "ubicacion": "FRENTE / PERSONALIZADO",
                                "archivos": lista_archivos,
                                "archivos_finales": [],
                                "estado": "Pendiente",
                                "turno": 1,
                                "timestamp": datetime.now()
                            }
                            db.collection("pedidos_bordado").add(data_pedido)
                            recalcular_turnos()
                            st.success("¡Proyecto enviado a Firebase con éxito!")
                    except Exception as e:
                        st.error(f"Error al conectar con Firebase: {e}")

        elif st.session_state.herramienta_activa == "Elementos":
            st.markdown("#### Elementos Gráficos")
            st.info("Selecciona gráficos predeterminados para tu diseño.")
            st.markdown("🐻 Oso Urbano Pixel Thread")
            st.markdown("🧢 Gorra y Estilos")

        elif st.session_state.herramienta_activa == "Texto":
            st.markdown("#### Añadir Texto")
            text_input = st.text_input("Texto Personalizado", "Pixel Thread")
            font_style = st.selectbox("Estilo de fuente", ["Urbano / Bold", "Cursiva", "Clásica"])

        elif st.session_state.herramienta_activa == "IA":
            st.markdown("#### Generador de Logos IA")
            prompt_ia = st.text_area("Describe tu logo ideal:", "Logotipo urbano estilo bordado con oso y letras PT")
            if st.button("Generar Diseño IA", use_container_width=True):
                st.success("¡Generando concepto con IA!")

        st.markdown("</div>", unsafe_allow_html=True)

    # --- 3. LIENZO CENTRAL (Plantilla de Despiece de Camiseta) ---
    with col_canvas:
        st.markdown("<div style='background-color: #242424; border: 1px solid #333; border-radius: 12px; padding: 20px; height: 740px; display: flex; flex-direction: column; align-items: center; justify-content: space-between;'>", unsafe_allow_html=True)
        
        # Despiece central exacto
        st.markdown("<div style='display: flex; gap: 20px; justify-content: center; align-items: center; height: 620px;'>", unsafe_allow_html=True)
        
        # Frente
        st.markdown("""
            <div style='background: #fff; color: #000; border-radius: 10px; padding: 15px; width: 170px; height: 480px; display: flex; flex-direction: column; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.3);'>
                <p style='font-size: 11px; font-weight: bold; margin-bottom: 10px;'>FRENTE</p>
                <div style='border: 2px dashed #00cec9; border-radius: 50%; width: 90px; height: 90px; display: flex; align-items: center; justify-content: center; background: #f9f9f9;'>
                    <span style='font-size: 20px;'>🐻</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Espalda
        st.markdown("""
            <div style='background: #fff; color: #000; border-radius: 10px; padding: 15px; width: 170px; height: 480px; display: flex; flex-direction: column; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.3);'>
                <p style='font-size: 11px; font-weight: bold; margin-bottom: 10px;'>ESPALDA</p>
                <div style='border: 2px dashed #ccc; border-radius: 50%; width: 90px; height: 90px; display: flex; align-items: center; justify-content: center; background: #f9f9f9;'>
                    <span style='font-size: 10px; color: #999;'>Vacío</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Mangas y cuello
        st.markdown("""
            <div style='display: flex; flex-direction: column; gap: 10px; height: 480px; justify-content: center;'>
                <div style='background: #fff; color: #000; border-radius: 10px; padding: 10px; width: 130px; height: 120px; display: flex; flex-direction: column; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.3);'>
                    <p style='font-size: 9px; font-weight: bold;'>CUELLO</p>
                    <div style='border: 1px solid #ccc; width: 80px; height: 30px; background: #f9f9f9;'></div>
                </div>
                <div style='background: #fff; color: #000; border-radius: 10px; padding: 10px; width: 130px; height: 170px; display: flex; flex-direction: column; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.3);'>
                    <p style='font-size: 9px; font-weight: bold;'>MANGA IZQ</p>
                    <div style='border: 1px solid #ccc; width: 80px; height: 70px; background: #f9f9f9;'></div>
                </div>
                <div style='background: #fff; color: #000; border-radius: 10px; padding: 10px; width: 130px; height: 170px; display: flex; flex-direction: column; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.3);'>
                    <p style='font-size: 9px; font-weight: bold;'>MANGA DER</p>
                    <div style='border: 1px solid #ccc; width: 80px; height: 70px; background: #f9f9f9;'></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

        # Barra de herramientas inferior del lienzo (Zoom, Deshacer, etc.)
        b_tool1, b_tool2, b_tool3, b_tool4, b_tool5 = st.columns(5)
        with b_tool1:
            st.markdown("↩️ Deshacer")
        with b_tool2:
            st.markdown("🔍 Zoom 100%")
        with b_tool3:
            st.markdown("👁️ Vista Previa")
        with b_tool4:
            st.markdown("⚡ Sincronizado")
        with b_tool5:
            st.markdown("✨ 50 pts")

        st.markdown("</div>", unsafe_allow_html=True)

    # --- 4. PANEL DERECHO (Visor 3D y Selector de Colores) ---
    with col_right:
        st.markdown("<div style='background-color: #1e1e1e; border: 1px solid #333; border-radius: 12px; padding: 15px; height: 740px; display: flex; flex-direction: column; gap: 15px;'>", unsafe_allow_html=True)
        
        # Visor 3D de la camiseta
        model_viewer_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
            <style>
                body { margin: 0; background-color: #1e1e1e; overflow: hidden; }
                model-viewer {
                    width: 100%;
                    height: 320px;
                    background-color: #141414;
                    border-radius: 10px;
                }
            </style>
        </head>
        <body>
            <model-viewer 
                src="https://modelviewer.dev/shared-assets/models/Astronaut.glb" 
                alt="Maqueta 3D" 
                auto-rotate 
                camera-controls 
                interaction-prompt="none">
            </model-viewer>
        </body>
        </html>
        """
        st.components.v1.html(model_viewer_html, height=330)

        st.markdown("#### Color del Producto")
        
        # Selector de colores en círculos exactos como en la referencia
        col_c1, col_c2, col_c3, col_c4, col_c5, col_c6, col_c7 = st.columns(7)
        with col_c1:
            st.button("➕", key="col_add")
        with col_c2:
            st.button("⚪", key="col_white")
        with col_c3:
            st.button("⚫", key="col_black")
        with col_c4:
            st.button("🔘", key="col_gray")
        with col_c5:
            st.button("🔴", key="col_red")
        with col_c6:
            st.button("🟣", key="col_purple")
        with col_c7:
            st.button("🩷", key="col_pink")

        st.markdown("---")
        st.markdown("#### Mis Pedidos Guardados")
        try:
            todos = list(db.collection("pedidos_bordado").order_by("timestamp").stream())
            mis_pedidos = [p.to_dict() for p in todos if p.to_dict().get("cliente", "").strip().lower() == st.session_state.user.strip().lower()]
            if mis_pedidos:
                for p in mis_pedidos[-2:]:
                    st.caption(f"🧵 {p.get('nombre_proyecto')} | Turno: #{p.get('turno')}")
                    render_estado_badge(p.get('estado', 'Pendiente'))
            else:
                st.info("Sin pedidos guardados.")
        except Exception:
            st.caption("Cargando base de datos...")

        st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# 2. PANEL DE ADMINISTRADOR
# =========================================================
else:
    st.subheader("🛠️ Panel de Administración General (Firebase)")

    try:
        tab_admin_pend, tab_admin_comp = st.tabs(["⏳ Pedidos Pendientes y En Proceso", "✅ Completados / Entregados"])

        recalcular_turnos()
        docs = list(db.collection("pedidos_bordado").order_by("timestamp").stream())

        with tab_admin_pend:
            pedidos_activos = [(doc.id, doc.to_dict()) for doc in docs if doc.to_dict().get('estado') != "Completado"]

            if pedidos_activos:
                cols = st.columns(4)
                for i, (doc_id, p) in enumerate(pedidos_activos):
                    with cols[i % 4]:
                        with st.container(border=True):
                            turno_val = p.get('turno', 'N/A')
                            st.markdown(f"**🔢 Turno:** `#{turno_val}`")
                            st.markdown(f"**👤 Cliente:** `{p.get('cliente')}`")
                            st.markdown(f"**🧵 Proyecto:** `{p.get('nombre_proyecto', 'N/A')}`")
                            
                            estado_actual = p.get('estado', 'Pendiente')
                            render_estado_badge(estado_actual)
                            
                            if estado_actual == "Pendiente":
                                if st.button("🔄 Pasar a En Proceso", key=f"btn_proceso_{doc_id}", use_container_width=True):
                                    db.collection("pedidos_bordado").document(doc_id).update({"estado": "En Proceso"})
                                    recalcular_turnos()
                                    st.rerun()
                            else:
                                if st.button("🔄 Regresar a Pendiente", key=f"btn_pendiente_{doc_id}", use_container_width=True):
                                    db.collection("pedidos_bordado").document(doc_id).update({"estado": "Pendiente"})
                                    recalcular_turnos()
                                    st.rerun()

                            with st.expander("📤 Subir Archivo Entregable"):
                                archivos_entregables = st.file_uploader(
                                    "Archivos finales:", 
                                    type=["dst", "emb", "pes", "png", "jpg", "pdf"],
                                    accept_multiple_files=True, 
                                    key=f"up_admin_{doc_id}"
                                )
                                if st.button("🚀 SUBIR Y COMPLETAR", key=f"btn_comp_{doc_id}", use_container_width=True):
                                    if archivos_entregables:
                                        try:
                                            lista_finales = []
                                            for af in archivos_entregables:
                                                b64_fin = procesar_archivo_subido(af)
                                                lista_finales.append({"nombre": af.name, "data": b64_fin})
                                                
                                            db.collection("pedidos_bordado").document(doc_id).update({
                                                "archivos_finales": lista_finales,
                                                "estado": "Completado",
                                                "turno": "N/A"
                                            })
                                            recalcular_turnos()
                                            st.success("¡Pedido completado!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error: {e}")
                                    else:
                                        st.warning("Adjunta archivos.")

                            if st.button("🗑️ Eliminar Pedido", key=f"mob_del_{doc_id}", use_container_width=True):
                                db.collection("pedidos_bordado").document(doc_id).delete()
                                recalcular_turnos()
                                st.rerun()
            else:
                st.info("🎉 No hay pedidos pendientes.")

        with tab_admin_comp:
            pedidos_completados_admin = [(doc.id, doc.to_dict()) for doc in docs if doc.to_dict().get('estado') == "Completado"]
            if pedidos_completados_admin:
                for doc_id, p in pedidos_completados_admin:
                    with st.container(border=True):
                        st.markdown(f"**👤 {p.get('cliente')}** - **🧵 {p.get('nombre_proyecto')}**")
                        render_estado_badge("Completado")
                        if st.button("🔄 Marcar como Pendiente", key=f"reg_{doc_id}"):
                            db.collection("pedidos_bordado").document(doc_id).update({"estado": "Pendiente"})
                            recalcular_turnos()
                            st.rerun()
            else:
                st.info("No hay pedidos completados.")

    except Exception as e:
        st.error(f"Error en el panel admin: {e}")
