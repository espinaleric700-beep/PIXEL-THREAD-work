import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import base64
import io
from PIL import Image
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Pixel Thread | Pro", layout="centered")
st_autorefresh(interval=5000, limit=1000, key="auto_refrescar")

# --- CSS AVANZADO ---
st.markdown("""
<style>
    :root {
        --primary: #00ffcc;
        --bg-dark: #050505;
    }
    .stApp {
        background: radial-gradient(circle at 50% 50%, #1a0033 0%, #050505 100%);
        background-attachment: fixed;
    }
    .stApp::before {
        content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background-image: linear-gradient(rgba(0, 255, 204, 0.05) 1px, transparent 1px),
                          linear-gradient(90deg, rgba(0, 255, 204, 0.05) 1px, transparent 1px);
        background-size: 50px 50px; pointer-events: none; z-index: 0;
    }
    div[data-testid="stExpander"], div[data-testid="stVerticalBlock"] > div {
        background: rgba(10, 10, 15, 0.6) !important;
        border: 1px solid rgba(0, 255, 204, 0.2) !important;
        border-radius: 12px !important;
        backdrop-filter: blur(10px);
        padding: 15px;
    }
    div.stButton > button {
        background: transparent !important;
        color: var(--primary) !important;
        border: 1px solid var(--primary) !important;
        border-radius: 5px !important;
        transition: all 0.3s ease !important;
        text-transform: uppercase;
        font-weight: bold;
    }
    div.stButton > button:hover {
        background: var(--primary) !important;
        color: black !important;
        box-shadow: 0 0 20px var(--primary) !important;
        transform: translateY(-2px);
    }
    h1, h2, h3 { color: var(--primary) !important; text-transform: uppercase; letter-spacing: 2px; }
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

# --- GESTIÓN DE ESTADOS Y URL ---
params = st.query_params
if "modo_vista" not in st.session_state: 
    st.session_state.modo_vista = params.get("seccion", "Cliente")
if "user" not in st.session_state: 
    st.session_state.user = params.get("user", "")
if "expandir_nuevo_pedido" not in st.session_state: 
    st.session_state.expandir_nuevo_pedido = False
if "mensaje_exito" not in st.session_state: 
    st.session_state.mensaje_exito = ""
if "form_version" not in st.session_state: 
    st.session_state.form_version = 0

def actualizar_url(vista, user):
    st.session_state.modo_vista = vista
    st.session_state.user = user
    st.query_params.update({"seccion": vista, "user": user})
    st.rerun()

ADMINS_AUTORIZADOS = ["Pixel2580", "eric"]

# --- NAVEGACIÓN SUPERIOR ---
st.title("⚡ PIXEL THREAD")
col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("👤 PANEL CLIENTE"): 
        actualizar_url("Cliente", st.session_state.user)
with col_nav2:
    if st.button("🛠️ PANEL ADMIN"): 
        usuario_actual = st.session_state.user.strip()
        if usuario_actual in ADMINS_AUTORIZADOS:
            actualizar_url("Admin", st.session_state.user)
        else:
            st.error("❌ Acceso denegado: Tu usuario no tiene permisos de administrador.")

st.markdown("<br>", unsafe_allow_html=True)

# =========================================================
# 1. PANEL DE CLIENTE
# =========================================================
if st.session_state.modo_vista == "Cliente":
    user_input = st.text_input("Ingresa tu Nombre o ID de Usuario:", value=st.session_state.user)
    if user_input != st.session_state.user:
        actualizar_url("Cliente", user_input)

    if not st.session_state.user.strip():
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

        col_c1, col_c2 = st.columns([0.2, 3.8])
        with col_c1:
            if logo_cliente_b64:
                try:
                    st.image(base64.b64decode(logo_cliente_b64), width=80)
                except Exception:
                    st.markdown("<h3>👤</h3>", unsafe_allow_html=True)
            else:
                st.markdown("<h3>👤</h3>", unsafe_allow_html=True)
        with col_c2:
            st.subheader(f"Bienvenido, {nombre_cliente}")

        if st.session_state.mensaje_exito:
            st.success(st.session_state.mensaje_exito)
            st.session_state.mensaje_exito = ""

        st.markdown("---")
        fv = st.session_state.form_version

        with st.expander("➕ Enviar Nuevo Pedido", expanded=st.session_state.expandir_nuevo_pedido):
            tipo_producto = st.radio("Tipo de Producto:", ["GORRA", "TELA", "VARIOS"], horizontal=True, key=f"prod_{fv}")
            ubicacion, estilo_frente = "N/A", "N/A"

            if tipo_producto == "GORRA":
                ubicacion = st.radio("Ubicación:", ["FRENTE", "TRASERO", "LATERAL"], horizontal=True, key=f"ubi_{fv}")
                if ubicacion == "FRENTE":
                    estilo_frente = st.radio("Estilo:", ["3D (Relieve)", "PLANO / FLAT"], horizontal=True, key=f"est_{fv}")

            nombre_proyecto = st.text_input("Nombre o Referencia del Proyecto", key=f"nom_{fv}")
            archivos_subidos = st.file_uploader("Sube tus Archivos", type=["png", "jpg", "jpeg", "dst", "pes", "pdf", "emb"], accept_multiple_files=True, key=f"arch_{fv}")
            comentarios = st.text_area("Comentarios Adicionales", key=f"com_{fv}")
            status_ph = st.empty()

            if st.button("🚀 ENVIAR PEDIDO A PRODUCCIÓN", key=f"btn_env_{fv}"):
                if not nombre_proyecto:
                    status_ph.warning("⚠️ Debes ingresar el nombre del proyecto.")
                elif not archivos_subidos:
                    status_ph.error("❌ Debes adjuntar al menos un archivo.")
                else:
                    try:
                        status_ph.info("⏳ Enviando pedido...")
                        lista_archivos = []
                        for arch in archivos_subidos:
                            b_cont = arch.getvalue()
                            lista_archivos.append({"nombre": arch.name, "data": base64.b64encode(b_cont).decode("utf-8")})

                        data_pedido = {
                            "id": f"PT-{int(datetime.now().timestamp())}",
                            "cliente": st.session_state.user.strip(),
                            "nombre_proyecto": nombre_proyecto,
                            "producto": tipo_producto,
                            "ubicacion": ubicacion,
                            "estilo": estilo_frente,
                            "archivos": lista_archivos,
                            "archivos_finales": [],
                            "comentarios": comentarios,
                            "estado": "Pendiente",
                            "timestamp": datetime.now()
                        }
                        db.collection("pedidos_bordado").add(data_pedido)
                        st.session_state.mensaje_exito = "🎉 ¡Pedido enviado con éxito!"
                        st.session_state.form_version += 1
                        st.session_state.expandir_nuevo_pedido = False
                        st.rerun()
                    except Exception as e:
                        status_ph.error(f"Error: {e}")

        st.markdown("---")
        st.subheader("📋 Estado de Mis Pedidos")
        try:
            todos = list(db.collection("pedidos_bordado").order_by("timestamp").stream())
            mis_pedidos = [p.to_dict() for p in todos if p.to_dict().get("cliente", "").strip().lower() == st.session_state.user.strip().lower()]

            if mis_pedidos:
                # Separar pedidos activos y completados para el cliente
                pedidos_cliente_activos = []
                pedidos_cliente_completados = []

                for p in mis_pedidos:
                    if p.get('estado') == "Completado":
                        pedidos_cliente_completados.append(p)
                    else:
                        pedidos_cliente_activos.append(p)

                # --- MOSTRAR PEDIDOS ACTIVOS DEL CLIENTE ---
                if pedidos_cliente_activos:
                    for p in pedidos_cliente_activos:
                        with st.container():
                            st.markdown(f"### 🧵 Proyecto: {p.get('nombre_proyecto')}")
                            st.markdown(f"**ID de Pedido:** `{p.get('id')}` | **Estado:** `{p.get('estado')}`")
                            st.markdown(f"**Producto:** {p.get('producto')} | **Ubicación:** {p.get('ubicacion')} | **Estilo:** {p.get('estilo')}")
                            if p.get('comentarios'):
                                st.markdown(f"**Comentarios:** {p.get('comentarios')}")
                            
                            archivos = p.get('archivos', [])
                            if archivos:
                                st.markdown("🖼️ **Archivos Adjuntos:**")
                                cols_arch = st.columns(min(len(archivos), 3))
                                for idx_a, arch_item in enumerate(archivos):
                                    nombre_a = arch_item.get('nombre', 'archivo')
                                    data_a = arch_item.get('data')
                                    with cols_arch[idx_a % len(cols_arch)]:
                                        if nombre_a.lower().endswith(('png', 'jpg', 'jpeg')):
                                            try:
                                                img_bytes = base64.b64decode(data_a)
                                                st.image(img_bytes, caption=nombre_a, width=150)
                                            except Exception:
                                                st.text(nombre_a)
                                        else:
                                            st.text(f"📄 {nombre_a}")
                                        
                                        try:
                                            st.download_button(f"📥 {nombre_a}", data=base64.b64decode(data_a), file_name=nombre_a, key=f"dl_orig_{p.get('id')}_{idx_a}")
                                        except Exception:
                                            pass

                            af = p.get('archivos_finales', [])
                            if af:
                                st.success("✨ ¡Entregables listos para descargar!")
                                for idx_f, f_item in enumerate(af):
                                    st.download_button(
                                        f"📥 Descargar Entregable: {f_item.get('nombre')}", 
                                        data=base64.b64decode(f_item.get('data')), 
                                        file_name=f_item.get('nombre'), 
                                        key=f"dl_client_{p.get('id')}_{idx_f}"
                                    )
                            st.markdown("---")
                else:
                    st.info("No tienes pedidos pendientes o en proceso en este momento.")

                # --- SECCIÓN APARTE: PEDIDOS COMPLETADOS DEL CLIENTE ---
                if pedidos_cliente_completados:
                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.expander(f"📦 Historial de Mis Pedidos Completados / Entregados ({len(pedidos_cliente_completados)})", expanded=False):
                        st.info("Aquí puedes consultar y volver a descargar los entregables de tus trabajos finalizados.")
                        
                        for p in pedidos_cliente_completados:
                            st.markdown(f"### 🧵 Proyecto: {p.get('nombre_proyecto')}")
                            st.markdown(f"**ID de Pedido:** `{p.get('id')}` | **Estado:** `✅ Completado`")
                            st.markdown(f"**Producto:** {p.get('producto')} | **Ubicación:** {p.get('ubicacion')} | **Estilo:** {p.get('estilo')}")
                            
                            af = p.get('archivos_finales', [])
                            if af:
                                st.success("✨ Archivos Entregados:")
                                for idx_f, f_item in enumerate(af):
                                    st.download_button(
                                        f"📥 Descargar: {f_item.get('nombre')}", 
                                        data=base64.b64decode(f_item.get('data')), 
                                        file_name=f_item.get('nombre'), 
                                        key=f"dl_client_comp_{p.get('id')}_{idx_f}"
                                    )
                            st.markdown("---")
            else:
                st.info(f"No hay pedidos registrados para: {st.session_state.user}")
        except Exception as e:
            st.error(f"Error al cargar historial: {e}")

# =========================================================
# 2. PANEL DE ADMINISTRADOR
# =========================================================
else:
    st.subheader("🛠️ Panel de Administración")

    with st.expander("➕ Registrar Nuevo Cliente", expanded=False):
        with st.form("form_cliente", clear_on_submit=True):
            nuevo_id = st.text_input("ID o Nombre del Nuevo Cliente")
            logo_subido = st.file_uploader("Logo Opcional", type=["png", "jpg", "jpeg"])
            if st.form_submit_button("Crear Cliente"):
                if nuevo_id.strip():
                    ref = db.collection("usuarios_perfil").document(nuevo_id.strip().lower())
                    logo_b64 = base64.b64encode(logo_subido.getvalue()).decode("utf-8") if logo_subido else None
                    ref.set({"nombre_usuario": nuevo_id.strip(), "logo_b64": logo_b64, "creado": datetime.now()})
                    st.success("¡Cliente registrado!")
                    st.rerun()

    st.markdown("---")
    st.subheader("📋 Gestión de Pedidos Entrantes")
    try:
        docs = list(db.collection("pedidos_bordado").order_by("timestamp").stream())
        if not docs:
            st.info("No hay pedidos en la base de datos.")
        
        pedidos_activos = []
        pedidos_completados = []

        for doc in docs:
            p_data = doc.to_dict()
            if p_data.get('estado') == "Completado":
                pedidos_completados.append((doc.id, p_data))
            else:
                pedidos_activos.append((doc.id, p_data))

        # --- MOSTRAR PEDIDOS ACTIVOS (Admin) ---
        if pedidos_activos:
            for doc_id, p in pedidos_activos:
                nombre_cliente = p.get('cliente', 'Desconocido')
                nombre_proyecto = p.get('nombre_proyecto', 'Sin Nombre')
                id_pedido = p.get('id', 'Sin ID')
                
                st.markdown(f"### 👤 {nombre_cliente} — 🧵 {nombre_proyecto}")
                st.markdown(f"**ID de Pedido:** `{id_pedido}` | **Estado:** `{p.get('estado')}`")
                st.text(f"Producto: {p.get('producto')} | Ubicación: {p.get('ubicacion')} | Estilo: {p.get('estilo')}")
                if p.get('comentarios'):
                    st.text(f"Comentarios: {p.get('comentarios')}")

                archivos = p.get('archivos', [])
                if archivos:
                    st.markdown("🖼️ **Archivos del Cliente:**")
                    for arch_item in archivos:
                        nombre_a = arch_item.get('nombre', 'archivo')
                        data_a = arch_item.get('data')
                        if nombre_a.lower().endswith(('png', 'jpg', 'jpeg')):
                            try:
                                st.image(base64.b64decode(data_a), caption=nombre_a, width=120)
                            except Exception:
                                pass
                        st.download_button(f"📥 Descargar {nombre_a}", data=base64.b64decode(data_a), file_name=nombre_a, key=f"dl_admin_orig_{id_pedido}_{nombre_a}")

                st.markdown("<br>", unsafe_allow_html=True)

                with st.expander("📤 Subir Entregables / Archivo Digitalizado para el Cliente", expanded=False):
                    archivos_entregables = st.file_uploader(
                        "Selecciona los archivos finalizados (.DST, .EMB, .PES, .PNG, etc.):", 
                        type=["dst", "emb", "pes", "png", "jpg", "jpeg", "pdf"],
                        accept_multiple_files=True, 
                        key=f"upload_final_{doc_id}"
                    )
                    if st.button("🚀 ENVIAR ARCHIVO AL CLIENTE", key=f"btn_send_final_{doc_id}"):
                        if archivos_entregables:
                            lista_finales = p.get('archivos_finales', [])
                            for af in archivos_entregables:
                                b_cont = af.getvalue()
                                lista_finales.append({
                                    "nombre": af.name,
                                    "data": base64.b64encode(b_cont).decode("utf-8")
                                })
                            db.collection("pedidos_bordado").document(doc_id).update({
                                "archivos_finales": lista_finales,
                                "estado": "Completado"
                            })
                            st.success("¡Archivos enviados correctamente al cliente!")
                            st.rerun()
                        else:
                            st.warning("⚠️ Debes adjuntar al menos un archivo para enviar.")

                af_existentes = p.get('archivos_finales', [])
                if af_existentes:
                    st.markdown("✅ **Entregables Ya Subidos:**")
                    for idx_fe, fe_item in enumerate(af_existentes):
                        st.text(f"📄 {fe_item.get('nombre')}")

                estados = ["Pendiente", "En Proceso", "Completado"]
                est_actual = p.get('estado', 'Pendiente')
                nuevo_est = st.selectbox("Actualizar Estado Manualmente", estados, index=estados.index(est_actual) if est_actual in estados else 0, key=f"st_{doc_id}")
                if nuevo_est != est_actual:
                    db.collection("pedidos_bordado").document(doc_id).update({"estado": nuevo_est})
                    st.success("¡Estado actualizado!")
                    st.rerun()
                
                if st.button(f"🗑️ Eliminar Pedido {id_pedido}", key=f"del_{doc_id}"):
                    db.collection("pedidos_bordado").document(doc_id).delete()
                    st.warning("Pedido eliminado.")
                    st.rerun()
                st.markdown("---")
        else:
            st.info("🎉 No hay pedidos pendientes o en proceso en este momento.")

        # --- SECCIÓN APARTE: PEDIDOS COMPLETADOS / ENTREGADOS (Admin) ---
        if pedidos_completados:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander(f"🗂️ Historial de Pedidos Entregados / Completados ({len(pedidos_completados)})", expanded=False):
                st.info("Aquí se encuentran los pedidos que ya fueron completados y entregados a los clientes.")
                
                for doc_id, p in pedidos_completados:
                    nombre_cliente = p.get('cliente', 'Desconocido')
                    nombre_proyecto = p.get('nombre_proyecto', 'Sin Nombre')
                    id_pedido = p.get('id', 'Sin ID')
                    
                    st.markdown(f"### 👤 {nombre_cliente} — 🧵 {nombre_proyecto}")
                    st.markdown(f"**ID de Pedido:** `{id_pedido}` | **Estado:** `✅ Completado`")
                    st.text(f"Producto: {p.get('producto')} | Ubicación: {p.get('ubicacion')} | Estilo: {p.get('estilo')}")
                    
                    col_op1, col_op2 = st.columns(2)
                    with col_op1:
                        if st.button(f"🔄 Volver a 'Pendiente' {id_pedido}", key=f"revert_{doc_id}"):
                            db.collection("pedidos_bordado").document(doc_id).update({"estado": "Pendiente"})
                            st.rerun()
                    with col_op2:
                        if st.button(f"🗑️ Eliminar Definitivo {id_pedido}", key=f"del_comp_{doc_id}"):
                            db.collection("pedidos_bordado").document(doc_id).delete()
                            st.warning("Pedido eliminado.")
                            st.rerun()
                    st.markdown("---")

    except Exception as e:
        st.error(f"Error al cargar panel de administración: {e}")
