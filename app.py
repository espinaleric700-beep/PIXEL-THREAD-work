import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import base64
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Pixel Thread | Pro", layout="wide")
st_autorefresh(interval=10000, limit=1000, key="auto_refrescar")

# --- CSS AVANZADO PARA DISEÑO HORIZONTAL EN MÓVILES Y PC ---
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
        padding-left: 1.5rem;
        padding-right: 1.5rem;
        padding-top: 2rem;
    }
    div[data-testid="stExpander"], div[data-testid="stVerticalBlock"] > div {
        background: rgba(10, 10, 15, 0.6) !important;
        border: 1px solid rgba(0, 255, 204, 0.2) !important;
        border-radius: 12px !important;
        backdrop-filter: blur(10px);
        padding: 12px;
    }
    div.stButton > button {
        background: transparent !important;
        color: var(--primary) !important;
        border: 1px solid var(--primary) !important;
        border-radius: 5px !important;
        transition: all 0.3s ease !important;
        text-transform: uppercase;
        font-weight: bold;
        width: 100%;
    }
    div.stButton > button:hover {
        background: var(--primary) !important;
        color: black !important;
        box-shadow: 0 0 15px var(--primary) !important;
        transform: translateY(-2px);
    }
    h1, h2, h3 { color: var(--primary) !important; text-transform: uppercase; letter-spacing: 2px; }

    /* Forzar que las columnas se mantengan limpias y compactas en pantallas móviles */
    @media (max-width: 768px) {
        .stColumns {
            flex-direction: row !important;
            display: flex !important;
        }
        div[data-testid="column"] {
            width: 50% !important;
            flex: 1 1 auto !important;
            min-width: unset !important;
        }
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

# --- NAVEGACIÓN SUPERIOR (AHORA EN HORIZONTAL COMPACTO) ---
st.title("⚡ PIXEL THREAD")

# Contenedor en columnas para que los botones queden lado a lado en el móvil
col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("👤 CLIENTE"): 
        actualizar_url("Cliente", st.session_state.user)
with col_nav2:
    if st.button("🛠️ ADMIN"): 
        usuario_actual = st.session_state.user.strip()
        if usuario_actual in ADMINS_AUTORIZADOS:
            actualizar_url("Admin", st.session_state.user)
        else:
            st.error("❌ Sin permisos de administrador.")

st.markdown("<br>", unsafe_allow_html=True)

# =========================================================
# 1. PANEL DE CLIENTE
# =========================================================
if st.session_state.modo_vista == "Cliente":
    user_input = st.text_input("Ingresa tu Nombre o ID de Usuario:", value=st.session_state.user)
    if user_input != st.session_state.user:
        actualizar_url("Cliente", user_input)

    if not st.session_state.user.strip():
        st.info("👆 Ingresa tu ID de usuario arriba para ver tus pedidos.")
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

            col_c1, col_c2 = st.columns([0.2, 3.8])
            with col_c1:
                if logo_cliente_b64:
                    try:
                        st.image(base64.b64decode(logo_cliente_b64), width=50)
                    except Exception:
                        st.markdown("<h3>👤</h3>", unsafe_allow_html=True)
                else:
                    st.markdown("<h3>👤</h3>", unsafe_allow_html=True)
            with col_c2:
                st.subheader(f"Hola, {nombre_cliente}")

            if st.session_state.mensaje_exito:
                st.success(st.session_state.mensaje_exito)
                st.session_state.mensaje_exito = ""

            st.markdown("---")
            fv = st.session_state.form_version

            with st.expander("➕ Enviar Nuevo Pedido", expanded=st.session_state.expandir_nuevo_pedido):
                tipo_producto = st.radio("Tipo:", ["GORRA", "TELA", "VARIOS"], horizontal=True, key=f"prod_{fv}")
                ubicacion, estilo_frente = "N/A", "N/A"

                if tipo_producto == "GORRA":
                    ubicacion = st.radio("Ubicación:", ["FRENTE", "TRASERO", "LATERAL"], horizontal=True, key=f"ubi_{fv}")
                    if ubicacion == "FRENTE":
                        estilo_frente = st.radio("Estilo:", ["3D", "PLANO"], horizontal=True, key=f"est_{fv}")

                nombre_proyecto = st.text_input("Nombre del Proyecto", key=f"nom_{fv}")
                archivos_subidos = st.file_uploader("Archivos", type=["png", "jpg", "jpeg", "dst", "pes", "pdf", "emb"], accept_multiple_files=True, key=f"arch_{fv}")
                comentarios = st.text_area("Comentarios", key=f"com_{fv}")
                status_ph = st.empty()

                if st.button("🚀 ENVIAR PEDIDO", key=f"btn_env_{fv}"):
                    if not nombre_proyecto:
                        status_ph.warning("⚠️ Ingresa el nombre del proyecto.")
                    elif not archivos_subidos:
                        status_ph.error("❌ Adjunta al menos un archivo.")
                    else:
                        try:
                            status_ph.info("⏳ Enviando...")
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
                            st.session_state.mensaje_exito = "🎉 ¡Enviado con éxito!"
                            st.session_state.form_version += 1
                            st.session_state.expandir_nuevo_pedido = False
                            st.rerun()
                        except Exception as e:
                            status_ph.error(f"Error: {e}")

            st.markdown("---")
            st.subheader("📋 Mis Pedidos")

            todos = list(db.collection("pedidos_bordado").order_by("timestamp").stream())
            mis_pedidos = [p.to_dict() for p in todos if p.to_dict().get("cliente", "").strip().lower() == st.session_state.user.strip().lower()]

            if mis_pedidos:
                pedidos_activos = [p for p in mis_pedidos if p.get('estado') != "Completado"]
                
                if pedidos_activos:
                    for p in pedidos_activos:
                        with st.container():
                            # Organizar los datos clave horizontalmente dentro de la tarjeta
                            col_p1, col_p2 = st.columns([2, 1])
                            with col_p1:
                                st.markdown(f"**🧵 {p.get('nombre_proyecto')}**")
                                st.text(f"ID: {p.get('id')}")
                            with col_p2:
                                st.markdown(f"**Estado:** `{p.get('estado')}`")
                                st.text(f"{p.get('producto')} / {p.get('ubicacion')}")

                            archivos = p.get('archivos', [])
                            if archivos:
                                for idx_a, arch_item in enumerate(archivos):
                                    nombre_a = arch_item.get('nombre', 'archivo')
                                    try:
                                        st.download_button(f"📥 {nombre_a}", data=base64.b64decode(arch_item.get('data')), file_name=nombre_a, key=f"dl_mob_{p.get('id')}_{idx_a}")
                                    except Exception:
                                        pass
                            st.markdown("---")
                else:
                    st.info("No tienes pedidos activos.")
            else:
                st.info("No hay pedidos registrados.")

        except Exception as e:
            if "ResourceExhausted" in str(type(e).__name__) or "quota" in str(e).lower():
                st.error("⚠️ Límite de base de datos alcanzado temporalmente. Espera unos segundos.")
            else:
                st.error(f"Error: {e}")

# =========================================================
# 2. PANEL DE ADMINISTRADOR
# =========================================================
else:
    st.subheader("🛠️ Administración")

    try:
        docs = list(db.collection("pedidos_bordado").order_by("timestamp").stream())
        pedidos_activos = [(doc.id, doc.to_dict()) for doc in docs if doc.to_dict().get('estado') != "Completado"]

        if pedidos_activos:
            for doc_id, p in pedidos_activos:
                with st.container():
                    col_a1, col_a2 = st.columns([2, 1])
                    with col_a1:
                        st.markdown(f"**👤 {p.get('cliente')}**")
                        st.text(f"Proj: {p.get('nombre_proyecto')} | ID: {p.get('id')}")
                    with col_a2:
                        st.markdown(f"**{p.get('estado')}**")
                        if st.button("🗑️ Borrar", key=f"mob_del_{doc_id}"):
                            db.collection("pedidos_bordado").document(doc_id).delete()
                            st.rerun()
                    st.markdown("---")
        else:
            st.info("🎉 No hay pedidos pendientes.")

    except Exception as e:
        st.error(f"Error al cargar administración: {e}")
