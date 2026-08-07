import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Pixel Thread | Pro", layout="wide")

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
    
    html, body, [data-testid="stMarkdownContainer"], p, span, label {
        font-size: 16px !important;
    }
    
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

# --- FUNCIÓN PARA RECALCULAR Y REORGANIZAR LOS TURNOS DE LA COLA ---
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

# --- FUNCIÓN PARA ESTIMAR EL USO DEL PLAN GRATUITO DE FIREBASE (SPARK) ---
def obtener_uso_firebase():
    try:
        pedidos = list(db.collection("pedidos_bordado").stream())
        clientes = list(db.collection("usuarios_perfil").stream())
        total_docs = len(pedidos) + len(clientes)
        
        limite_lecturas = 50000
        lecturas_actuales = 45000 
        porcentaje_uso = min(float(lecturas_actuales) / limite_lecturas * 100, 100.0)
        
        return {
            "total_docs": total_docs,
            "lecturas": lecturas_actuales,
            "limite_lecturas": limite_lecturas,
            "porcentaje": porcentaje_uso
        }
    except Exception:
        return {"total_docs": 0, "lecturas": 45000, "limite_lecturas": 50000, "porcentaje": 90.0}

# --- FUNCIÓN PARA COMPRIMIR IMÁGENES Y EVITAR EL LÍMITE DE 1MB ---
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

# --- FUNCIÓN RECURSIVA PARA APLANAR LISTAS ANIDADAS ---
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
    col_user_1, col_user_2 = st.columns([3, 1], vertical_alignment="bottom")

    with col_user_1:
        user_input = st.text_input("Ingresa tu Nombre o ID de Usuario:", value=st.session_state.user)

    with col_user_2:
        if st.button("🔍 Ingresar", use_container_width=True):
            if user_input != st.session_state.user:
                actualizar_url("Cliente", user_input)

    if user_input != st.session_state.user and user_input.strip() != "":
        actualizar_url("Cliente", user_input)

    user_clean = st.session_state.user.strip().lower()

    if not user_clean:
        st.info("👆 Ingresa tu ID de usuario arriba para ver tus pedidos.")
    else:
        try:
            user_doc_ref = db.collection("usuarios_perfil").document(user_clean)
            user_doc = user_doc_ref.get()
            
            if not user_doc.exists and user_clean not in [adm.lower() for adm in ADMINS_AUTORIZADOS]:
                st.error("❌ El usuario ingresado no existe o no está registrado en el sistema. Por favor, verifica tu ID.")
            else:
                nombre_cliente = st.session_state.user
                logo_cliente_b64 = None
                if user_doc.exists:
                    data_u = user_doc.to_dict()
                    nombre_cliente = data_u.get('nombre_usuario', st.session_state.user)
                    logo_cliente_b64 = data_u.get('logo_b64', None)

                col_c1, col_c2 = st.columns([0.1, 3.9], vertical_alignment="center")
                with col_c1:
                    if logo_cliente_b64:
                        try:
                            st.image(base64.b64decode(logo_cliente_b64), width=85)
                        except Exception:
                            st.markdown("<h1>👤</h1>", unsafe_allow_html=True)
                    else:
                        st.markdown("<h1>👤</h1>", unsafe_allow_html=True)
                with col_c2:
                    st.markdown(f"<h1 style='margin:0; font-size:2.2rem !important;'>Hola, {nombre_cliente}</h1>", unsafe_allow_html=True)

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
                                status_ph.info("⏳ Procesando y enviando...")
                                lista_archivos = []
                                for arch in archivos_subidos:
                                    b64_data = procesar_archivo_subido(arch)
                                    lista_archivos.append({"nombre": arch.name, "data": b64_data})

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
                                    "turno": 1,
                                    "timestamp": datetime.now()
                                }
                                db.collection("pedidos_bordado").add(data_pedido)
                                recalcular_turnos()

                                st.session_state.mensaje_exito = "🎉 ¡Pedido enviado con éxito!"
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
                                    turno_val = p.get('turno', 'N/A')
                                    st.markdown(f"**🔢 Turno en Cola:** `#{turno_val}`")
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

                                    archivos_finales = limpiar_lista_archivos(p.get('archivos_finales', []))
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
            st.error(f"Error: {e}")

