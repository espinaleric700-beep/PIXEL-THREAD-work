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

# --- ESTILOS CSS AVANZADOS (INTERFAZ OSCURA & ESTUDIO) ---
st.markdown("""
    <style>
    .stApp {
        background-color: #1e1e1e;
        color: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .block-container {
        max-width: 100% !important;
        padding-left: 2rem;
        padding-right: 2rem;
        padding-top: 1.5rem;
    }
    
    .panel-box {
        background-color: #262626;
        border: 1px solid #3b3b3b;
        border-radius: 12px;
        padding: 16px;
        height: 720px;
        overflow-y: auto;
    }
    
    .canvas-box {
        background-color: #191919;
        border: 1px solid #3b3b3b;
        border-radius: 12px;
        padding: 24px;
        height: 720px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
    }
    
    .preview-box {
        background-color: #262626;
        border: 1px solid #3b3b3b;
        border-radius: 12px;
        padding: 16px;
        height: 720px;
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

def actualizar_url(vista, user):
    st.session_state.modo_vista = vista
    st.session_state.user = user
    st.query_params.update({"seccion": vista, "user": user})
    st.rerun()

ADMINS_AUTORIZADOS = ["pixel2580", "eric"]

# --- BARRA SUPERIOR DE NAVEGACIÓN Y CONTROL ---
col_top1, col_top2, col_top3 = st.columns([2, 6, 2])
with col_top1:
    if st.button("✕ Estudio 3D"):
        actualizar_url("Estudio", st.session_state.user)
with col_top2:
    st.markdown("<h3 style='text-align: center; margin: 0; color: #fff;'>Pixel Thread Studio 3D</h3>", unsafe_allow_html=True)
with col_top3:
    with st.popover("⚙️ Menú General"):
        st.markdown("### Navegación")
        if st.button("🎨 Estudio / Pedidos", use_container_width=True): 
            actualizar_url("Estudio", st.session_state.user)
        if st.button("🛠️ Panel Admin", use_container_width=True): 
            usuario_actual = st.session_state.user.strip().lower()
            if usuario_actual in [adm.lower() for adm in ADMINS_AUTORIZADOS]:
                actualizar_url("Admin", st.session_state.user)
            else:
                st.error("❌ Sin permisos de Administrador.")

st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

# =========================================================
# 1. VISTA DE ESTUDIO Y GESTIÓN DE PEDIDOS CON FIREBASE
# =========================================================
if st.session_state.modo_vista == "Estudio":
    
    # Selector de usuario rápido en la parte superior para vincular pedidos
    with st.expander("👤 Identificación de Usuario / Cliente"):
        user_input = st.text_input("Ingresa tu Nombre o ID de Usuario:", value=st.session_state.user)
        if user_input != st.session_state.user:
            actualizar_url("Estudio", user_input)

    # 1. TRES COLUMNAS PRINCIPALES (Diseño original optimizado con Firebase)
    col_left, col_center, col_right = st.columns([1.2, 2.2, 1.4], gap="medium")

    # --- PANEL IZQUIERDO: Biblioteca de Archivos, IA y Enviar a Firebase ---
    with col_left:
        st.markdown('<div class="panel-box">', unsafe_allow_html=True)
        st.markdown("#### 📁 Archivos y Base de Datos")
        
        nombre_proyecto = st.text_input("Nombre del Proyecto", "Proyecto Pixel 3D")
        uploaded_file = st.file_uploader("Subir JPG, PNG, SVG, DST", type=["png", "jpg", "jpeg", "svg", "dst", "pes"])
        
        st.markdown("---")
        st.markdown("**Herramientas de Texto y IA:**")
        text_input = st.text_input("Añadir Texto al Diseño", "Pixel Thread")
        font_style = st.selectbox("Estilo de fuente", ["Urbano / Bold", "Cursiva", "Clásica"])
        
        if st.button("Generar con IA (Logo)", use_container_width=True):
            st.info("Generador IA activado para estilos de bordado urbano.")
            
        st.markdown("---")
        
        # Botón de guardado oficial conectado a Firebase
        if st.button("🚀 Enviar Pedido a Producción", use_container_width=True):
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
                            "estilo": font_style,
                            "archivos": lista_archivos,
                            "archivos_finales": [],
                            "comentarios": f"Texto asociado: {text_input}",
                            "estado": "Pendiente",
                            "turno": 1,
                            "timestamp": datetime.now()
                        }
                        db.collection("pedidos_bordado").add(data_pedido)
                        recalcular_turnos()
                        st.success("¡Proyecto enviado y guardado en Firebase con éxito!")
                except Exception as e:
                    st.error(f"Error al conectar con Firebase: {e}")
            
        st.markdown('</div>', unsafe_allow_html=True)

    # --- PANEL CENTRAL: Lienzo de Patrones ---
    with col_center:
        st.markdown('<div class="canvas-box">', unsafe_allow_html=True)
        st.markdown("<h4 style='color: #ccc; margin-bottom: 10px;'>Plantilla de Despiece de Camiseta</h4>", unsafe_allow_html=True)
        
        pattern_col1, pattern_col2, pattern_col3 = st.columns([2, 2, 1])
        
        with pattern_col1:
            st.markdown("""
                <div style='background: #fff; color: #000; border-radius: 12px; padding: 20px; height: 380px; display: flex; flex-direction: column; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.3);'>
                    <p style='font-size: 12px; font-weight: bold; margin-bottom: 10px;'>FRENTE</p>
                    <div style='border: 2px dashed #00cec9; border-radius: 50%; width: 100px; height: 100px; display: flex; align-items: center; justify-content: center; background: #f9f9f9;'>
                        <span style='font-size: 24px;'>🐻</span>
                    </div>
                    <p style='font-size: 10px; color: #666; margin-top: 10px;'>Pixel Thread Logo</p>
                </div>
            """, unsafe_allow_html=True)
            
        with pattern_col2:
            st.markdown("""
                <div style='background: #fff; color: #000; border-radius: 12px; padding: 20px; height: 380px; display: flex; flex-direction: column; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.3);'>
                    <p style='font-size: 12px; font-weight: bold; margin-bottom: 10px;'>ESPALDA</p>
                    <div style='border: 2px dashed #ccc; border-radius: 50%; width: 100px; height: 100px; display: flex; align-items: center; justify-content: center; background: #f9f9f9;'>
                        <span style='font-size: 12px; color: #999;'>Vacío</span>
                    </div>
                    <p style='font-size: 10px; color: #666; margin-top: 10px;'>Área libre</p>
                </div>
            """, unsafe_allow_html=True)

        with pattern_col3:
            st.markdown("""
                <div style='background: #fff; color: #000; border-radius: 12px; padding: 10px; height: 380px; display: flex; flex-direction: column; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.3);'>
                    <p style='font-size: 10px; font-weight: bold;'>MANGAS</p>
                    <div style='border: 1px solid #ccc; width: 60px; height: 40px; margin-bottom: 15px; background: #f9f9f9;'></div>
                    <div style='border: 1px solid #ccc; width: 60px; height: 40px; background: #f9f9f9;'></div>
                </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        tools_col1, tools_col2, tools_col3, tools_col4 = st.columns(4)
        with tools_col1:
            st.markdown("↩️ Deshacer")
        with tools_col2:
            zoom_val = st.slider("Zoom", 50, 200, 100, label_visibility="collapsed")
        with tools_col3:
            st.markdown("👁️ Vista Previa")
        with tools_col4:
            st.markdown("⚡ **Estado: Sincronizado**")
            
        st.markdown('</div>', unsafe_allow_html=True)

    # --- PANEL DERECHO: Vista Previa 3D y Selector de Color ---
    with col_right:
        st.markdown('<div class="preview-box">', unsafe_allow_html=True)
        st.markdown("#### 🧊 Visor 3D en Vivo")
        
        shirt_color = st.color_picker("Color Base del Producto", "#ffffff")
        
        model_viewer_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
            <style>
                body {{ margin: 0; background-color: #262626; }}
                model-viewer {{
                    width: 100%;
                    height: 360px;
                    background-color: #1e1e1e;
                    border-radius: 12px;
                }}
            </style>
        </head>
        <body>
            <model-viewer 
                src="https://modelviewer.dev/shared-assets/models/Astronaut.glb" 
                alt="Maqueta 3D" 
                auto-rotate 
                camera-controls 
                ar>
            </model-viewer>
        </body>
        </html>
        """
        
        st.components.v1.html(model_viewer_html, height=380)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Mis Pedidos Guardados en Firebase:**")
        
        # Mostrar los pedidos recientes del usuario actual de forma integrada
        try:
            todos = list(db.collection("pedidos_bordado").order_by("timestamp").stream())
            mis_pedidos = [p.to_dict() for p in todos if p.to_dict().get("cliente", "").strip().lower() == st.session_state.user.strip().lower()]
            
            if mis_pedidos:
                for p in mis_pedidos[-2:]: # Mostrar últimos 2
                    with st.container(border=True):
                        st.caption(f"🧵 {p.get('nombre_proyecto')} | Turno: #{p.get('turno')}")
                        render_estado_badge(p.get('estado', 'Pendiente'))
                        
                        # Descarga de archivos entregables si ya están listos
                        archivos_finales = limpiar_lista_archivos(p.get('archivos_finales', []))
                        if archivos_finales:
                            for af in archivos_finales:
                                try:
                                    raw_bytes = base64.b64decode(af.get('data'))
                                    st.download_button(f"📥 Descargar {af.get('nombre')}", data=raw_bytes, file_name=af.get('nombre'), key=f"dl_{p.get('id')}_{af.get('nombre')}")
                                except Exception:
                                    pass
            else:
                st.info("No hay pedidos guardados todavía.")
        except Exception:
            st.caption("Conectando con base de datos...")
            
        st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 2. PANEL DE ADMINISTRADOR (GESTIÓN DE PEDIDOS Y FIREBASE)
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
