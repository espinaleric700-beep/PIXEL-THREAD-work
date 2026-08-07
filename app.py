import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import base64
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Pixel Thread | Pro", layout="wide")
st_autorefresh(interval=10000, limit=1000, key="auto_refrescar")

# --- CSS LIMPIO, SIN LÍNEAS ANIDADAS, LETRAS MÁS GRANDES Y FONDO ORIGINAL ---
st.markdown("""
<style>
    :root {
        --primary: #00ffcc;
    }
    .stApp {
        background: radial-gradient(circle at 50% 50%, #1a0033 0%, #050505 100%);
        background-attachment: fixed;
        color: #ffffff;
    }
    .block-container {
        max-width: 100% !important;
        padding-left: 2rem;
        padding-right: 2rem;
        padding-top: 1.5rem;
    }
    
    /* Aumentar tamaño de letra general y legibilidad */
    html, body, [data-testid="stMarkdownContainer"], p, span, label {
        font-size: 16px !important;
    }
    
    /* Limpiar bordes innecesarios, dejando solo un estilo limpio */
    div[data-testid="stExpander"] {
        background: rgba(15, 15, 25, 0.7) !important;
        border: 1px solid rgba(0, 255, 204, 0.3) !important;
        border-radius: 10px !important;
        padding: 8px;
    }
    
    div.stButton > button {
        background: transparent !important;
        color: var(--primary) !important;
        border: 1px solid var(--primary) !important;
        border-radius: 6px !important;
        transition: all 0.3s ease !important;
        text-transform: uppercase;
        font-weight: bold;
        font-size: 14px !important;
        padding: 6px 12px;
    }
    div.stButton > button:hover {
        background: var(--primary) !important;
        color: black !important;
        box-shadow: 0 0 15px var(--primary) !important;
        transform: translateY(-2px);
    }
    
    h1 { color: var(--primary) !important; font-size: 2.5rem !important; letter-spacing: 2px; }
    h2 { color: var(--primary) !important; font-size: 1.8rem !important; }
    h3 { color: var(--primary) !important; font-size: 1.3rem !important; }

    /* --- CÍRCULOS DE ESTADO --- */
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

# --- FUNCIÓN AUXILIAR PARA RENDERIZAR ESTADO CON CÍRCULO ---
def render_estado_badge(estado):
    if estado == "Pendiente":
        st.markdown("**Estado:** Pendiente <span class='dot-red'></span>", unsafe_allow_html=True)
    elif estado == "En Proceso":
        st.markdown("**Estado:** En Proceso <span class='dot-green'></span>", unsafe_allow_html=True)
    else:
        st.markdown("**Estado:** Completado <span class='dot-blue'></span>", unsafe_allow_html=True)

# --- ENCABEZADO SUPERIOR CON MENÚ MINIMIZADO ---
col_head1, col_head2 = st.columns([3, 1])

with col_head1:
    st.title("⚡ PIXEL THREAD")

with col_head2:
    with st.popover("⚙️ Menú"):
        st.markdown("### Navegación")
        if st.button("👤 Panel Cliente", use_container_width=True): 
            actualizar_url("Cliente", st.session_state.user)
        if st.button("🛠️ Panel Admin", use_container_width=True): 
            usuario_actual = st.session_state.user.strip()
            if usuario_actual in ADMINS_AUTORIZADOS:
                actualizar_url("Admin", st.session_state.user)
            else:
                st.error("❌ Sin permisos.")

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
                        st.image(base64.b64decode(logo_cliente_b64), width=45)
                    except Exception:
                        st.markdown("👤", unsafe_allow_html=True)
                else:
                    st.markdown("👤", unsafe_allow_html=True)
            with col_c2:
                st.subheader(f"Hola, {nombre_cliente}")

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
                        estilo_frente = st.radio("Estilo:", ["3D (Relieve)", "PLANO"], horizontal=True, key=f"est_{fv}")

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
            
            tab_pendientes, tab_completados = st.tabs(["⏳ Pedidos Pendientes", "✅ Pedidos Completados"])

            todos = list(db.collection("pedidos_bordado").order_by("timestamp").stream())
            mis_pedidos = [p.to_dict() for p in todos if p.to_dict().get("cliente", "").strip().lower() == st.session_state.user.strip().lower()]

            with tab_pendientes:
                st.subheader("📋 Pedidos en Proceso")
                pedidos_activos = [p for p in mis_pedidos if p.get('estado') != "Completado"]
                
                if pedidos_activos:
                    cols = st.columns(4)
                    for i, p in enumerate(pedidos_activos):
                        with cols[i % 4]:
                            with st.container(border=True):
                                st.markdown(f"**🧵 Proyecto:** {p.get('nombre_proyecto', 'N/A')}")
                                st.markdown(f"**📦 Producto:** {p.get('producto', 'N/A')}")
                                st.markdown(f"**📍 Ubicación:** {p.get('ubicacion', 'N/A')}")
                                st.markdown(f"**🎨 Estilo:** {p.get('estilo', 'N/A')}")
                                render_estado_badge(p.get('estado', 'Pendiente'))
                                if p.get('comentarios'):
                                    st.caption(f"📝 Nota: {p.get('comentarios')}")

                                archivos = p.get('archivos', [])
                                if archivos:
                                    st.markdown("📁 **Archivos:**")
                                    for idx_a, arch_item in enumerate(archivos):
                                        nombre_a = arch_item.get('nombre', 'archivo')
                                        try:
                                            raw_bytes = base64.b64decode(arch_item.get('data'))
                                            if nombre_a.lower().endswith(('png', 'jpg', 'jpeg')):
                                                st.image(raw_bytes, width=120, caption=nombre_a)
                                            st.download_button(f"📥 {nombre_a}", data=raw_bytes, file_name=nombre_a, key=f"dl_cli_{p.get('id')}_{idx_a}")
                                        except Exception:
                                            pass
                else:
                    st.info("No tienes pedidos pendientes activos.")

            with tab_completados:
                st.subheader("🎉 Historial de Pedidos Listos")
                pedidos_terminados = [p for p in mis_pedidos if p.get('estado') == "Completado"]

                if pedidos_terminados:
                    cols = st.columns(4)
                    for i, p in enumerate(pedidos_terminados):
                        with cols[i % 4]:
                            with st.container(border=True):
                                st.markdown(f"**🧵 Proyecto:** {p.get('nombre_proyecto', 'N/A')}")
                                st.markdown(f"**📦 Producto:** {p.get('producto', 'N/A')}")
                                st.markdown(f"**📍 Ubicación:** {p.get('ubicacion', 'N/A')}")
                                st.markdown(f"**🎨 Estilo:** {p.get('estilo', 'N/A')}")
                                render_estado_badge("Completado")

                                archivos_finales = p.get('archivos_finales', [])
                                if archivos_finales:
                                    st.markdown("✨ **Archivos Listos:**")
                                    for idx_f, af in enumerate(archivos_finales):
                                        nom_f = af.get('nombre', 'resultado')
                                        try:
                                            raw_f_bytes = base64.b64decode(af.get('data'))
                                            if nom_f.lower().endswith(('png', 'jpg', 'jpeg')):
                                                st.image(raw_f_bytes, width=120, caption=nom_f)
                                            st.download_button(f"📥 {nom_f}", data=raw_f_bytes, file_name=nom_f, key=f"dl_fin_{p.get('id')}_{idx_f}")
                                        except Exception:
                                            pass
                else:
                    st.info("Aún no tienes pedidos completados.")

        except Exception as e:
            if "ResourceExhausted" in str(type(e).__name__) or "quota" in str(e).lower():
                st.error("⚠️ Límite de base de datos alcanzado temporalmente. Espera unos segundos.")
            else:
                st.error(f"Error: {e}")

# =========================================================
# 2. PANEL DE ADMINISTRADOR
# =========================================================
else:
    st.subheader("🛠️ Administración General")

    try:
        tab_admin_pend, tab_admin_comp, tab_admin_clientes = st.tabs([
            "⏳ Pendientes y En Proceso", 
            "✅ Completados / Entregados", 
            "👥 Gestión de Clientes"
        ])

        docs = list(db.collection("pedidos_bordado").order_by("timestamp").stream())

        with tab_admin_pend:
            pedidos_activos = [(doc.id, doc.to_dict()) for doc in docs if doc.to_dict().get('estado') != "Completado"]

            if pedidos_activos:
                cols = st.columns(4)
                for i, (doc_id, p) in enumerate(pedidos_activos):
                    with cols[i % 4]:
                        with st.container(border=True):
                            st.markdown(f"**👤 Cliente:** `{p.get('cliente')}`")
                            st.markdown(f"**🧵 Proyecto:** `{p.get('nombre_proyecto', 'N/A')}`")
                            st.markdown(f"**📦 Producto:** {p.get('producto', 'N/A')}")
                            st.markdown(f"**📍 Ubicación:** {p.get('ubicacion', 'N/A')}")
                            st.markdown(f"**🎨 Estilo:** {p.get('estilo', 'N/A')}")
                            
                            estado_actual = p.get('estado', 'Pendiente')
                            render_estado_badge(estado_actual)
                            
                            if p.get('comentarios'):
                                st.caption(f"📝 Comentarios: {p.get('comentarios')}")
                            
                            if estado_actual == "Pendiente":
                                if st.button("🔄 En Proceso", key=f"btn_proceso_{doc_id}", use_container_width=True):
                                    db.collection("pedidos_bordado").document(doc_id).update({"estado": "En Proceso"})
                                    st.rerun()
                            else:
                                if st.button("🔄 Pendiente", key=f"btn_pendiente_{doc_id}", use_container_width=True):
                                    db.collection("pedidos_bordado").document(doc_id).update({"estado": "Pendiente"})
                                    st.rerun()

                            archivos_cliente = p.get('archivos', [])
                            if archivos_cliente:
                                st.markdown("📁 **Archivos:**")
                                for idx_ac, ac in enumerate(archivos_cliente):
                                    nom_ac = ac.get('nombre', 'archivo')
                                    try:
                                        raw_ac = base64.b64decode(ac.get('data'))
                                        if nom_ac.lower().endswith(('png', 'jpg', 'jpeg')):
                                            st.image(raw_ac, width=100, caption=nom_ac)
                                        st.download_button(f"📥 {nom_ac}", data=raw_ac, file_name=nom_ac, key=f"dl_admin_cli_{doc_id}_{idx_ac}", use_container_width=True)
                                    except Exception:
                                        pass

                            with st.expander("📤 Subir Resultado"):
                                archivos_entregables = st.file_uploader(
                                    "Archivos finales:", 
                                    type=["dst", "emb", "pes", "png", "jpg", "pdf"],
                                    accept_multiple_files=True, 
                                    key=f"up_admin_{doc_id}"
                                )
                                if st.button("🚀 COMPLETAR", key=f"btn_comp_{doc_id}", use_container_width=True):
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
                                        st.success("¡Completado!")
                                        st.rerun()
                                    else:
                                        st.warning("Adjunta al menos un archivo.")

                            if st.button("🗑️ Eliminar", key=f"mob_del_{doc_id}", use_container_width=True):
                                db.collection("pedidos_bordado").document(doc_id).delete()
                                st.rerun()
            else:
                st.info("🎉 No hay pedidos pendientes de revisión.")

        with tab_admin_comp:
            pedidos_completados_admin = [(doc.id, doc.to_dict()) for doc in docs if doc.to_dict().get('estado') == "Completado"]

            if pedidos_completados_admin:
                cols = st.columns(4)
                for i, (doc_id, p) in enumerate(pedidos_completados_admin):
                    with cols[i % 4]:
                        with st.container(border=True):
                            st.markdown(f"**👤 {p.get('cliente')}**")
                            st.markdown(f"**🧵 {p.get('nombre_proyecto', 'N/A')}**")
                            st.markdown(f"**📦 Producto:** {p.get('producto', 'N/A')}")
                            st.markdown(f"**📍 Ubicación:** {p.get('ubicacion', 'N/A')}")
                            st.markdown(f"**🎨 Estilo:** {p.get('estilo', 'N/A')}")
                            render_estado_badge("Completado")
                            
                            if st.button("🗑️ Eliminar Historial", key=f"admin_del_comp_{doc_id}", use_container_width=True):
                                db.collection("pedidos_bordado").document(doc_id).delete()
                                st.rerun()
            else:
                st.info("No hay pedidos completados en el historial.")

        with tab_admin_clientes:
            st.subheader("👥 Registro y Control de Clientes")
            
            with st.expander("➕ Agregar o Modificar Cliente"):
                with st.form("form_cliente"):
                    c_id = st.text_input("ID o Usuario del Cliente (ej. juan123):").strip().lower()
                    c_nombre = st.text_input("Nombre Completo / Nombre Comercial:").strip()
                    c_logo = st.file_uploader("Logotipo del Cliente (Opcional)", type=["png", "jpg", "jpeg"])
                    
                    guardar_cliente = st.form_submit_button("💾 Guardar / Actualizar Cliente")
                    
                    if guardar_cliente:
                        if not c_id:
                            st.warning("⚠️ Debes ingresar un ID o nombre de usuario.")
                        else:
                            try:
                                doc_ref = db.collection("usuarios_perfil").document(c_id)
                                data_cliente = {
                                    "id_usuario": c_id,
                                    "nombre_usuario": c_nombre if c_nombre else c_id
                                }
                                if c_logo:
                                    data_cliente["logo_b64"] = base64.b64encode(c_logo.getvalue()).decode("utf-8")
                                
                                doc_ref.set(data_cliente, merge=True)
                                st.success(f"✅ Cliente '{c_id}' guardado correctamente.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al guardar cliente: {e}")

            st.markdown("---")
            st.markdown("### 📋 Lista de Clientes Registrados")
            
            try:
                clientes_docs = list(db.collection("usuarios_perfil").stream())
                if clientes_docs:
                    cols_cli = st.columns(4)
                    for i, c_doc in enumerate(clientes_docs):
                        c_data = c_doc.to_dict()
                        c_key = c_doc.id
                        
                        with cols_cli[i % 4]:
                            with st.container(border=True):
                                logo_b64 = c_data.get("logo_b64")
                                if logo_b64:
                                    try:
                                        st.image(base64.b64decode(logo_b64), width=50)
                                    except:
                                        st.markdown("👤", unsafe_allow_html=True)
                                else:
                                    st.markdown("👤", unsafe_allow_html=True)
                                
                                st.markdown(f"**ID:** `{c_key}`")
                                st.markdown(f"**Nombre:** {c_data.get('nombre_usuario', 'N/A')}")
                                
                                if st.button("🗑️ Eliminar", key=f"del_cli_{c_key}", use_container_width=True):
                                    db.collection("usuarios_perfil").document(c_key).delete()
                                    st.success(f"Cliente {c_key} eliminado.")
                                    st.rerun()
                else:
                    st.info("No hay clientes registrados en la base de datos.")
            except Exception as e:
                st.error(f"Error al listar clientes: {e}")

    except Exception as e:
        st.error(f"Error al cargar administración: {e}")
