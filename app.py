from flask import Flask, request, jsonify
from firebase_admin import storage, firestore
import firebase_admin
from firebase_admin import credentials

# Asegúrate de tener inicializado firebase_admin en tu app.py previamente con tus credenciales:
# cred = credentials.Certificate("ruta/a/tus/credenciales.json")
# firebase_admin.initialize_app(cred, {'storageBucket': 'pixel-thread-db.appspot.com'})

app = Flask(__name__)
db = firestore.client()

@app.route('/subir-pedido', methods=['POST'])
def subir_pedido():
    try:
        # 1. Verificar si se envió un archivo en la petición
        if 'archivo' not in request.files:
            return jsonify({"error": "No se encontró ningún archivo"}), 400
        
        archivo = request.files['archivo']
        
        if archivo.filename == '':
            return jsonify({"error": "El archivo no tiene un nombre válido"}), 400

        # 2. Obtener datos adicionales del formulario (si los hay)
        nombre_cliente = request.form.get('nombre_cliente', 'Sin nombre')
        
        # 3. Referenciar el bucket de Firebase Storage
        bucket = storage.bucket()
        
        # 4. Crear una ruta única en el storage para el archivo
        filename = f"pedidos_archivos/{archivo.filename}"
        blob = bucket.blob(filename)
        
        # 5. Subir el archivo binario directamente desde el stream de la petición
        # Especificamos el content_type para conservar el formato original
        blob.upload_from_file(
            archivo.stream, 
            content_type=archivo.content_type
        )
        
        # 6. Hacer opcionalmente público o generar una URL firmada (o usar la URL pública si el bucket lo permite)
        # Nota: Si tus reglas permiten lectura pública, puedes usar blob.public_url
        # Si prefieres una URL de descarga segura, puedes usar blob.generate_signed_url(...)
        blob.make_public()
        download_url = blob.public_url

        # 7. Guardar únicamente la URL y los datos en Firestore (evitando el error de 1MB)
        pedido_data = {
            "nombre_cliente": nombre_cliente,
            "archivoUrl": download_url,
            "archivoNombre": archivo.filename,
            "fechaSubida": firestore.SERVER_TIMESTAMP
        }
        
        # Guardar en la colección 'pedidos_bordado'
        update_time, doc_ref = db.collection('pedidos_bordado').add(pedido_data)

        return jsonify({
            "success": True, 
            "message": "¡Pedido y archivo subidos con éxito!",
            "id_documento": doc_ref.id,
            "url": download_url
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
