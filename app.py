import streamlit as st
from PIL import Image
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import json
import os
import io
import base64

st.set_page_config(page_title="Pixel Thread - Portal Profesional", layout="centered")

# --- CONVERTIR LOGO A BASE64 PARA EL FONDO ---
logo_path = "PIXEL THREAD W_Mesa de trabajo 1_2.jpg"
logo_base64 = ""
if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode("utf-8")

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown(f"""
    <style>
    .stApp {{
        background: linear-gradient(135deg, rgba(10, 15, 29, 0.93) 0%, rgba(17, 24, 39, 0.93) 50%, rgba(31, 17, 40, 0.93) 100%);
        color: #e2e8f0;
    }}
    
    .stApp::before {{
        content: "";
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 60vw;
        height: 60vw;
        max-width: 650px;
        max-height: 650px;
        background-image: url("data:image/jpeg;base64,{logo_base64}");
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
        opacity: 0.08;
        z-index: 0;
        pointer-events: none;
    }}

    div[data-testid="stExpander"], div.stContainer, div[data-testid="stVerticalBlock"] > div > div.element-container {{
        position: relative;
        z-index: 1;
    }}

    div[data-testid="stMetric"] {{
        background: rgba(17, 24, 39, 0.85);
        border: 1px solid rgba(0, 255, 204, 0.2);
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 0 15px rgba(0, 255, 204, 0.05);
    }}
    div[data-testid="stMetric"] label {{
        color: #94a3b8 !important;
    }}
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
        color: #00ffcc !important;
        text-shadow: 0 0 10px rgba(0, 255, 204, 0.4);
    }}

    .stButton>button {{
        background: linear-gradient(90deg, #00ffcc 0%, #0077ff 100%);
        color: #0a0f1d;
        font-weight: bold;
        border: none;
        border-radius: 8px;
        box-shadow: 0 0 10px rgba(0, 255, 204, 0.3);
        transition: all 0.3s ease;
    }}
    .stButton>button:hover {{
        box-shadow: 0 0 20px rgba(0, 255, 204, 0.6);
        transform: translateY(-2px);
    }}

    section[data-testid="stSidebar"] {{
        background-color: #070a14;
        border-right: 1px solid rgba(0, 255, 204, 0.1);
    }}
    </style>
""", unsafe_allow_html=True)

# --- ARCHIVO DE PERSISTENCIA LOCAL ---
DB_FILE = "datos_pixel_thread.json"

def cargar_datos():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def guardar_datos():
    try:
        logos_limpios = []
        for l in st.session_state.get("logos", []):
            logo_copy = {}
            for k, v in l.items():
                if k in ["imagen_obj", "archivo_bordado_bytes", "archivos_multiples"]:
                    if k == "archivos_multiples" and isinstance(v, list):
                        logo_copy[k] = [{"nombre": arch.get("nombre")} for arch in v if isinstance(arch, dict)]
                    continue
                logo_copy[k] = v
            logos_limpios.append(logo_copy)

        clientes_limpios = {}
        for cli, info in st.session_state.get("clientes_registrados", {}).items():
            if isinstance(info, dict):
                clientes_limpios[cli] = {
                    "divisa": info.get("divisa", "Dólares (USD - $)"),
                    "avatar_nombre": info.get("avatar_nombre", None)
                }
            else:
                clientes_limpios[cli] = {"divisa": info, "avatar_bytes": None, "avatar_nombre": None}

        datos = {
            "clientes_registrados": clientes_limpios,
            "logos": logos_limpios
        }
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error al guardar datos: {e}")

# --- ACTUALIZACIÓN AUTOMÁTICA CADA 2 SEGUNDOS ---
st_autorefresh(interval=2000, limit=None, key="autorefresh_global")

# --- CARGAR DATOS PERSISTENTES AL INICIAR LA SESIÓN ---
datos_guardados = cargar_datos()

if "clientes_registrados" not in st.session_state:
    if datos_guardados and "clientes_registrados" in datos_guardados:
        st.session_state.clientes_registrados = datos_guardados["clientes_registrados"]
    else:
        st.session_state.clientes_registrados = {
            "Cliente A": {"divisa": "Dólares (USD - $)", "avatar_bytes": None, "avatar_nombre": None},
            "Cliente B": {"divisa": "Pesos Dominicanos (DOP - RD$)", "avatar_bytes": None, "avatar_nombre": None}
        }
