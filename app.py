# ... dentro del bloque del expander ...
            with st.form("form_pedido_streamlit", clear_on_submit=True):
                nombre_proyecto = st.text_input("1. Nombre o Referencia del Proyecto")
                archivos_subidos = st.file_uploader(
                    "2. Sube tus Archivos del Pedido (PNG, JPG, DST, PES, PDF, EMB)", 
                    type=["png", "jpg", "jpeg", "dst", "pes", "pdf", "emb"],
                    accept_multiple_files=True
                )
                comentarios = st.text_area("3. Comentarios o Instrucciones Adicionales (Opcional)")
                submit_pedido = st.form_submit_button("🚀 ENVIAR PEDIDO A PRODUCCIÓN")
                
                if submit_pedido:
                    # Contenedor para mostrar mensajes de estado
                    status_placeholder = st.empty()
                    
                    if not nombre_proyecto:
                        status_placeholder.warning("⚠️ Debes ingresar el nombre o referencia del proyecto.")
                    elif not archivos_subidos:
                        status_placeholder.error("❌ Error: Debes adjuntar al menos un archivo.")
                    else:
                        try:
                            # Indicador de carga
                            status_placeholder.info("⏳ Procesando y enviando archivos, por favor espera...")
                            
                            lista_archivos_guardados = []
                            for archivo in archivos_subidos:
                                bytes_contenido = archivo.getvalue()
                                
                                # Procesamiento de imagen
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

                            # Guardado en Firestore
                            db.collection("pedidos_bordado").add({
                                "id": f"PT-{int(datetime.now().timestamp())}",
                                "cliente": str(st.session_state.user.strip()),
                                "nombre_proyecto": str(nombre_proyecto),
                                "producto": str(tipo_producto),
                                "ubicacion": str(ubicacion),
                                "estilo": str(estilo_frente),
                                "archivos": lista_archivos_guardados,
                                "comentarios": str(comentarios),
                                "estado": "Pendiente",
                                "timestamp": datetime.now()
                            })
                            
                            # ÉXITO: Limpiar, cerrar y notificar
                            st.session_state.expandir_nuevo_pedido = False
                            status_placeholder.success("🎉 ¡Pedido enviado correctamente!")
                            st.rerun() # Recarga para refrescar la lista y cerrar el expander
                            
                        except Exception as e:
                            # ERROR: Notificar sin cerrar el formulario
                            status_placeholder.error(f"❌ Error al enviar el pedido: {e}")
                            st.session_state.expandir_nuevo_pedido = True
