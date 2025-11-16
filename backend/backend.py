from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import glob
from ocr import run_ocr  # Your OCR function
from search import search_documents, create_index

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])  # Allow React frontend
documents = []

@app.route('/api/file', methods=['GET'])
def get_file():
    path = request.args.get('path')
    if not path or not os.path.isfile(path):
        return {'error': 'File not found'}, 404
    try:
        return send_file(path, as_attachment=False)
    except Exception as e:
        return {'error': str(e)}, 500

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
    """
    Returns JSON list of:
    dir name, list of indicies of matching files, and
    list of all filenames in that directory.
    """
    data = request.get_json()
    query = data.get('query')

    if not query:
        return jsonify({'results': []})

    matching_paths = search_documents(query, documents)
    results = []
    for document in matching_paths:
        path = document.path
        # convert path to absolute
        path = os.path.abspath(path)
        dir_name = os.path.dirname(path)
        all_files = [os.path.abspath(doc.path) for doc in documents if os.path.dirname(os.path.abspath(doc.path)) == dir_name]
        match_index = all_files.index(path) if path in all_files else -1
        results.append({
            'dir': dir_name,
            'match_index': match_index,
            'all_files': all_files
        })
    return jsonify({'results': results})

if __name__ == '__main__':
    documents = create_index('tests/data/', use_cache=True)
    app.run(debug=True, port=5000)
