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

# Contador para limpiar los inputs del formulario dinámicamente
if "form_version" not in st.session_state:
    st.session_state.form_version = 0

def actualizar_url_y_estado(nueva_vista, nuevo_usuario):
    st.session_state.modo_vista = nueva_vista
    st.session_state.user = nuevo_usuario
    st.query_params["seccion"] = nueva_vista
    st.query_params["user"] = nuevo_usuario
    st.rerun()

# Lista de administradores autorizados
ADMINS_AUTORIZADOS = ["Pixel2580", "eric"]

# Barra superior de navegación entre paneles
col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("👤 Panel de Cliente"):
        actualizar_url_y_estado("Cliente", st.session_state.user)
with col_nav2:
    if st.button("🛠️ Panel Admin"):
        usuario_actual = st.session_state.user.strip()
        if usuario_actual in ADMINS_AUTORIZADOS:
            actualizar_url_y_estado("Admin", st.session_state.user)
        else:
            st.error("❌ Acceso denegado: Tu usuario no tiene permisos de administrador.")

st.markdown("---")

# =========================================================
# 1. PANEL DE CLIENTE
# =========================================================
if st.session_state.modo_vista == "Cliente":
    
    user_input = st.text_input("Ingresa tu Nombre o ID de Usuario para continuar:", value=st.session_state.user)
    if user_input != st.session_state.user:
        actualizar_url_y_estado("Cliente", user_input)

    if not st.session_state.user.strip():
        st.title("Pixel Thread - Portal de Cliente")
        st.info("👆 Por favor, ingresa tu nombre o ID de usuario arriba para acceder a tus pedidos.")
    else:
        user_doc_ref = db.collection("usuarios_perfil").document(st.session_state.user.strip().lower())
        user_doc = user_doc_ref.get()
        
        nombre_cliente = st.session_state.user
        logo_cliente_b64 = None
        if user_doc.exists:
            data_u = user_doc.to_dict()
            nombre_cliente = data_u.get('nombre_usuario', st.session_state.user)
            logo_cliente_b64 = data_u.get('logo_b64', None)

        # Cabecera centralizada horizontalmente con el icono exactamente del tamaño del cuadro rojo (ancho mayor) y al lado del nombre
        col_esp_izq, col_contenido, col_esp_der = st.columns([1, 4, 1])
        with col_contenido:
            sub_c1, sub_c2 = st.columns([0.42, 3.58])
            with sub_c1:
                if logo_cliente_b64:
                    try:
                        st.image(base64.b64decode(logo_cliente_b64), width=120)
                    except Exception:
                        st.markdown("<h1 style='margin: 0; font-size: 60px;'>👤</h1>", unsafe_allow_html=True)
                else:
                    st.markdown("<h1 style='margin: 0; font-size: 60px;'>👤</h1>", unsafe_allow_html=True)
            with sub_c2:
                st.markdown(f"<h1 style='margin: 0; padding-top: 24px;'>{nombre_cliente}</h1>", unsafe_allow_html=True)
        
        if st.session_state.mensaje_exito:
            st.success(st.session_state.mensaje_exito)
            st.session_state.mensaje_exito = ""

        st.markdown("---")

        fv = st.session_state.form_version

        with st.expander("➕ Enviar Nuevo Pedido", expanded=st.session_state.expandir_nuevo_pedido):
            st.markdown("📦 **Tipo de Producto:**")
            tipo_producto = st.radio("Producto:", ["GORRA", "TELA", "VARIOS"], horizontal=True, label_visibility="collapsed", key=f"input_tipo_prod_{fv}")

            ubicacion = "N/A"
            estilo_frente = "N/A"

            if tipo_producto == "GORRA":
                st.markdown("📍 **Ubicación en la Gorra:**")
                ubicacion = st.radio("Ubicación:", ["FRENTE", "TRASERO", "LATERAL"], horizontal=True, label_visibility="collapsed", key=f"input_ubicacion_{fv}")
                if ubicacion == "FRENTE":
                    st.markdown("✨ **Estilo de Bordado (Frente):**")
                    estilo_frente = st.radio("Estilo:", ["3D (Relieve)", "PLANO / FLAT"], horizontal=True, label_visibility="collapsed", key=f"input_estilo_{fv}")

            st.markdown("---")

            nombre_proyecto = st.text_input("1. Nombre o Referencia del Proyecto", key=f"input_nombre_proyecto_{fv}")
            archivos_subidos = st.file_uploader(
                "2. Sube tus Archivos del Pedido (PNG, JPG, DST, PES, PDF, EMB)", 
                type=["png", "jpg", "jpeg", "dst", "pes", "pdf", "emb"],
                accept_multiple_files=True,
                key=f"input_archivos_{fv}"
            )
            comentarios = st.text_area("3. Comentarios o Instrucciones Adicionales (Opcional)", key=f"input_comentarios_{fv}")
            
            status_placeholder = st.empty()
            
            if st.button("🚀 ENVIAR PEDIDO A PRODUCCIÓN", key=f"btn_enviar_pedido_prod_{fv}"):
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
                            "archivos_finales": [],
                            "comentarios": str(comentarios),
                            "estado": "Pendiente",
                            "timestamp": datetime.now()
                        }
                        
                        ref = db.collection("pedidos_bordado").document()
                        ref.set(data_pedido)
                        
                        if ref.get().exists:
                            st.session_state.mensaje_exito = "🎉 ¡Pedido enviado con éxito a producción!"
                            st.session_state.form_version += 1
                            st.rerun() 
                        else:
                            status_placeholder.error("❌ El pedido no pudo ser verificado en la base de datos.")
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
                            st.markdown("**Tus Archivos Adjuntos:**")
                            for arch in archivos:
                                nombre_arch = arch.get('nombre', '')
                                data_arch = arch.get('data', '')
                                st.text(f"📄 {nombre_arch}")
                                if data_arch and nombre_arch.lower().endswith(('.png', '.jpg', '.jpeg')):
                                    try:
                                        st.image(base64.b64decode(data_arch), width=150)
                                    except Exception:
                                        pass

                        archivos_finales = pedido.get('archivos_finales', [])
                        if archivos_finales:
                            st.success("✅ ¡Tu pedido está completo! Descarga tus archivos finales aquí:")
                            for idx_af, af in enumerate(archivos_finales):
                                st.download_button(
                                    label=f"📥 Descargar Entregable: {af.get('nombre')}",
                                    data=base64.b64decode(af.get('data')),
                                    file_name=af.get('nombre'),
                                    mime="application/octet-stream",
                                    key=f"client_dl_{pedido.get('id')}_{idx_af}"
                                )

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
    
    # --- REGISTRO DE CLIENTES ---
    with st.expander("➕ Registrar Nuevo Cliente", expanded=False):
        with st.form("form_nuevo_cliente_admin", clear_on_submit=True):
            nuevo_id_cliente = st.text_input("ID o Nombre del Nuevo Cliente")
            logo_nuevo_subido = st.file_uploader("Logo / Icono del Cliente (Opcional)", type=["png", "jpg", "jpeg"])
            submit_registro = st.form_submit_button("✨ Crear Cliente")
            
            if submit_registro:
                if not nuevo_id_cliente.strip():
                    st.warning("⚠️ Ingresa un ID para el cliente.")
                else:
                    doc_ref_nuevo = db.collection("usuarios_perfil").document(nuevo_id_cliente.strip().lower())
                    if doc_ref_nuevo.get().exists:
                        st.error("⚠️ Este cliente ya existe.")
                    else:
                        logo_b64 = None
                        if logo_nuevo_subido:
                            img_bytes = logo_nuevo_subido.getvalue()
                            logo_b64 = base64.b64encode(img_bytes).decode("utf-8")

                        doc_ref_nuevo.set({
                            "nombre_usuario": nuevo_id_cliente.strip(),
                            "logo_b64": logo_b64,
                            "creado": datetime.now()
                        })
                        st.success(f"¡Cliente '{nuevo_id_cliente.strip()}' registrado exitosamente!")
                        st.rerun()

    st.markdown("---")

    # --- GESTIÓN DE CLIENTES EXISTENTES (MINIMIZABLE) ---
    with st.expander("👥 Gestión de Clientes Existentes", expanded=False):
        try:
            clientes_docs = list(db.collection("usuarios_perfil").stream())
            if not clientes_docs:
                st.info("No hay clientes registrados.")
            
            for c_doc in clientes_docs:
                c_data = c_doc.to_dict()
                c_id = c_doc.id
                c_logo = c_data.get('logo_b64', None)
                
                with st.container():
                    col_logo, col_c1, col_c2, col_c3 = st.columns([0.5, 2.5, 1, 1])
                    with col_logo:
                        if c_logo:
                            try:
                                st.image(base64.b64decode(c_logo), width=35)
                            except Exception:
                                st.write("🖼️")
                        else:
                            st.write("👤")
                    with col_c1:
                        st.write(f"**{c_data.get('nombre_usuario')}** (`{c_id}`)")
                    
                    with col_c2:
                        if st.button("✏️ Editar", key=f"edit_{c_id}"):
                            st.session_state[f"edit_mode_{c_id}"] = not st.session_state.get(f"edit_mode_{c_id}", False)
                    
                    with col_c3:
                        if st.button("🗑️ Borrar", key=f"del_client_{c_id}"):
                            db.collection("usuarios_perfil").document(c_id).delete()
                            st.warning(f"Cliente {c_id} eliminado.")
                            st.rerun()

                    # Formulario de Edición inline para el cliente
                    if st.session_state.get(f"edit_mode_{c_id}", False):
                        with st.form(key=f"form_edit_client_{c_id}"):
                            nuevo_nombre_cliente = st.text_input("Modificar Nombre/ID:", value=c_data.get('nombre_usuario', ''))
                            nuevo_logo_subido = st.file_uploader("Actualizar Logo / Icono (Opcional)", type=["png", "jpg", "jpeg"], key=f"logo_up_{c_id}")
                            
                            if st.form_submit_button("💾 Guardar Cambios"):
                                update_data = {"nombre_usuario": nuevo_nombre_cliente.strip()}
                                if nuevo_logo_subido:
                                    update_data["logo_b64"] = base64.b64encode(nuevo_logo_subido.getvalue()).decode("utf-8")
                                
                                db.collection("usuarios_perfil").document(c_id).update(update_data)
                                st.session_state[f"edit_mode_{c_id}"] = False
                                st.success("¡Cliente actualizado con éxito!")
                                st.rerun()
                    st.markdown("---")
        except Exception as e:
            st.error(f"Error al cargar clientes: {e}")

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
                    st.markdown("**Archivos Originales del Pedido:**")
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

                st.markdown("---")
                st.markdown("📤 **Subir Archivos Finales / Entregables (Múltiples archivos permitidos):**")
                
                archivos_finales_subidos = st.file_uploader(
                    f"Subir entregables para {p.get('nombre_proyecto')}", 
                    accept_multiple_files=True,
                    key=f"up_final_{doc_id}"
                )
                
                if archivos_finales_subidos:
                    if st.button(f"💾 Guardar y Enviar Entregables", key=f"btn_save_final_{doc_id}"):
                        try:
                            lista_finales = p.get("archivos_finales", [])
                            
                            for archivo_final in archivos_finales_subidos:
                                bytes_final = archivo_final.getvalue()
                                b64_final = base64.b64encode(bytes_final).decode("utf-8")
                                
                                lista_finales.append({
                                    "nombre": str(archivo_final.name.strip()),
                                    "data": b64_final
                                })
                            
                            db.collection("pedidos_bordado").document(doc_id).update({
                                "archivos_finales": lista_finales,
                                "estado": "Completado"
                            })
                            st.success("¡Archivos finales guardados y orden marcada como completada con éxito!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al subir los archivos finales: {e}")

                archivos_finales_actuales = p.get("archivos_finales", [])
                if archivos_finales_actuales:
                    st.markdown("✔️ **Entregables actuales en la nube:**")
                    for idx_af_admin, af_item in enumerate(archivos_finales_actuales):
                        st.text(f"• {af_item.get('nombre')}")

                st.markdown("---")
                
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

                st.markdown("==================================================")

    except Exception as e:
        st.error(f"Error al conectar con Firebase: {e}")
