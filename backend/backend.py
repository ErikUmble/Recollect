from flask import Flask, request, jsonify, send_from_directory
import os

app = Flask(__name__)

# In-memory storage of directory path
current_directory = {'path': None}

@app.route('/')
def index():
    # Serve the frontend HTML
    return send_from_directory('../frontend', 'frontend.html')

@app.route('/api/set-path', methods=['POST'])
def set_path():
    data = request.get_json()
    path = data.get('path')
    if not path or not os.path.isdir(path):
        return jsonify({'error': 'Invalid directory path'}), 400
    current_directory['path'] = path
    return jsonify({'ok': True, 'path': path})

@app.route('/api/search', methods=['POST'])
def search():
    if not current_directory['path']:
        return jsonify({'error': 'Directory not set'}), 400

    data = request.get_json()
    query = data.get('q', '').lower()
    if not query:
        return jsonify({'results': []})

    results = []
    for root, dirs, files in os.walk(current_directory['path']):
        for filename in files:
            file_path = os.path.join(root, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    if query in content:
                        excerpt_index = content.find(query)
                        start = max(excerpt_index - 50, 0)
                        end = min(excerpt_index + 150, len(content))
                        excerpt = f"...{content[start:end]}..."
                        results.append({'path': file_path, 'excerpt': excerpt})
            except Exception:
                continue

    return jsonify({'results': results})

if __name__ == '__main__':
    app.run(debug=True)
