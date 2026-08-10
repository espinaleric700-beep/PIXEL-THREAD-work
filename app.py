with st.expander("👕 Configurar Patrón Base por Piezas y Modelo 3D", expanded=True):
        config_actual = obtener_configuracion_activa()
        nuevo_nombre = st.text_input("Nombre del Modelo / Prenda", config_actual.get("nombre_modelo", "Camisa Estándar"))
        
        # Usar la URL directa del modelo 3D (Se recomienda alojarlo en un enlace público directo)
        st.markdown("##### Modelo 3D (.glb)")
        nueva_url_3d = st.text_input(
            "URL pública del archivo .glb (Ej: Enlace directo o CDN)", 
            config_actual.get("modelo_3d_url", "https://modelviewer.dev/shared-assets/models/Astronaut.glb")
        )
        
        st.markdown("<caption style='color: #aaa;'>Consejo: Sube tu archivo .glb a un servidor de enlaces directos o Firebase Storage y pega la URL aquí para evitar problemas de espacio en la base de datos.</caption>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("##### Subir Imágenes Base de las Piezas del Patrón")
        
        up_frente = st.file_uploader("Frente", type=["svg", "png", "jpg", "jpeg"], key="up_f")
        up_espalda = st.file_uploader("Espalda", type=["svg", "png", "jpg", "jpeg"], key="up_e")
        up_cuello = st.file_uploader("Cuello", type=["svg", "png", "jpg", "jpeg"], key="up_c")
        up_manga_izq = st.file_uploader("Manga Izquierda", type=["svg", "png", "jpg", "jpeg"], key="up_mi")
        up_manga_der = st.file_uploader("Manga Derecha", type=["svg", "png", "jpg", "jpeg"], key="up_md")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("💾 Guardar Patrón Base"):
                try:
                    piezas_actuales = config_actual.get("piezas", {})
                    
                    def actualizar_pieza_base(up_f, key_name):
                        if up_f:
                            b64, tipo = procesar_archivo_subido(up_f)
                            if key_name not in piezas_actuales:
                                piezas_actuales[key_name] = {"b64": "", "tipo": "raster", "elementos": []}
                            piezas_actuales[key_name]["b64"] = b64
                            piezas_actuales[key_name]["tipo"] = tipo

                    actualizar_pieza_base(up_frente, "frente")
                    actualizar_pieza_base(up_espalda, "espalda")
                    actualizar_pieza_base(up_cuello, "cuello")
                    actualizar_pieza_base(up_manga_izq, "manga_izq")
                    actualizar_pieza_base(up_manga_der, "manga_der")
                    
                    # Guardamos únicamente la configuración y la URL del modelo 3D (evitando saturar Firestore)
                    db.collection("config_estudio").document("modelo_actual").set({
                        "nombre_modelo": nuevo_nombre,
                        "modelo_3d_url": nueva_url_3d,
                        "piezas": piezas_actuales,
                        "actualizado": datetime.now()
                    }, merge=True)
                    st.success("¡Patrón base y modelo 3D guardados con éxito!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
