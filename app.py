# --- VISOR 3D CORREGIDO Y OPTIMIZADO ---
        model_viewer_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
            <style>
                body {{ margin: 0; background-color: #262626; overflow: hidden; }}
                model-viewer {{
                    width: 100%;
                    height: 360px;
                    background-color: #191919;
                    border-radius: 12px;
                }}
            </style>
        </head>
        <body>
            <model-viewer 
                src="https://modelviewer.dev/shared-assets/models/Astronaut.glb" 
                alt="Maqueta 3D" 
                auto-rotate 
                camera-controls 
                interaction-prompt="none">
            </model-viewer>
        </body>
        </html>
        """
        
        st.components.v1.html(model_viewer_html, height=380)
