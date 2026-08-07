with st.expander("➕ Enviar Nuevo Pedido", expanded=False):
                with st.form("form_pedido_streamlit", clear_on_submit=True):
                    nombre_proyecto = st.text_input("1. Nombre o Referencia del Proyecto")
                    archivo_subido = st.file_uploader("2. Sube tu Logo del Pedido (PNG, JPG, DST, PES)", type=["png", "jpg", "jpeg", "dst", "pes"])
                    
                    st.markdown("3. **Selecciona el Tipo de Producto:**")
                    tipo_producto = st.radio("Producto:", ["GORRA", "TELA"], horizontal=True, label_visibility="collapsed")
                    
                    # Variables de control
                    ubicacion = None
                    estilo_frente = None
                    
                    # Lógica condicional visual
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

                            # Construcción dinámica de los datos
                            data_pedido = {
                                "id": "PT-" + str(int(datetime.now().timestamp())),
                                "cliente": st.session_state.user.strip(),
                                "nombre_proyecto": nombre_proyecto,
                                "producto": tipo_producto,
                                "archivo_nombre": file_name,
                                "archivo_data": img_base64,
                                "estado": "Pendiente",
                                "timestamp": datetime.now()
                            }
                            
                            # Solo agregamos las llaves si son relevantes
                            if tipo_producto == "GORRA":
                                data_pedido["ubicacion"] = ubicacion
                                if ubicacion == "FRENTE":
                                    data_pedido["estilo"] = estilo_frente
                                else:
                                    data_pedido["estilo"] = "N/A"
                            else:
                                data_pedido["ubicacion"] = "N/A"
                                data_pedido["estilo"] = "N/A"
                            
                            db.collection("pedidos_bordado").add(data_pedido)
                            st.success("¡Pedido enviado y guardado correctamente!")
                            st.rerun()
