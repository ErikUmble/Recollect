from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from ocr import run_ocr
from search import search_documents, create_index

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])
documents = []       # Stored as relative paths

@app.route('/api/file', methods=['GET'])
def get_file():
    rel = request.args.get('path')
    if not rel:
        return {'error': 'Missing path'}, 400
    abs_path = os.path.abspath(rel)
    if not os.path.isfile(abs_path):
        return {'error': 'File not found'}, 404
    return send_file(abs_path)

@app.route('/api/list-dirs', methods=['GET'])
def list_dirs():
    base = request.args.get('path', '.')
    base_abs = os.path.abspath(base)

    if not os.path.isdir(base_abs):
        return jsonify({'dirs': []})

    dirs = []
    for entry in os.scandir(base_abs):
        if entry.is_dir():
            dirs.append({
                'name': entry.name,
                'full': os.path.relpath(entry.path, base_abs)  # relative to requested path
            })

    return jsonify({'dirs': dirs})


@app.route('/api/set-path', methods=['POST'])
def set_path():
    global documents
    data = request.get_json()
    path = data.get('path')

    if not path or not os.path.isdir(path):
        return jsonify({'error': 'Invalid directory path'}), 400

    documents = create_index(path, use_cache=True)
    return jsonify({
        'status': 'Index created',
        'num_documents': len(documents),
    })


@app.route('/api/search', methods=['POST'])
def search():
    global documents

    data = request.get_json()
    query = data.get('query')
    path = data.get('path')
    documents = create_index(path, use_cache=True)

    if not query or not documents:
        return jsonify({'results': []})

    # Now search uses absolute paths internally
    matches = search_documents(query, documents, top_k=5)

    grouped = {}

    for doc in matches:
        path = doc.path
        dir = os.path.dirname(path)

        if dir not in grouped:
            # list all files in that dir
            all_files = [os.path.join(dir, f) for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f))]
            grouped[dir] = {
                'all_files': all_files,
                'matching_indices': []
            }

        all_files = grouped[dir]['all_files']
        idx = all_files.index(path)
        grouped[dir]['matching_indices'].append(idx)

    # Convert grouped result into list
    results = []
    for dir_name, data in grouped.items():
        results.append({
            'dir': dir_name,
            'all_files': data['all_files'],
            'matching_indices': data['matching_indices']
        })
    return jsonify({'results': results})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