else:
    for cli, val in list(st.session_state.clientes_registrados.items()):
        if not isinstance(val, dict):
            st.session_state.clientes_registrados[cli] = {"divisa": val, "avatar_bytes": None, "avatar_nombre": None}

if "logos" not in st.session_state:
    if datos_guardados and "logos" in datos_guardados:
        st.session_state.logos = datos_guardados["logos"]
    else:
        st.session_state.logos = [
            {"id": 1, "cliente": "Cliente A", "nombre": "Logo León Dorado", "precio_usd": 5.0, "precio_dop": 300.0, "estado": "Pendiente", "pago": "Pendiente", "tipo": "Tela", "ubicacion_gorra": "N/A", "detalle_gorra": "N/A", "comentario": "Urgente", "archivo": "leon.png"},
            {"id": 2, "cliente": "Cliente A", "nombre": "Logo Cafetería", "precio_usd": 5.0, "precio_dop": 300.0, "estado": "En Revisión", "pago": "Pendiente", "tipo": "Gorra", "ubicacion_gorra": "Frontal", "detalle_gorra": "3D (Puff)", "comentario": "Centrado", "archivo": "cafe.png"},
            {"id": 3, "cliente": "Cliente B", "nombre": "Escudo Deportivo", "precio_usd": 5.0, "precio_dop": 300.0, "estado": "Terminado", "pago": "Pagado", "tipo": "Tela", "ubicacion_gorra": "N/A", "detalle_gorra": "N/A", "comentario": "Ninguno", "archivo": "escudo.png"},
        ]

if "recibos_pago" not in st.session_state:
    st.session_state.recibos_pago = {}

if "form_enviado" not in st.session_state:
    st.session_state.form_enviado = False

if "sesion_activa" not in st.session_state:
    st.session_state.sesion_activa = None

# --- MENÚ DE NAVEGACIÓN Y AUTENTICACIÓN LATERAL ---
st.sidebar.title("Pixel Thread 🧵")

if st.session_state.sesion_activa is None:
    st.sidebar.subheader("🔒 Iniciar Sesión")
    tipo_ingreso = st.sidebar.radio("Tipo de Acceso", ["Cliente", "Panel Administrador"])
    
    if tipo_ingreso == "Panel Administrador":
        pin_ingresado = st.sidebar.text_input("Contraseña Administrador", type="password")
        if st.sidebar.button("Entrar como Admin"):
            if pin_ingresado == "2580PIXEL":
                st.session_state.sesion_activa = "admin"
                st.success("¡Acceso concedido!")
                st.rerun()
            else:
                st.error("Contraseña incorrecta. Usa: 2580PIXEL")
    else:
        usuario_ingresado = st.sidebar.text_input("Ingresa tu Nombre de Usuario")
        if st.sidebar.button("Entrar a mi Portal"):
            if usuario_ingresado in st.session_state.clientes_registrados:
                st.session_state.sesion_activa = usuario_ingresado
                st.success(f"¡Bienvenido, {usuario_ingresado}!")
                st.rerun()
            else:
                st.error("Usuario no encontrado o no autorizado. Solicítalo al administrador.")
    
    st.sidebar.divider()
    st.sidebar.info("💡 Tarifa oficial: $5.00 USD / $300.00 DOP por logo digitalizado.")
    st.stop()

else:
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state.sesion_activa = None
        st.rerun()
    
    st.sidebar.divider()
    if st.session_state.sesion_activa == "admin":
        st.sidebar.success("🔑 Sesión Activa: Administrador")
    else:
        st.sidebar.success(f"👤 Sesión Activa: {st.session_state.sesion_activa}")
    
    st.sidebar.divider()
    st.sidebar.info("💡 Tarifa oficial: $5.00 USD / $300.00 DOP por logo digitalizado.")
    st.sidebar.caption("🔄 Actualización automática activa (cada 2 seg)")

