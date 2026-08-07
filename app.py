import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import base64
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Pixel Thread | Pro", layout="wide")
st_autorefresh(interval=10000, limit=1000, key="auto_refrescar")

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
    .block-container {
        max-width: 100% !important;
        padding-left: 3rem;
        padding-right: 3rem;
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
# 1. PANEL DE CLIENTE (EJEMPLO DE GRILLA HORIZONTAL DE PEDIDOS)
# =========================================================
if st.session_state.modo_vista == "Cliente":
    user_input = st.text_input("Ingresa tu Nombre o ID de Usuario:", value=st.session_state.user)
    if user_input != st.session_state.user:
        actualizar_url("Cliente", user_input)

    if not st.session_state.user.strip():
        st.info("👆 Por favor, ingresa tu nombre o ID de usuario arriba para acceder a tus pedidos.")
    else:
        try:
            user_doc_ref = db.collection("usuarios_perfil").document(st.session_state.user.strip().lower())
            user_doc = user_doc_ref.get()
            
            nombre_cliente = st.session_state.user
            logo_cliente_b64 = None
            if user_doc.exists:
                data_u = user_doc.to_dict()
                nombre_cliente = data_u.get('nombre_usuario', st.session_state.user)
                logo_cliente_b64 = data_u.get('logo_b64', None)

            col_c1, col_c2 = st.columns([0.1, 3.9])
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
            st.subheader("📋 Estado de Mis Pedidos (Organización en Tarjetas Horizontales)")

            todos = list(db.collection("pedidos_bordado").order_by("timestamp").stream())
            mis_pedidos = [p.to_dict() for p in todos if p.to_dict().get("cliente", "").strip().lower() == st.session_state.user.strip().lower()]

            if mis_pedidos:
                pedidos_activos = [p for p in mis_pedidos if p.get('estado') != "Completado"]
                
                # ORGANIZACIÓN EN GRILLA HORIZONTAL (2 columnas de tarjetas por fila)
                if pedidos_activos:
                    for i in range(0, len(pedidos_activos), 2):
                        cols = st.columns(2)
                        for j in range(2):
                            if i + j < len(pedidos_activos):
                                p = pedidos_activos[i + j]
                                with cols[j]:
                                    with st.container():
                                        st.markdown(f"### 🧵 {p.get('nombre_proyecto')}")
                                        st.markdown(f"**ID:** `{p.get('id')}` | **Estado:** `{p.get('estado')}`")
                                        st.markdown(f"**Prod:** {p.get('producto')} | **Ubi:** {p.get('ubicacion')}")
                                        if p.get('comentarios'):
                                            st.markdown(f"*Comentarios:* {p.get('comentarios')}")
                                        
                                        archivos = p.get('archivos', [])
                                        if archivos:
                                            st.markdown("🖼️ **Archivos:**")
                                            for idx_a, arch_item in enumerate(archivos):
                                                nombre_a = arch_item.get('nombre', 'archivo')
                                                data_a = arch_item.get('data')
                                                try:
                                                    st.download_button(f"📥 {nombre_a}", data=base64.b64decode(data_a), file_name=nombre_a, key=f"grid_orig_{p.get('id')}_{idx_a}")
                                                except Exception:
                                                    pass
                                        st.markdown("---")
                else:
                    st.info("No tienes pedidos pendientes o en proceso en este momento.")
            else:
                st.info(f"No hay pedidos registrados para: {st.session_state.user}")

        except Exception as e:
            if "ResourceExhausted" in str(type(e).__name__) or "quota" in str(e).lower():
                st.error("⚠️ Límite de consultas a la base de datos alcanzado temporalmente. Por favor, espera unos segundos y recarga la página.")
            else:
                st.error(f"Error al cargar historial: {e}")

# =========================================================
# 2. PANEL DE ADMINISTRADOR (GRILLA HORIZONTAL DE PEDIDAS)
# =========================================================
else:
    st.subheader("🛠️ Panel de Administración (Vista en Tarjetas Horizontales)")

    try:
        docs = list(db.collection("pedidos_bordado").order_by("timestamp").stream())
        pedidos_activos = [(doc.id, doc.to_dict()) for doc in docs if doc.to_dict().get('estado') != "Completado"]

        if pedidos_activos:
            # Organizar la vista de administración en filas de 2 columnas horizontales
            for i in range(0, len(pedidos_activos), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i + j < len(pedidos_activos):
                        doc_id, p = pedidos_activos[i + j]
                        with cols[j]:
                            with st.container():
                                st.markdown(f"### 👤 {p.get('cliente')} — 🧵 {p.get('nombre_proyecto')}")
                                st.markdown(f"**ID:** `{p.get('id')}` | **Estado:** `{p.get('estado')}`")
                                st.text(f"Prod: {p.get('producto')} | Ubi: {p.get('ubicacion')}")
                                
                                # Subir entregables dentro de la tarjeta horizontal
                                with st.expander("📤 Subir Entregable", expanded=False):
                                    archivos_entregables = st.file_uploader(
                                        "Archivos finalizados:", 
                                        type=["dst", "emb", "pes", "png", "jpg", "pdf"],
                                        accept_multiple_files=True, 
                                        key=f"grid_upload_{doc_id}"
                                    )
                                    if st.button("🚀 ENVIAR AL CLIENTE", key=f"grid_btn_{doc_id}"):
                                        if archivos_entregables:
                                            lista_finales = p.get('archivos_finales', [])
                                            for af in archivos_entregables:
                                                lista_finales.append({
                                                    "nombre": af.name,
                                                    "data": base64.b64encode(af.getvalue()).decode("utf-8")
                                                })
                                            db.collection("pedidos_bordado").document(doc_id).update({
                                                "archivos_finales": lista_finales,
                                                "estado": "Completado"
                                            })
                                            st.success("¡Enviado!")
                                            st.rerun()
                                        else:
                                            st.warning("Adjunta un archivo.")

                                if st.button(f"🗑️ Eliminar Pedido", key=f"grid_del_{doc_id}"):
                                    db.collection("pedidos_bordado").document(doc_id).delete()
                                    st.warning("Eliminado.")
                                    st.rerun()
                                st.markdown("---")
        else:
            st.info("🎉 No hay pedidos pendientes.")

    except Exception as e:
        if "ResourceExhausted" in str(type(e).__name__) or "quota" in str(e).lower():
            st.error("⚠️ Límite de consultas a la base de datos alcanzado temporalmente. Por favor, espera unos segundos y recarga la página.")
        else:
            st.error(f"Error al cargar administración: {e}")
