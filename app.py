import os
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from deepface import DeepFace
from PIL import Image
from flask_cors import CORS
from dotenv import load_dotenv

app = Flask(__name__)

# Database Configuration
# app.config['DB_HOST'] = 'localhost'  
# app.config['DB_USER'] = 'root'       
# app.config['DB_PASSWORD'] = ''       
# app.config['DB_NAME'] = 'face_match' 

# app.config['DB_HOST'] = 'localhost'  
# app.config['DB_USER'] = 'pineslhw_hovsol'       
# app.config['DB_PASSWORD'] = '@}B3({jE4aDG'       
# app.config['DB_NAME'] = 'pineslhw_face_match'

load_dotenv()
app.config['DB_HOST'] = os.getenv('DB_HOST')
app.config['DB_USER'] = os.getenv('DB_USER')
app.config['DB_PASSWORD'] = os.getenv('DB_PASSWORD')
app.config['DB_NAME'] = os.getenv('DB_NAME')


# Connect to the database
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=app.config['DB_HOST'],
            user=app.config['DB_USER'],
            password=app.config['DB_PASSWORD'],
            database=app.config['DB_NAME']
        )
        print("Database connection successful!")
        return conn
    except Error as e:
        print(f"Error connecting to the database: {e}")
        return None

UPLOAD_FOLDER = 'uploads'
GALLERY_FOLDER = 'gallery'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists(GALLERY_FOLDER):
    os.makedirs(GALLERY_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_image(image_path):
    try:
        with Image.open(image_path) as img:
            if img.mode != "RGB":
                print(f"Converting {image_path} to RGB format.")
                img = img.convert("RGB")
                img.save(image_path)
    except Exception as e:
        print(f"Error preprocessing {image_path}: {e}")
        raise e

def load_gallery():
    gallery = []
    for file_name in os.listdir(GALLERY_FOLDER):
        file_path = os.path.join(GALLERY_FOLDER, file_name)
        try:
            preprocess_image(file_path)
            gallery.append((file_name, file_path))
        except Exception as e:
            print(f"Error processing gallery image {file_name}: {e}")
    return gallery

GALLERY_IMAGES = load_gallery()
CORS(app)

@app.route('/check', methods=['GET'])
def check_api():
    return jsonify({
        "message": "API is running successfully!",
        "status": "OK"
    }), 200



@app.route('/add_to_gallery', methods=['POST'])
def add_to_gallery():
    app_id = request.headers.get('app-id')
    app_key = request.headers.get('app-key')

    if not app_id or not app_key:
        return jsonify({"error": "Missing app_id or app_key in headers"}), 400

    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM fm_user_api WHERE app_id = %s AND app_key = %s"
        cursor.execute(query, (app_id, app_key))
        user = cursor.fetchone()

        if not user:
            cursor.close()
            conn.close()
            return jsonify({"error": "Invalid app_id or app_key"}), 403

        if 'image' not in request.files:
            return jsonify({"error": "No image part in the request"}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No file selected for uploading"}), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(GALLERY_FOLDER, filename)
            file.save(file_path)
            try:
                preprocess_image(file_path)
                insert_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                query = "INSERT INTO fm_gallery (id_user_api, img_name, insert_time) VALUES (%s, %s, %s)"
                cursor.execute(query, (user['id'], filename, insert_time))
                conn.commit()

                return jsonify({"message": "Image added to gallery and database successfully."}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500
            finally:
                cursor.close()
                conn.close()

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"error": "Allowed file types are png, jpg, jpeg"}), 400



@app.route('/match', methods=['POST'])
def match_api():
    app_id = request.headers.get('app-id')
    app_key = request.headers.get('app-key')

    if not app_id or not app_key:
        return jsonify({"error": "Missing app_id or app_key in headers"}), 400

    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM fm_user_api WHERE app_id = %s AND app_key = %s"
        cursor.execute(query, (app_id, app_key))
        user = cursor.fetchone()

        if not user:
            cursor.close()
            conn.close()
            return jsonify({"error": "Invalid app_id or app_key"}), 403
    except Exception as e:
        return jsonify({"error": f"Database query failed: {str(e)}"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

    if 'image' not in request.files:
        return jsonify({"error": "No image part in the request"}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No file selected for uploading"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        try:
            preprocess_image(file_path)
            results = []

            for gallery_name, gallery_path in GALLERY_IMAGES:
                try:
                    verification = DeepFace.verify(
                        img1_path=file_path,
                        img2_path=gallery_path,
                        enforce_detection=False,
                        distance_metric="cosine"
                    )
                    distance = verification['distance']
                    similarity = (1 - distance) * 100
                    verified = verification['verified']
                    model = verification['model']
                    threshold = verification['threshold']
                    if verification['verified']:
                        results.append({
                            "file_name": gallery_name,
                            "similarity_percentage": round(similarity, 2),
                            "distance": round(distance, 4),
                            "model": model,
                            "threshold": threshold,
                            "verified": verified
                        })
                except Exception as e:
                    print(f"Error matching with {gallery_name}: {e}")

            filtered_results = [result for result in results if result["similarity_percentage"] > 20]
            filtered_results = sorted(filtered_results, key=lambda x: x['similarity_percentage'], reverse=True)

            return jsonify({"matches": filtered_results})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    return jsonify({"error": "Allowed file types are png, jpg, jpeg"}), 400



if __name__ == '__main__':
    conn = get_db_connection()
    if conn is not None:
        conn.close()
    app.run(debug=True)
