from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import glob
from ocr import run_ocr  # Your OCR function

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])  # Allow React frontend

@app.route('/api/list-dirs', methods=['GET'])
def list_dirs():
    base_path = request.args.get('path', '.')
    if not os.path.isdir(base_path):
        return jsonify({'dirs': []})
    dirs = []
    try:
        for entry in os.scandir(base_path):
            if entry.is_dir():
                dirs.append({'name': entry.name, 'full': os.path.abspath(entry.path)})
    except Exception as e:
        print(f"Error listing directories: {e}")
    return jsonify({'dirs': dirs})

@app.route('/api/set-path', methods=['POST'])
def set_path():
    data = request.get_json()
    path = data.get('path')
    if not path or not os.path.isdir(path):
        return jsonify({'error': 'Invalid directory path'}), 400

    cache_dir = os.path.join(path, 'recollect')
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

        # Find all images to OCR
        image_extensions = ['*.png','*.jpg','*.jpeg','*.bmp','*.tiff']
        image_files = []
        for ext in image_extensions:
            image_files.extend(glob.glob(os.path.join(path, ext)))

        for img_path in image_files:
            try:
                ocr_text = run_ocr(img_path)
                base_name = os.path.splitext(os.path.basename(img_path))[0]
                with open(os.path.join(cache_dir, f'{base_name}.txt'), 'w', encoding='utf-8') as out_f:
                    out_f.write(ocr_text)
            except Exception as e:
                print(f"Failed OCR for {img_path}: {e}")

    return jsonify({'ok': True, 'path': path})

@app.route('/api/search', methods=['POST'])
def search():
    data = request.get_json()
    query = data.get('q', '').lower()
    path = data.get('path')
    if not query:
        return jsonify({'results': []})
    if not path or not os.path.isdir(path):
        return jsonify({'error': 'Invalid directory path'}), 400

    results = []
    search_dir = os.path.join(path, 'recollect')
    if not os.path.exists(search_dir):
        return jsonify({'results': []})

    for root, dirs, files in os.walk(search_dir):
        for filename in files:
            file_path = os.path.join(root, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    if query in content:
                        idx = content.find(query)
                        start = max(idx - 50, 0)
                        end = min(idx + 150, len(content))
                        excerpt = f"...{content[start:end]}..."
                        results.append({'path': file_path, 'excerpt': excerpt})
            except Exception:
                continue

    return jsonify({'results': results})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
