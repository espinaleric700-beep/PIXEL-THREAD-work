import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import base64
import io
from PIL import Image
from streamlit_autorefresh import st_autorefresh

# Configuración de página optimizada
st.set_page_config(page_title="Pixel Thread - Portal Interactivo", layout="centered")

# Auto-refresco de la página cada 5 segundos
st_autorefresh(interval=5000, limit=1000, key="auto_refrescar_cliente")

# --- ESTILOS VISUALES ---
st.markdown("""
<style>
    .stApp {
        background: radial-gradient(circle at center, #1a0033 0%, #000000 100%);
        color: #00ffcc;
    }
    div.stButton > button {
        width: 100%;
        background-color: #00ffcc;
        color: black;
        font-weight: bold;
        border: none;
        border-radius: 6px;
        padding: 0.6rem;
    }
    h1, h2, h3 {
        color: #00ffcc !important;
    }
</style>
""", unsafe_allow_html=True)

# --- CONEXIÓN FIREBASE ---
@st.cache_resource
def init_fb():
    if not firebase_admin._apps:
        cred_dict = {
            "type": st.secrets["firebase"]["type"],
            "project_id": st.secrets["firebase"]["project_id"],
            "private_key_id": st.secrets["firebase"]["private_key_id"],
            "private_key": st.secrets["firebase"]["private_key"],
            "client_email": st.secrets["firebase"]["client_email"],
            "client_id": st.secrets["firebase"]["client_id"],
            "auth_uri": st.secrets["firebase"]["auth_uri"],
            "token_uri": st.secrets["firebase"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"],
            "universe_domain": st.secrets["firebase"]["universe_domain"]
        }
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_fb()

# --- NAVEGACIÓN Y ESTADO ---
params = st.query_params
vista_en_url = params.get("seccion", "Cliente")

if "modo_vista" not in st.session_state:
    st.session_state.modo_vista = vista_en_url
if "user" not in st.session_state:
    st.session_state.user = params.get("user", "")

# Control de estado del expander
if "expandir_nuevo_pedido" not in st.session_state:
    st.session_state.expandir_nuevo_pedido = False

# Estado para mostrar el aviso de éxito temporalmente
if "mensaje_exito" not in st.session_state:
    st.session_state.mensaje_exito = ""

def actualizar_url_y_estado(nueva_vista, nuevo_usuario):
    st.session_state.modo_vista = nueva_vista
    st.session_state.user = nuevo_usuario
    st.query_params["seccion"] = nueva_vista
    st.query_params["user"] = nuevo_usuario
    st.rerun()

# Barra superior de navegación entre paneles
col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("👤 Panel de Cliente"):
        actualizar_url_y_estado("Cliente", st.session_state.user)
with col_nav2:
    if st.button("🛠️ Panel Admin"):
        actualizar_url_y_estado("Admin", st.session_state.user)

st.markdown("---")

# =========================================================
# 1. PANEL DE CLIENTE
# =========================================================
if st.session_state.modo_vista == "Cliente":
    
    user_input = st.text_input("Ingresa tu Nombre o ID de Usuario para continuar:", value=st.session_state.user)
    if user_input != st.session_state.user:
        actualizar_url_y_estado("Cliente", user_input)

    if not st.session_state.user.strip():
        st.title("🧵 Pixel Thread - Portal de Cliente")
        st.info("👆 Por favor, ingresa tu nombre o ID de usuario arriba para acceder a tus pedidos.")
    else:
        user_doc_ref = db.collection("usuarios_perfil").document(st.session_state.user.strip().lower())
        user_doc = user_doc_ref.get()
        
        nombre_cliente = st.session_state.user
        if user_doc.exists:
            nombre_cliente = user_doc.to_dict().get('nombre_usuario', st.session_state.user)

        st.title(f"🧵 Bienvenido, {nombre_cliente}")
        
        # Muestra el aviso de éxito si existe en la sesión y luego lo limpia
        if st.session_state.mensaje_exito:
            st.success(st.session_state.mensaje_exito)
            st.session_state.mensaje_exito = ""

        st.markdown("---")

        with st.expander("➕ Enviar Nuevo Pedido", expanded=st.session_state.expandir_nuevo_pedido):
            st.markdown("📦 **Tipo de Producto:**")
            tipo_producto = st.radio("Producto:", ["GORRA", "TELA", "VARIOS"], horizontal=True, label_visibility="collapsed", key="input_tipo_prod")

            ubicacion = "N/A"
            estilo_frente = "N/A"

            if tipo_producto == "GORRA":
                st.markdown("📍 **Ubicación en la Gorra:**")
                ubicacion = st.radio("Ubicación:", ["FRENTE", "TRASERO", "LATERAL"], horizontal=True, label_visibility="collapsed", key="input_ubicacion")
                if ubicacion == "FRENTE":
                    st.markdown("✨ **Estilo de Bordado (Frente):**")
                    estilo_frente = st.radio("Estilo:", ["3D (Relieve)", "PLANO / FLAT"], horizontal=True, label_visibility="collapsed", key="input_estilo")

            st.markdown("---")

            nombre_proyecto = st.text_input("1. Nombre o Referencia del Proyecto", key="input_nombre_proyecto")
            archivos_subidos = st.file_uploader(
                "2. Sube tus Archivos del Pedido (PNG, JPG, DST, PES, PDF, EMB)", 
                type=["png", "jpg", "jpeg", "dst", "pes", "pdf", "emb"],
                accept_multiple_files=True,
                key="input_archivos"
            )
            comentarios = st.text_area("3. Comentarios o Instrucciones Adicionales (Opcional)", key="input_comentarios")
            
            status_placeholder = st.empty()
            
            if st.button("🚀 ENVIAR PEDIDO A PRODUCCIÓN", key="btn_enviar_pedido_prod"):
                st.session_state.expandir_nuevo_pedido = False
                
                if not nombre_proyecto:
                    status_placeholder.warning("⚠️ Debes ingresar el nombre o referencia del proyecto.")
                    st.session_state.expandir_nuevo_pedido = True
                elif not archivos_subidos:
                    status_placeholder.error("❌ Error: Debes adjuntar al menos un archivo.")
                    st.session_state.expandir_nuevo_pedido = True
                else:
                    try:
                        status_placeholder.info("⏳ Enviando pedido, por favor espera...")
                        
                        lista_archivos_guardados = []
                        for archivo in archivos_subidos:
                            bytes_contenido = archivo.getvalue()
                            
                            if archivo.name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                                img = Image.open(io.BytesIO(bytes_contenido))
                                if img.mode in ("CMYK", "P"): img = img.convert("RGB")
                                img.thumbnail((1200, 1200))
                                buffered = io.BytesIO()
                                img.save(buffered, format="JPEG" if img.mode != "RGBA" else "PNG", quality=85)
                                bytes_contenido = buffered.getvalue()

                            lista_archivos_guardados.append({
                                "nombre": str(archivo.name.strip()),
                                "data": str(base64.b64encode(bytes_contenido).decode("utf-8"))
                            })

                        data_pedido = {
                            "id": f"PT-{int(datetime.now().timestamp())}",
                            "cliente": str(st.session_state.user.strip()),
                            "nombre_proyecto": str(nombre_proyecto),
                            "producto": str(tipo_producto),
                            "ubicacion": str(ubicacion),
                            "estilo": str(estilo_frente),
                            "archivos": lista_archivos_guardados,
                            "comentarios": str(comentarios),
                            "estado": "Pendiente",
                            "timestamp": datetime.now()
                        }
                        
                        ref = db.collection("pedidos_bordado").document()
                        ref.set(data_pedido)
                        
                        if ref.get().exists:
                            st.session_state.mensaje_exito = "🎉 ¡Pedido enviado con éxito a producción!"
                            st.rerun() 
                        else:
                            status_placeholder.error("❌ El pedido no pudo ser verificado en la base de datos. Inténtalo de nuevo.")
                            st.session_state.expandir_nuevo_pedido = True
                        
                    except Exception as e:
                        status_placeholder.error(f"❌ Error al enviar el pedido: {str(e)}")
                        st.session_state.expandir_nuevo_pedido = True

        st.markdown("---")
        st.subheader("📋 Estado de Mis Pedidos y Posición en Cola")

        try:
            todos_pedidos = list(db.collection("pedidos_bordado").order_by("timestamp").stream())
            pedidos_cliente = [p.to_dict() for p in todos_pedidos if p.to_dict().get("cliente", "").strip().lower() == st.session_state.user.strip().lower()]

            if pedidos_cliente:
                for pedido in pedidos_cliente:
                    estado = pedido.get("estado", "Pendiente")
                    color_estado = "⏳" if estado == "Pendiente" else ("⚙️" if estado == "En Proceso" else "✅")

                    with st.container():
                        st.markdown(f"### {color_estado} Proyecto: {pedido.get('nombre_proyecto')}")
                        st.markdown(f"**ID de Orden:** `{pedido.get('id')}` | **Estado:** `{estado}`")
                        st.markdown(f"*Producto:* {pedido.get('producto')} | *Ubicación:* {pedido.get('ubicacion')} | *Estilo:* {pedido.get('estilo')}")
                        
                        if pedido.get('comentarios'):
                            st.markdown(f"💬 **Comentarios:** {pedido.get('comentarios')}")
                        
                        archivos = pedido.get('archivos', [])
                        if archivos:
                            st.markdown("**Archivos Adjuntos y Logos:**")
                            for arch in archivos:
                                nombre_arch = arch.get('nombre', '')
                                data_arch = arch.get('data', '')
                                st.text(f"📄 {nombre_arch}")
                                if data_arch and nombre_arch.lower().endswith(('.png', '.jpg', '.jpeg')):
                                    try:
                                        st.image(base64.b64decode(data_arch), width=150)
                                    except Exception:
                                        pass
                        st.markdown("---")
            else:
                st.info(f"No tienes pedidos registrados bajo el usuario: **{st.session_state.user}**")
        except Exception as e:
            st.error(f"Error al cargar pedidos: {e}")

# =========================================================
# 2. PANEL DE ADMINISTRADOR
# =========================================================
else:
    st.title("🛠️ Panel de Administración")
    
    with st.expander("➕ Registrar Nuevo Cliente", expanded=False):
        with st.form("form_nuevo_cliente_admin", clear_on_submit=True):
            nuevo_id_cliente = st.text_input("ID o Nombre del Nuevo Cliente")
            logo_cliente_file = st.file_uploader("Logo del Cliente (Opcional)", type=["png", "jpg", "jpeg"])
            submit_registro = st.form_submit_button("✨ Crear Cliente")
            
            if submit_registro:
                if not nuevo_id_cliente.strip():
                    st.warning("⚠️ Ingresa un ID para el cliente.")
                else:
                    doc_ref_nuevo = db.collection("usuarios_perfil").document(nuevo_id_cliente.strip().lower())
                    if doc_ref_nuevo.get().exists:
                        st.error("⚠️ Este cliente ya existe.")
                    else:
                        l_b64 = ""
                        if logo_cliente_file is not None:
                            try:
                                l_b64 = base64.b64encode(logo_cliente_file.getvalue()).decode("utf-8")
                            except Exception:
                                pass
                        
                        doc_ref_nuevo.set({
                            "nombre_usuario": nuevo_id_cliente.strip(),
                            "logo_usuario": l_b64,
                            "creado": datetime.now()
                        })
                        st.success(f"¡Cliente '{nuevo_id_cliente.strip()}' registrado exitosamente!")
                        st.rerun()

    st.markdown("---")
    st.subheader("📋 Gestión de Pedidos Entrantes")

    try:
        docs = list(db.collection("pedidos_bordado").order_by("timestamp").stream())
        if not docs:
            st.info("No hay pedidos registrados en el sistema.")
        
        for doc in docs:
            p = doc.to_dict()
            doc_id = doc.id

            with st.container():
                st.markdown(f"### 🆔 {p.get('id', 'S/ID')} - {p.get('nombre_proyecto')}")
                st.text(f"Cliente: {p.get('cliente')} | Fecha: {p.get('timestamp')}")
                
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.markdown(f"**Producto:** {p.get('producto')}")
                    if p.get('producto') == 'GORRA':
                        st.markdown(f"**Ubicación:** {p.get('ubicacion')}")
                        if p.get('ubicacion') == 'FRENTE':
                            st.markdown(f"**Estilo:** {p.get('estilo')}")
                    if p.get('comentarios'):
                        st.markdown(f"**Comentarios:** {p.get('comentarios')}")
                with col_info2:
                    st.markdown("**Archivos y Logos del Pedido:**")
                    archivos = p.get('archivos', [])
                    for idx, arch in enumerate(archivos):
                        a_nombre = arch.get('nombre', '')
                        a_data = arch.get('data', '')
                        
                        st.text(f"• {a_nombre}")
                        if a_data and a_nombre.lower().endswith(('.png', '.jpg', '.jpeg')):
                            try:
                                st.image(base64.b64decode(a_data), width=100)
                            except Exception:
                                pass

                        if a_data:
                            try:
                                st.download_button(
                                    label=f"📥 Descargar {a_nombre}",
                                    data=base64.b64decode(a_data),
                                    file_name=a_nombre,
                                    mime="application/octet-stream",
                                    key=f"dl_{doc_id}_{idx}"
                                )
                            except Exception:
                                pass

                estado_actual = p.get('estado', 'Pendiente')
                opciones_estado = ["Pendiente", "En Proceso", "Completado"]
                nuevo_estado = st.selectbox(
                    "Estado del Pedido",
                    opciones_estado,
                    index=opciones_estado.index(estado_actual) if estado_actual in opciones_estado else 0,
                    key=f"status_{doc_id}"
                )

                if nuevo_estado != estado_actual:
                    db.collection("pedidos_bordado").document(doc_id).update({"estado": nuevo_estado})
                    st.success("¡Estado actualizado!")
                    st.rerun()

                if st.button(f"🗑️ Eliminar Pedido {p.get('id')}", key=f"del_{doc_id}"):
                    db.collection("pedidos_bordado").document(doc_id).delete()
                    st.warning("Pedido eliminado.")
                    st.rerun()

                st.markdown("---")

    except Exception as e:
        st.error(f"Error al conectar con Firebase: {e}")
