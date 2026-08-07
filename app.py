import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import base64
from streamlit_autorefresh import st_autorefresh

# Configuración de página optimizada para móvil
st.set_page_config(page_title="Pixel Thread - Portal Interactivo", layout="centered")

# Auto-refresco de la página cada 5 segundos (5000 ms)
count = st_autorefresh(interval=5000, limit=1000, key="auto_refrescar_cliente")

# --- ESTILOS FUTURISTAS Y COMPONENTES VISUALES ---
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
        transition: 0.2s;
    }
    div.stButton > button:hover {
        opacity: 0.85;
    }
    h1, h2, h3 {
        color: #00ffcc !important;
    }
    .stTextInput input, .stSelectbox select {
        background-color: #0b0f19;
        color: white;
        border: 1px solid #00ffcc55;
    }
</style>
""", unsafe_allow_html=True)

# --- CONEXIÓN FIREBASE (SEGURO POR SECCIONES) ---
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

# --- PERSISTENCIA TOTAL MEDIANTE PARÁMETROS DE URL ---
params = st.query_params

vista_en_url = params.get("seccion", "Cliente")
if "modo_vista" not in st.session_state:
    st.session_state.modo_vista = vista_en_url
else:
    if vista_en_url in ["Cliente", "Admin"]:
        st.session_state.modo_vista = vista_en_url

usuario_en_url = params.get("user", "")
if "user" not in st.session_state:
    st.session_state.user = usuario_en_url
else:
    if usuario_en_url:
        st.session_state.user = usuario_en_url

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
    st.title("🧵 Pixel Thread - Portal de Cliente")
    
    # Campo para ingresar el usuario de manera independiente
    user_input = st.text_input("Ingresa tu Nombre o ID de Usuario para continuar:", value=st.session_state.user, key="input_nombre_usuario")
    
    if user_input != st.session_state.user:
        actualizar_url_y_estado("Cliente", user_input)

    if not st.session_state.user.strip():
        st.info("👆 Por favor, ingresa tu nombre o ID de usuario arriba para acceder a tus pedidos y enviar nuevas solicitudes.")
    else:
        # Verificamos si este usuario ya existe en la base de datos de perfiles
        user_doc_ref = db.collection("usuarios_perfil").document(st.session_state.user.strip().lower())
        user_doc = user_doc_ref.get()
        
        # SI EL USUARIO NO EXISTE TODAVÍA (PRIMERA VEZ) -> FORMULARIO DE REGISTRO CON LOGO
        if not user_doc.exists:
            st.warning(f"⚠️ El usuario **{st.session_state.user}** no está registrado. Por favor, sube el logo de tu marca/usuario para completar tu registro por primera vez:")
            
            logo_registro_file = st.file_uploader("Sube el logo de tu usuario (PNG, JPG)", type=["png", "jpg", "jpeg"], key="uploader_logo_registro")
            
            if st.button("✨ Registrar Cuenta y Logo"):
                if logo_registro_file is not None:
                    l_b64 = base64.b64encode(logo_registro_file.getvalue()).decode("utf-8")
                    user_doc_ref.set({
                        "nombre_usuario": st.session_state.user.strip(),
                        "logo_usuario": l_b64,
                        "creado": datetime.now()
                    })
                    st.success("¡Registro completado con éxito!")
                    st.rerun()
                else:
                    st.warning("⚠️ Debes subir una imagen para continuar con el registro.")
        
        # SI EL USUARIO YA EXISTE -> MUESTRA SU PERFIL CON EL LOGO AL LADO Y EL RESTO DE FUNCIONES
        else:
            datos_usuario = user_doc.to_dict()
            logo_perfil_b64 = datos_usuario.get("logo_usuario", "")

            # Contenedor superior con la información del usuario y su logo al lado
            col_perfil1, col_perfil2 = st.columns([3, 1])
            with col_perfil1:
                st.success(f"Sesión activa como: **{st.session_state.user}**")
            with col_perfil2:
                if logo_perfil_b64:
                    st.image(base64.b64decode(logo_perfil_b64), width=60, caption="Tu Logo")

            st.markdown("---")

            # Opción de Enviar Nuevo Pedido
            with st.expander("➕ Enviar Nuevo Pedido", expanded=False):
                with st.form("form_pedido_streamlit", clear_on_submit=True):
                    nombre_proyecto = st.text_input("1. Nombre o Referencia del Proyecto")
                    
                    archivo_subido = st.file_uploader("2. Sube tu Logo del Pedido (PNG, JPG, DST, PES)", type=["png", "jpg", "jpeg", "dst", "pes"])
                    
                    st.markdown("3. **Selecciona el Tipo de Producto:**")
                    tipo_producto = st.radio("Producto:", ["GORRA", "TELA"], horizontal=True, label_visibility="collapsed")
                    
                    ubicacion = "N/A"
                    estilo_frente = "N/A"
                    
                    if tipo_producto == "GORRA":
                        st.markdown("📍 **Ubicación en la Gorra:**")
                        ubicacion = st.radio("Ubicación:", ["FRENTE", "TRASERO", "LATERAL"], horizontal=True, label_visibility="collapsed")
                        
                        if ubicacion == "FRENTE":
                            st.markdown("✨ **Estilo de Bordado (Frente):**")
                            estilo_frente = st.radio("Estilo:", ["3D (Relieve)", "PLANO / FLAT"], horizontal=True, label_visibility="collapsed")

                    submit_pedido = st.form_submit_button("🚀 ENVIAR PEDIDO A PRODUCCIÓN")
                    
                    if submit_pedido:
                        if not nombre_proyecto:
                            st.warning("⚠️ Debes ingresar el nombre del proyecto.")
                        else:
                            img_base64 = ""
                            file_name = "Sin archivo"
                            if archivo_subido is not None:
                                file_name = archivo_subido.name
                                img_base64 = base64.b64encode(archivo_subido.getvalue()).decode("utf-8")

                            data_pedido = {
                                "id": "PT-" + str(int(datetime.now().timestamp())),
                                "cliente": st.session_state.user.strip(),
                                "nombre_proyecto": nombre_proyecto,
                                "producto": tipo_producto,
                                "ubicacion": ubicacion,
                                "estilo": estilo_frente if ubicacion == "FRENTE" else "N/A",
                                "archivo_nombre": file_name,
                                "archivo_data": img_base64,
                                "estado": "Pendiente",
                                "timestamp": datetime.now()
                            }
                            
                            db.collection("pedidos_bordado").add(data_pedido)
                            st.success("¡Pedido enviado y guardado correctamente!")
                            st.rerun()

            st.markdown("---")
            st.subheader("📋 Estado de Mis Pedidos y Posición en Cola")

            try:
                todos_los_pedidos_ref = db.collection("pedidos_bordado").order_by("timestamp").stream()
                
                lista_cola = []
                pedidos_del_cliente = []

                for doc in todos_los_pedidos_ref:
                    p = doc.to_dict()
                    p["doc_id"] = doc.id
                    lista_cola.append(p)
                    if p.get("cliente", "").strip().lower() == st.session_state.user.strip().lower():
                        pedidos_del_cliente.append(p)

                if pedidos_del_cliente:
                    for pedido in pedidos_del_cliente:
                        estado = pedido.get("estado", "Pendiente")
                        
                        posicion_cola = "N/A (Finalizado o En Proceso)"
                        if estado != "Completado":
                            pendientes_antes = [
                                item for item in lista_cola 
                                if item.get("estado") != "Completado" and item["timestamp"] <= pedido["timestamp"]
                            ]
                            posicion_cola = len(pendientes_antes)

                        color_estado = "⏳" if estado == "Pendiente" else ("⚙️" if estado == "En Proceso" else "✅")

                        with st.container():
                            st.markdown(f"### {color_estado} Proyecto: {pedido.get('nombre_proyecto')}")
                            st.markdown(f"**ID de Orden:** `{pedido.get('id')}`")
                            st.markdown(f"**Estado Actual:** `{estado}`")
                            
                            if estado != "Completado":
                                st.info(f"📊 **Posición en la cola de producción:** #{posicion_cola}")
                            else:
                                st.success("🎉 ¡Tu pedido ha sido completado con éxito por el taller!")

                            st.markdown(f"*Producto:* {pedido.get('producto')} | *Ubicación:* {pedido.get('ubicacion')}")
                            
                            # Vista previa miniatura si el archivo es imagen
                            archivo_nombre = pedido.get('archivo_nombre', '').lower()
                            archivo_data = pedido.get('archivo_data', '')
                            if archivo_data and (archivo_nombre.endswith('.png') or archivo_nombre.endswith('.jpg') or archivo_nombre.endswith('.jpeg')):
                                st.markdown("**Vista Previa del Archivo:**")
                                st.image(base64.b64decode(archivo_data), width=120)
                            elif archivo_data:
                                st.text(f"Archivo adjunto: {pedido.get('archivo_nombre')} (Vista previa no disponible para este formato)")

                            st.markdown("---")
                else:
                    st.info(f"No tienes pedidos registrados todavía bajo el usuario: **{st.session_state.user}**")

            except Exception as e:
                st.error(f"Error al cargar los datos del cliente: {e}")

# =========================================================
# 2. PANEL DE ADMINISTRADOR
# =========================================================
else:
    st.title("🛠️ Panel de Administración")
    st.subheader("📋 Gestión de Pedidos Entrantes")

    try:
        docs = db.collection("pedidos_bordado").order_by("timestamp").stream()
        contador = 0

        for doc in docs:
            contador += 1
            p = doc.to_dict()
            doc_id = doc.id

            with st.container():
                st.markdown(f"### 🆔 {p.get('id', 'S/ID')} - {p.get('nombre_proyecto')}")
                st.text(f"Cliente: {p.get('cliente')} | Creado: {p.get('timestamp')}")
                
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.markdown(f"**Producto:** {p.get('producto')}")
                    if p.get('producto') == 'GORRA':
                        st.markdown(f"**Ubicación:** {p.get('ubicacion')}")
                        if p.get('ubicacion') == 'FRENTE':
                            st.markdown(f"**Estilo:** {p.get('estilo')}")
                with col_info2:
                    st.markdown(f"**Archivo:** {p.get('archivo_nombre')}")
                    
                    a_nombre = p.get('archivo_nombre', '').lower()
                    a_data = p.get('archivo_data', '')
                    if a_data and (a_nombre.endswith('.png') or a_nombre.endswith('.jpg') or a_nombre.endswith('.jpeg')):
                        st.image(base64.b64decode(a_data), width=100, caption="Miniatura del Logo")

                    if a_data:
                        st.download_button(
                            label="📥 Descargar Logo Adjunto",
                            data=base64.b64decode(a_data),
                            file_name=p.get('archivo_nombre'),
                            mime="application/octet-stream",
                            key=f"dl_{doc_id}"
                        )

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
                    st.success("¡Estado actualizado para el cliente!")
                    st.rerun()

                if st.button(f"🗑️ Eliminar Pedido {p.get('id')}", key=f"del_{doc_id}"):
                    db.collection("pedidos_bordado").document(doc_id).delete()
                    st.warning("Pedido eliminado permanentemente.")
                    st.rerun()

                st.markdown("---")

        if contador == 0:
            st.info("No hay pedidos registrados en el sistema.")

    except Exception as e:
        st.error(f"Error al conectar con la base de datos de Firebase: {e}")