# ==========================================
# 1. VISTA ADMINISTRADOR
# ==========================================
if st.session_state.sesion_activa == "admin":
    st.title("🎛️ Panel de Control - Pixel Thread")
    st.write("Administra el flujo de trabajo industrial, el estado de pagos y la entrega de archivos de bordado (.DST/.EMB/.PDF).")

    total_usd = sum(l.get('precio_usd', 5.0) for l in st.session_state.logos if l.get('estado', 'Pendiente') == "Terminado" and l.get('estado') != "Archivado/Pagado")
    total_dop = sum(l.get('precio_dop', 300.0) for l in st.session_state.logos if l.get('estado', 'Pendiente') == "Terminado" and l.get('estado') != "Archivado/Pagado")
    
    col1, col2 = st.columns(2)
    col1.metric("Total Acumulado (Semana)", f"${total_usd:.2f} USD")
    col2.metric("Total Acumulado (Semana)", f"RD$ {total_dop:,.2f}")

    st.divider()

    with st.expander("➕ Registrar Nuevo Cliente, Control y Recibos"):
        st.subheader("➕ Registrar Nuevo Cliente y su Divisa")
        with st.form(key="form_nuevo_cliente"):
            col_nc1, col_nc2 = st.columns(2)
            with col_nc1:
                nuevo_nombre_cli = st.text_input("Nombre de Usuario del Cliente (Ej. Cliente C)")
                nueva_divisa_cli = st.selectbox("Moneda Principal / Divisa", ["Dólares (USD - $)", "Pesos Dominicanos (DOP - RD$)"])
            with col_nc2:
                avatar_nuevo_file = st.file_uploader("Logo / Avatar del Cliente (Opcional)", type=["png", "jpg", "jpeg"])
            
            btn_crear_cli = st.form_submit_button("Registrar Cliente")
            if btn_crear_cli:
                if nuevo_nombre_cli:
                    if nuevo_nombre_cli in st.session_state.clientes_registrados:
                        st.error("¡Este cliente ya está registrado!")
                    else:
                        avatar_bytes_val = avatar_nuevo_file.getvalue() if avatar_nuevo_file else None
                        avatar_nombre_val = avatar_nuevo_file.name if avatar_nuevo_file else None

                        st.session_state.clientes_registrados[nuevo_nombre_cli] = {
                            "divisa": nueva_divisa_cli,
                            "avatar_bytes": avatar_bytes_val,
                            "avatar_nombre": avatar_nombre_val
                        }
                        guardar_datos()
                        st.success(f"¡Cliente '{nuevo_nombre_cli}' agregado con éxito!")
                        st.rerun()
                else:
                    st.error("Por favor, ingresa un nombre para el cliente.")

        st.divider()

        st.subheader("👥 Control, Cierre de Ciclo y Gestión de Clientes")
        for cli in list(st.session_state.clientes_registrados.keys()):
            logos_cli_term = [l for l in st.session_state.logos if l.get('cliente') == cli and l.get('estado', 'Pendiente') == "Terminado"]
            sub_usd = sum(l.get('precio_usd', 5.0) for l in logos_cli_term)
            sub_dop = sum(l.get('precio_dop', 300.0) for l in logos_cli_term)
            
            with st.expander(f"👤 Cliente: {cli} — Acumulado Terminado: ${sub_usd:.2f} USD / RD$ {sub_dop:,.2f}"):
                c_info, c_btn_reset, c_btn_del = st.columns([2, 1, 1])
                with c_info:
                    st.write(f"Trabajos terminados pendientes de cerrar ciclo: **{len(logos_cli_term)}**")
                with c_btn_reset:
                    if st.button(f"🔄 Reiniciar Ciclo", key=f"reset_cli_{cli}"):
                        for logo in st.session_state.logos:
                            if logo.get('cliente') == cli and logo.get('estado', 'Pendiente') == "Terminado":
                                logo['pago'] = "Pagado"
                                logo['estado'] = "Archivado/Pagado"
                        guardar_datos()
                        st.success(f"¡Ciclo de {cli} reiniciado!")
                        st.rerun()
                with c_btn_del:
                    if st.button(f"🗑️ Eliminar Usuario", key=f"del_cli_{cli}"):
                        del st.session_state.clientes_registrados[cli]
                        if cli in st.session_state.recibos_pago:
                            del st.session_state.recibos_pago[cli]
                        st.session_state.logos = [l for l in st.session_state.logos if l.get('cliente') != cli]
                        guardar_datos()
                        st.warning(f"¡Usuario '{cli}' eliminado!")
                        st.rerun()

        st.divider()

        st.subheader("🧾 Recibos de Pago Subidos por Clientes")
        if st.session_state.recibos_pago:
            for cli, recibo_info in st.session_state.recibos_pago.items():
                with st.expander(f"📥 Ver Recibo de Pago de: {cli} ({recibo_info['nombre_archivo']})"):
                    st.download_button(
                        label=f"Descargar comprobante de {cli}",
                        data=recibo_info['bytes'],
                        file_name=recibo_info['nombre_archivo'],
                        mime="application/octet-stream",
                        key=f"dl_recibo_{cli}"
                    )
        else:
            st.info("No hay recibos de pago subidos por los clientes todavía.")

    st.divider()

    logos_activos_admin = [l for l in st.session_state.logos if l.get('estado') != "Archivado/Pagado"]
    logos_por_hacer = [l for l in logos_activos_admin if l.get('estado', 'Pendiente') != "Terminado"]
    logos_terminados = [l for l in logos_activos_admin if l.get('estado', 'Pendiente') == "Terminado"]

    # 1. GESTIÓN DE TRABAJOS ACTIVOS
    st.subheader("📋 Gestión de Trabajos (Pendientes y En Proceso)")
    if not logos_por_hacer:
        st.info("No hay trabajos activos pendientes o en proceso.")

    for idx_cola, logo in enumerate(logos_por_hacer, 1):
        i = st.session_state.logos.index(logo)
        
        with st.container():
            col_img, col_info = st.columns([1, 3])
            
            with col_img:
                if logo.get('imagen_bytes'):
                    try:
                        img_cargada = Image.open(io.BytesIO(logo['imagen_bytes']))
                        st.image(img_cargada, caption="Diseño Original", width=100)
                    except Exception:
                        st.info("Sin miniatura")
                elif logo.get('imagen_obj') is not None:
                    st.image(logo['imagen_obj'], caption="Diseño Original", width=100)
                else:
                    st.info("Sin miniatura")

            with col_info:
                st.markdown(f"### <span style='color: #00ffcc;'>🔢 Cola #{idx_cola}</span> - 🧵 {logo.get('nombre', 'Sin nombre')} *({logo.get('cliente', 'Cliente')})*", unsafe_allow_html=True)
                st.write(f"**Tipo:** {logo.get('tipo', 'Tela')} | **Ubicación:** {logo.get('ubicacion_gorra', 'N/A')} | **Estilo:** {logo.get('detalle_gorra', 'N/A')}")
                st.write(f"**Comentario:** {logo.get('comentario', 'Ninguno')}")
                st.write(f"**Archivo cliente:** `📁 {logo.get('archivo', 'Sin archivo')}`")
                st.write(f"**Precio:** ${logo.get('precio_usd', 5.0):.2f} USD / RD${logo.get('precio_dop', 300.0):.2f}")
            
            estado_actual = logo.get('estado', 'Pendiente')
            c1, c2, c3 = st.columns(3)
            
            if estado_actual == "Pendiente":
                if c1.button("🔍 Pasar a Revisión", key=f"rev_{logo['id']}"):
                    st.session_state.logos[i]['estado'] = "En Revisión"
                    guardar_datos()
                    st.rerun()
            elif estado_actual == "En Revisión":
                c1.info("🔍 En Revisión")
                if c2.button("▶ Iniciar (Luz Verde)", key=f"iniciar_{logo['id']}"):
                    st.session_state.logos[i]['estado'] = "En Progreso"
                    guardar_datos()
                    st.rerun()
            elif estado_actual == "En Progreso":
                c1.warning("🟢 En Progreso")
                if c2.button("✓ Marcar Terminado", key=f"terminar_{logo['id']}"):
                    st.session_state.logos[i]['estado'] = "Terminado"
                    guardar_datos()
                    st.rerun()

            with st.expander("📤 Subir múltiples archivos de bordado (.DST / .EMB / .PDF)"):
                archivos_bordado = st.file_uploader(
                    "Sube los archivos listos para bordar", 
                    type=["dst", "emb", "pes", "jef", "pdf"], 
                    accept_multiple_files=True, 
                    key=f"bordado_{logo['id']}"
                )
                if archivos_bordado:
                    logo['archivos_multiples'] = [{"nombre": f.name, "bytes": f.getvalue()} for f in archivos_bordado]
                    guardar_datos()
                    nombres_str = ", ".join([f.name for f in archivos_bordado])
                    st.success(f"Archivos guardados correctamente: {nombres_str}")

            st.divider()

    # 2. TRABAJOS YA REALIZADOS
    st.subheader("✅ Trabajos Ya Realizados")
    if not logos_terminados:
        st.info("No hay trabajos terminados todavía.")

    for logo in logos_terminados:
        i = st.session_state.logos.index(logo)
        with st.container():
            col_img, col_info = st.columns([1, 3])
            
            with col_img:
                if logo.get('imagen_bytes'):
                    try:
                        img_cargada = Image.open(io.BytesIO(logo['imagen_bytes']))
                        st.image(img_cargada, caption="Diseño Original", width=100)
                    except Exception:
                        st.info("Sin miniatura")
                elif logo.get('imagen_obj') is not None:
                    st.image(logo['imagen_obj'], caption="Diseño Original", width=100)
                else:
                    st.info("Sin miniatura")

            with col_info:
                st.markdown(f"### 🧵 {logo.get('nombre', 'Sin nombre')} *({logo.get('cliente', 'Cliente')})*")
                st.write(f"**Tipo:** {logo.get('tipo', 'Tela')} | **Ubicación:** {logo.get('ubicacion_gorra', 'N/A')} | **Estilo:** {logo.get('detalle_gorra', 'N/A')}")
                st.write(f"**Comentario:** {logo.get('comentario', 'Ninguno')}")
                st.write(f"**Archivo cliente:** `📁 {logo.get('archivo', 'Sin archivo')}`")
                st.write(f"**Precio:** ${logo.get('precio_usd', 5.0):.2f} USD / RD${logo.get('precio_dop', 300.0):.2f}")
            
            c1, c2, c3 = st.columns(3)
            c1.success("✅ Terminado")
            pago_actual = logo.get('pago', 'Pendiente')
            nuevo_pago = c2.selectbox("Estado de Pago", ["Pendiente", "Pagado"], index=0 if pago_actual=="Pendiente" else 1, key=f"pago_{logo['id']}")
            if nuevo_pago != pago_actual:
                st.session_state.logos[i]['pago'] = nuevo_pago
                guardar_datos()
                st.rerun()

            with st.expander("📤 Subir múltiples archivos de bordado (.DST / .EMB / .PDF)"):
                archivos_bordado = st.file_uploader(
                    "Sube los archivos listos para bordar", 
                    type=["dst", "emb", "pes", "jef", "pdf"], 
                    accept_multiple_files=True, 
                    key=f"bordado_term_{logo['id']}"
                )
                if archivos_bordado:
                    logo['archivos_multiples'] = [{"nombre": f.name, "bytes": f.getvalue()} for f in archivos_bordado]
                    guardar_datos()
                    nombres_str = ", ".join([f.name for f in archivos_bordado])
                    st.success(f"Archivos guardados correctamente: {nombres_str}")

            st.divider()

    st.subheader("📄 Generación de Factura / Corte Semanal General")
    if st.button("Generar Corte Semanal"):
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        contenido_factura = f"=========================================\n"
        contenido_factura += f"         PIXEL THREAD - FACTURA          \n"
        contenido_factura += f"           CORTE SEMANAL GENERAL         \n"
        contenido_factura += f"=========================================\n"
        contenido_factura += f"Fecha de emisión: {fecha_actual}\n\n"
        
        total_gen_usd = 0.0
        total_gen_dop = 0.0
        
        for idx, logo in enumerate(st.session_state.logos, 1):
            p_usd = logo.get('precio_usd', 5.0)
            p_dop = logo.get('precio_dop', 300.0)
            total_gen_usd += p_usd
            total_gen_dop += p_dop
            
            contenido_factura += f"Item #{idx}\n"
            contenido_factura += f" - Cliente: {logo.get('cliente', 'N/A')}\n"
            contenido_factura += f" - Diseño: {logo.get('nombre', 'N/A')}\n"
            contenido_factura += f" - Estado: {logo.get('estado', 'Pendiente')}\n"
            contenido_factura += f" - Pago: {logo.get('pago', 'Pendiente')}\n"
            contenido_factura += f" - Precio: ${p_usd:.2f} USD / RD${p_dop:.2f} DOP\n"
            contenido_factura += f"-----------------------------------------\n"
            
        contenido_factura += f"\nTOTAL GENERAL ACUMULADO:\n"
        contenido_factura += f"USD: ${total_gen_usd:.2f}\n"
        contenido_factura += f"DOP: RD$ {total_gen_dop:,.2f}\n"
        contenido_factura += f"=========================================\n"
        
        st.success("¡Corte y factura generados con éxito!")
        
        st.download_button(
            label="⬇️ Descargar Factura / Corte en TXT",
            data=contenido_factura,
            file_name=f"factura_corte_semanal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )

# ==========================================
# 2. VISTA PORTAL DE CLIENTES
# ==========================================
else:
    nombre_cliente = st.session_state.sesion_activa
    info_cliente = st.session_state.clientes_registrados.get(nombre_cliente, {"divisa": "Dólares (USD - $)", "avatar_bytes": None})
    if isinstance(info_cliente, dict):
        divisa_default = info_cliente.get("divisa", "Dólares (USD - $)")
        avatar_bytes = info_cliente.get("avatar_bytes", None)
    else:
        divisa_default = info_cliente
        avatar_bytes = None

    col_av, col_tit = st.columns([1, 12])
    with col_av:
        if avatar_bytes:
            try:
                img_avatar = Image.open(io.BytesIO(avatar_bytes))
                st.image(img_avatar, width=55)
            except Exception:
                st.markdown("👤")
        else:
            st.markdown("👤")
            
    with col_tit:
        st.title(f"Portal de Cliente: {nombre_cliente}")

    st.write("Bienvenido a Pixel Thread. Gestiona tus solicitudes y descarga tus archivos de bordado digitalizados.")
    
    divisa = st.radio("Selecciona tu moneda:", ["Dólares (USD - $)", "Pesos Dominicanos (DOP - RD$)"], index=0 if "Dólares" in divisa_default else 1, horizontal=True, key=f"divisa_{nombre_cliente}")
    
    logos_cliente = [l for l in st.session_state.logos if l.get('cliente') == nombre_cliente and l.get('estado') != "Archivado/Pagado"]
    
    col_metrica, col_vacio = st.columns(2)

    with col_metrica:
        if "Dólares" in divisa:
            total_cliente = sum(l.get('precio_usd', 5.0) for l in logos_cliente if l.get('estado', 'Pendiente') == "Terminado")
            st.metric("Total Acumulado (Semana)", f"${total_cliente:.2f} USD")
        else:
            total_cliente = sum(l.get('precio_dop', 300.0) for l in logos_cliente if l.get('estado', 'Pendiente') == "Terminado")
            st.metric("Total Acumulado (Semana)", f"RD$ {total_cliente:,.2f}")

    st.divider()

    # --- ACCESOS RÁPIDOS EN DOS COLUMNAS ---
    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        with st.popover("🧾 Subir Recibo de Pago", use_container_width=True):
            recibo_subido = st.file_uploader("Sube tu comprobante", type=["png", "jpg", "jpeg", "pdf"], key=f"recibo_file_{nombre_cliente}")
            
            if st.button("Enviar Comprobante", key=f"btn_enviar_recibo_{nombre_cliente}"):
                if recibo_subido:
                    st.session_state.recibos_pago[nombre_cliente] = {
                        "nombre_archivo": recibo_subido.name,
                        "bytes": recibo_subido.getvalue()
                    }
                    st.success("¡Recibo enviado al administrador con éxito!")
                else:
                    st.error("Por favor, selecciona un archivo antes de enviar el comprobante.")

    with col_btn2:
        with st.popover("➕ Enviar Nuevo Logo", use_container_width=True):
            if st.session_state.form_enviado:
                st.success("✅ ¡ORDEN AGREGADA CORRECTAMENTE!")
                if st.button("Enviar otro diseño", key=f"otro_{nombre_cliente}"):
                    st.session_state.form_enviado = False
                    st.rerun()
            else:
                nombre_logo = st.text_input("Nombre del Logo / Diseño", key=f"inp_nom_{nombre_cliente}")
                
                archivos_subidos = st.file_uploader(
                    "Sube tus archivos originales", 
                    type=["png", "jpg", "jpeg", "ai", "pdf"], 
                    accept_multiple_files=True, 
                    key=f"inp_file_{nombre_cliente}"
                )
                
                if archivos_subidos:
                    st.write("🖼️ **Vista previa:**")
                    cols_prev = st.columns(min(len(archivos_subidos), 4))
                    for idx, arch in enumerate(archivos_subidos):
                        try:
                            img_prev = Image.open(arch)
                            with cols_prev[idx % 4]:
                                st.image(img_prev, caption=arch.name, width=80)
                        except Exception:
                            pass

                tipo_aplicacion = st.radio("¿Para qué tipo de soporte es el bordado?", ["Tela (Camisetas, Polos, etc.)", "Gorra"], key=f"tipo_app_{nombre_cliente}")
                
                ubicacion_gorra = "N/A"
                detalle_gorra = "N/A"
                
                if tipo_aplicacion == "Gorra":
                    ubicacion_gorra = st.radio("Ubicación en la gorra:", ["Frontal", "Trasero", "Lateral"], key=f"ubicacion_{nombre_cliente}")
                    if ubicacion_gorra == "Frontal":
                        detalle_gorra = st.radio("Estilo:", ["3D (Puff)", "Plano (Flat)"], key=f"detalle_{nombre_cliente}")
                    else:
                        detalle_gorra = "Plano (Flat)"
                
                comentario_cliente = st.text_area("Comentarios o instrucciones especiales", key=f"inp_com_{nombre_cliente}")
                
                if st.button("Enviar Logo a Pixel Thread", key=f"btn_enviar_{nombre_cliente}"):
                    if nombre_logo:
                        nombre_archivo = ", ".join([f.name for f in archivos_subidos]) if archivos_subidos else "Sin archivo adjunto"
                        
                        img_bytes_guardar = None
                        if archivos_subidos:
                            try:
                                img_bytes_guardar = archivos_subidos[0].getvalue()
                            except Exception:
                                pass

                        nuevo_logo = {
                            "id": len(st.session_state.logos) + 1,
                            "cliente": nombre_cliente,
                            "nombre": nombre_logo,
                            "precio_usd": 5.0,
                            "precio_dop": 300.0,
                            "estado": "Pendiente",
                            "pago": "Pendiente",
                            "tipo": tipo_aplicacion,
                            "ubicacion_gorra": ubicacion_gorra,
                            "detalle_gorra": detalle_gorra,
                            "comentario": comentario_cliente if comentario_cliente else "Ninguno",
                            "archivo": nombre_archivo,
                            "imagen_bytes": img_bytes_guardar
                        }
                        st.session_state.logos.append(nuevo_logo)
                        guardar_datos()
                        st.session_state.form_enviado = True
                        st.toast("¡Orden agregada con éxito!", icon="🎉")
                        st.rerun()
                    else:
                        st.error("Por favor, ingresa un nombre para el logo.")

    st.divider()

    logos_por_realizar = [l for l in logos_cliente if l.get('estado', 'Pendiente') != "Terminado"]
    logos_realizados = [l for l in logos_cliente if l.get('estado', 'Pendiente') == "Terminado"]

    # TRABAJOS POR REALIZAR
    st.subheader("⏳ Trabajos por Realizar y Estado en Cola")
    if not logos_por_realizar:
        st.info("No tienes trabajos pendientes actualmente.")

    todos_activos_global = [l for l in st.session_state.logos if l.get('estado') != "Archivado/Pagado" and l.get('estado', 'Pendiente') != "Terminado"]

    for logo in logos_por_realizar:
        try:
            posicion_en_cola = todos_activos_global.index(logo) + 1
        except ValueError:
            posicion_en_cola = "N/A"

        col_img, col_info = st.columns([1, 3])
        with col_img:
            if logo.get('imagen_bytes'):
                try:
                    img_cargada = Image.open(io.BytesIO(logo['imagen_bytes']))
                    st.image(img_cargada, caption=logo.get('nombre', 'Diseño'), width=100)
                except Exception:
                    st.info("Sin miniatura")
            elif logo.get('imagen_obj') is not None:
                st.image(logo['imagen_obj'], caption=logo.get('nombre', 'Diseño'), width=100)
            else:
                st.info("Sin miniatura")
                
        with col_info:
            st.markdown(f"### <span style='color: #00ffcc;'>🔢 Posición en Cola: #{posicion_en_cola}</span> — 🧵 {logo.get('nombre', 'Logo')}", unsafe_allow_html=True)
            st.write(f"**Aplicación:** {logo.get('tipo', 'Tela')} | **Ubicación:** {logo.get('ubicacion_gorra', 'N/A')} | **Estilo:** {logo.get('detalle_gorra', 'N/A')}")
            st.write(f"**Tus notas:** {logo.get('comentario', 'Ninguno')}")
            st.write(f"**Archivos:** `📁 {logo.get('archivo', 'N/A')}`")
        
        estado_logo = logo.get('estado', 'Pendiente')
        if estado_logo == "Pendiente":
            st.info(f"⏳ Estado: Recibido (Tu orden está en el puesto #{posicion_en_cola} de la cola general)")
            col_mod, col_elim = st.columns(2)
            with col_mod:
                with st.popover("✏️ Modificar Orden"):
                    with st.form(key=f"edit_form_{logo['id']}"):
                        nuevo_nombre = st.text_input("Nuevo nombre", value=logo.get('nombre', ''))
                        nuevo_comentario = st.text_area("Nuevas notas", value=logo.get('comentario', ''))
                        if st.form_submit_button("Guardar Cambios"):
                            logo['nombre'] = nuevo_nombre
                            logo['comentario'] = nuevo_comentario
                            guardar_datos()
                            st.success("Orden actualizada correctamente")
                            st.rerun()
            with col_elim:
                if st.button("🗑️ Eliminar Orden", key=f"del_ord_{logo['id']}"):
                    st.session_state.logos = [l for l in st.session_state.logos if l['id'] != logo['id']]
                    guardar_datos()
                    st.warning("Orden eliminada")
                    st.rerun()
        else:
            st.warning(f"🟢 Estado: {estado_logo} (Tu orden está en proceso, no se permiten modificaciones)")

        st.divider()

    # TRABAJOS COMPLETADOS
    st.subheader("✅ Trabajos Completados y Archivos de Bordado")
    if not logos_realizados:
        st.info("No tienes trabajos completados aún.")

    for logo in logos_realizados:
        col_img, col_info = st.columns([1, 3])
        with col_img:
            if logo.get('imagen_bytes'):
                try:
                    img_cargada = Image.open(io.BytesIO(logo['imagen_bytes']))
                    st.image(img_cargada, caption=logo.get('nombre', 'Diseño'), width=100)
                except Exception:
                    st.info("Sin miniatura")
            elif logo.get('imagen_obj') is not None:
                st.image(logo['imagen_obj'], caption=logo.get('nombre', 'Diseño'), width=100)
            else:
                st.info("Sin miniatura")

        with col_info:
            st.markdown(f"### 🧵 {logo.get('nombre', 'Logo')}")
            st.write(f"**Aplicación:** {logo.get('tipo', 'Tela')} | **Ubicación:** {logo.get('ubicacion_gorra', 'N/A')}")
            st.write(f"**Precio:** ${logo.get('precio_usd', 5.0):.2f} USD / RD${logo.get('precio_dop', 300.0):.2f}")
            st.success("✅ Diseño Listo para Bordar")

            if "archivos_multiples" in logo and logo["archivos_multiples"]:
                st.write("📥 **Archivos listos para descargar:**")
                for arch in logo["archivos_multiples"]:
                    if isinstance(arch, dict) and "bytes" in arch:
                        st.download_button(
                            label=f"⬇️ Descargar {arch['nombre']}",
                            data=arch["bytes"],
                            file_name=arch["nombre"],
                            mime="application/octet-stream",
                            key=f"dl_file_{logo['id']}_{arch['nombre']}"
                        )
            else:
                st.info("El administrador aún está subiendo los archivos matriculados (.DST/.EMB).")

        st.divider()
