from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import glob
from ocr import run_ocr  # Your OCR function

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])  # Allow React frontend

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
    Returns JSON with each result containing:
    - 'image': index of the main image in the all_files list
    - 'all_files': list of full file paths in the directory
    """
    # Example main image
    main_image = 'tests/data/The_Rensselaer_Polytechnic:_April_1,_1918/page1.jpg'
    directory = os.path.dirname(main_image)

    try:
        # Full paths for all files in directory
        all_files = [
            os.path.abspath(os.path.join(directory, f))
            for f in os.listdir(directory)
            if os.path.isfile(os.path.join(directory, f))
        ]
        all_files.sort()

        # Determine index of main image
        try:
            main_index = all_files.index(os.path.abspath(main_image))
        except ValueError:
            main_index = 0
    except Exception:
        all_files = []
        main_index = 0

    result = {
        'image': main_index,
        'all_files': all_files
    }

    return jsonify({'results': [result]})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