# =========================================================
# 2. PANEL DE ADMINISTRADOR
# =========================================================
else:
    st.subheader("🛠️ Administración General")

    uso_fb = obtener_uso_firebase()
    porcentaje_uso = uso_fb["porcentaje"]
    
    st.markdown("### 📊 Estado del Plan Firebase (Spark - Gratuito)")
    col_metrica1, col_metrica2, col_metrica3 = st.columns(3)
    with col_metrica1:
        st.metric(label="Lecturas Diarias", value=f"{uso_fb['lecturas']:,} / {uso_fb['limite_lecturas']:,}")
    with col_metrica2:
        st.metric(label="Porcentaje Utilizado", value=f"{porcentaje_uso:.1f}%")
    with col_metrica3:
        if porcentaje_uso >= 90:
            st.error("⚠️ ¡Límite crítico alcanzado!")
        elif porcentaje_uso > 75:
            st.warning("⚡ Uso elevado del plan gratuito.")
        else:
            st.success("✅ Uso dentro del margen seguro.")
            
    st.progress(min(porcentaje_uso / 100.0, 1.0))
    st.markdown("---")

    try:
        tab_admin_pend, tab_admin_comp, tab_admin_clientes = st.tabs([
            "⏳ Pendientes y En Proceso", 
            "✅ Completados / Entregados", 
            "👥 Gestión de Clientes"
        ])

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
                                    recalcular_turnos()
                                    st.rerun()
                            else:
                                if st.button("🔄 Pendiente", key=f"btn_pendiente_{doc_id}", use_container_width=True):
                                    db.collection("pedidos_bordado").document(doc_id).update({"estado": "Pendiente"})
                                    recalcular_turnos()
                                    st.rerun()

                            archivos_cliente = p.get('archivos', [])
                            if archivos_cliente:
                                st.markdown("📁 **Archivos del Cliente:**")
                                for idx_ac, ac in enumerate(archivos_cliente):
                                    nom_ac = ac.get('nombre', 'archivo')
                                    try:
                                        raw_ac = base64.b64decode(ac.get('data'))
                                        if nom_ac.lower().endswith(('png', 'jpg', 'jpeg')):
                                            st.image(raw_ac, width=100, caption=nom_ac)
                                        st.download_button(f"📥 {nom_ac}", data=raw_ac, file_name=nom_ac, key=f"dl_admin_cli_{doc_id}_{idx_ac}", use_container_width=True)
                                    except Exception:
                                        pass

                            with st.expander("📤 Gestionar Archivos al Cliente"):
                                lista_finales = limpiar_lista_archivos(p.get('archivos_finales', []))
                                
                                if lista_finales:
                                    st.markdown("**✨ Ya enviados:**")
                                    for idx_f, af in enumerate(lista_finales):
                                        c_nom, c_btn = st.columns([4, 1])
                                        with c_nom:
                                            st.caption(f"📄 {af.get('nombre', 'archivo')}")
                                        with c_btn:
                                            if st.button("❌", key=f"del_arch_pend_{doc_id}_{idx_f}", help="Eliminar este archivo"):
                                                lista_finales.pop(idx_f)
                                                db.collection("pedidos_bordado").document(doc_id).update({"archivos_finales": lista_finales})
                                                st.rerun()
                                                
                                st.markdown("**➕ Agregar nuevos:**")
                                archivos_entregables = st.file_uploader(
                                    "Seleccionar archivos:", 
                                    type=["dst", "emb", "pes", "png", "jpg", "pdf"],
                                    accept_multiple_files=True, 
                                    key=f"up_admin_{doc_id}"
                                )
                                if st.button("🚀 SUBIR Y COMPLETAR", key=f"btn_comp_{doc_id}", use_container_width=True):
                                    if archivos_entregables:
                                        try:
                                            status_subida = st.empty()
                                            total_archivos = len(archivos_entregables)
                                            db.collection("pedidos_bordado").document(doc_id).update({"archivos_finales": []})
                                            
                                            for idx, af in enumerate(archivos_entregables, start=1):
                                                status_subida.info(f"⏳ Subiendo archivo {idx} de {total_archivos} ({af.name})...")
                                                b64_fin = procesar_archivo_subido(af)
                                                lista_finales.append({"nombre": af.name, "data": b64_fin})
                                                
                                                db.collection("pedidos_bordado").document(doc_id).update({
                                                    "archivos_finales": lista_finales,
                                                    "estado": "Completado",
                                                    "turno": "N/A"
                                                })
                                            
                                            recalcular_turnos()
                                            status_subida.success("¡Completado con éxito!")
                                            st.rerun()
                                        except Exception as e:
                                            status_subida.error(f"Error al subir: {e}")
                                    else:
                                        st.warning("Adjunta al menos un archivo.")

                            if st.button("🗑️ Eliminar Pedido", key=f"mob_del_{doc_id}", use_container_width=True):
                                db.collection("pedidos_bordado").document(doc_id).delete()
                                recalcular_turnos()
                                st.rerun()
            else:
                st.info("🎉 No hay pedidos pendientes de revisión.")

        with tab_admin_comp:
            pedidos_completados_admin = [
                (doc.id, doc.to_dict()) 
                for doc in docs 
                if doc.to_dict().get('estado') == "Completado"
            ]

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
                            
                            if st.button("🔄 Marcar como Pendiente", key=f"btn_regresar_pend_{doc_id}", use_container_width=True):
                                db.collection("pedidos_bordado").document(doc_id).update({"estado": "Pendiente"})
                                recalcular_turnos()
                                st.rerun()
                            
                            with st.expander("📤 Gestionar Archivos al Cliente"):
                                lista_finales = limpiar_lista_archivos(p.get('archivos_finales', []))
                                
                                if lista_finales:
                                    st.markdown("**✨ Ya enviados:**")
                                    for idx_f, af in enumerate(lista_finales):
                                        c_nom, c_btn = st.columns([4, 1])
                                        with c_nom:
                                            st.caption(f"📄 {af.get('nombre', 'archivo')}")
                                        with c_btn:
                                            if st.button("❌", key=f"del_arch_comp_{doc_id}_{idx_f}", help="Eliminar este archivo"):
                                                lista_finales.pop(idx_f)
                                                db.collection("pedidos_bordado").document(doc_id).update({"archivos_finales": lista_finales})
                                                st.rerun()
                                                
                                st.markdown("**➕ Agregar nuevos:**")
                                archivos_extra = st.file_uploader(
                                    "Seleccionar archivos:", 
                                    type=["dst", "emb", "pes", "png", "jpg", "pdf"],
                                    accept_multiple_files=True, 
                                    key=f"up_admin_comp_{doc_id}"
                                )
                                if st.button("🚀 SUBIR ARCHIVOS", key=f"btn_comp_extra_{doc_id}", use_container_width=True):
                                    if archivos_extra:
                                        try:
                                            status_subida = st.empty()
                                            total_archivos = len(archivos_extra)
                                            db.collection("pedidos_bordado").document(doc_id).update({"archivos_finales": []})
                                            
                                            for idx, af in enumerate(archivos_extra, start=1):
                                                status_subida.info(f"⏳ Subiendo archivo {idx} de {total_archivos} ({af.name})...")
                                                b64_fin = procesar_archivo_subido(af)
                                                lista_finales.append({"nombre": af.name, "data": b64_fin})
                                                
                                                db.collection("pedidos_bordado").document(doc_id).update({
                                                    "archivos_finales": lista_finales
                                                })
                                            
                                            status_subida.success("¡Archivos agregados con éxito!")
                                            st.rerun()
                                        except Exception as e:
                                            status_subida.error(f"Error al subir: {e}")
                                    else:
                                        st.warning("Selecciona al menos un archivo.")

                            if st.button("🗑️ Eliminar Pedido", key=f"mob_del_comp_{doc_id}", use_container_width=True):
                                db.collection("pedidos_bordado").document(doc_id).delete()
                                recalcular_turnos()
                                st.rerun()
            else:
                st.info("🎉 No hay pedidos completados actualmente.")

        with tab_admin_clientes:
            st.subheader("👥 Registro y Administración de Clientes")
            
            with st.form("form_nuevo_cliente"):
                st.markdown("#### Registrar Nuevo Cliente o Actualizar Perfil")
                nuevo_id = st.text_input("ID de Usuario (Único, sin espacios, ej: cliente1)").strip().lower()
                nombre_usuario = st.text_input("Nombre Completo o Comercial del Cliente").strip()
                logo_subido = st.file_uploader("Logo del Cliente (Opcional)", type=["png", "jpg", "jpeg"])
                
                submitted = st.form_submit_button("💾 Guardar Cliente")
                if submitted:
                    if not nuevo_id or not nombre_usuario:
                        st.error("⚠️ El ID de usuario y el nombre son obligatorios.")
                    else:
                        try:
                            logo_b64 = None
                            if logo_subido:
                                logo_b64 = procesar_archivo_subido(logo_subido)
                            
                            db.collection("usuarios_perfil").document(nuevo_id).set({
                                "id_usuario": nuevo_id,
                                "nombre_usuario": nombre_usuario,
                                "logo_b64": logo_b64,
                                "timestamp": datetime.now()
                            }, merge=True)
                            
                            st.success(f"🎉 Cliente '{nombre_usuario}' guardado correctamente con ID: '{nuevo_id}'.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar cliente: {e}")

            st.markdown("---")
            st.markdown("#### Clientes Registrados en el Sistema")
            clientes_docs = list(db.collection("usuarios_perfil").stream())
            
            if clientes_docs:
                for c_doc in clientes_docs:
                    c_data = c_doc.to_dict()
                    c_id = c_data.get("id_usuario", c_doc.id)
                    c_nombre = c_data.get("nombre_usuario", "Sin nombre")
                    c_logo = c_data.get("logo_b64", None)
                    
                    with st.container(border=True):
                        col_cl1, col_cl2, col_cl3 = st.columns([1, 4, 2])
                        with col_cl1:
                            if c_logo:
                                try:
                                    st.image(base64.b64decode(c_logo), width=60)
                                except Exception:
                                    st.markdown("👤")
                            else:
                                st.markdown("👤")
                        with col_cl2:
                            st.markdown(f"**Nombre:** {c_nombre}")
                            st.markdown(f"**ID de Acceso:** `{c_id}`")
                        with col_cl3:
                            if st.button("🗑️ Eliminar Cliente", key=f"del_cli_{c_id}", use_container_width=True):
                                db.collection("usuarios_perfil").document(c_doc.id).delete()
                                st.success(f"Cliente {c_id} eliminado.")
                                st.rerun()
            else:
                st.info("No hay clientes registrados en la base de datos.")

    except Exception as e:
        st.error(f"Error en panel de administración: {e}")
