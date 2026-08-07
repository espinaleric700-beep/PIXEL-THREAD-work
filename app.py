@st.cache_data(ttl=60)
def obtener_pedidos_cached():
    # Obtener documentos de manera eficiente
    docs = list(db.collection("pedidos_bordado").order_by("timestamp").stream())
    return [(doc.id, doc.to_dict()) for doc in docs]

# --- LÓGICA DE NAVEGACIÓN Y ESTADOS ---
if "modo_vista" not in st.session_state: st.session_state.modo_vista = "Cliente"
if "user" not in st.session_state: st.session_state.user = ""

# --- UI PRINCIPAL ---
st.title("⚡ PIXEL THREAD")

# --- PANEL CLIENTE ---
if st.session_state.modo_vista == "Cliente":
    user_input = st.text_input("Usuario:", value=st.session_state.user)
    if user_input != st.session_state.user:
        st.session_state.user = user_input
        st.rerun()

    if st.session_state.user:
        try:
            # Usar la función cacheada
            todos_los_pedidos = obtener_pedidos_cached()
            mis_pedidos = [p for id, p in todos_los_pedidos if p.get("cliente", "").strip().lower() == st.session_state.user.strip().lower()]
            
            st.subheader(f"Pedidos de {st.session_state.user}")
            for p in mis_pedidos:
                st.write(f"Proyecto: {p.get('nombre_proyecto')} | Estado: {p.get('estado')}")
        except Exception as e:
            st.error("Límite de cuota alcanzado. Espera unos segundos.")
            
# --- PANEL ADMIN (Simplificado) ---
elif st.session_state.modo_vista == "Admin":
    try:
        todos_los_pedidos = obtener_pedidos_cached()
        st.subheader("Panel de Admin")
        for id, p in todos_los_pedidos:
            st.write(f"Cliente: {p.get('cliente')} | Proyecto: {p.get('nombre_proyecto')}")
    except Exception as e:
        st.error("Límite de cuota alcanzado.")
