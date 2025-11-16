from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
from search import search_documents, get_cached_index_only
from agent import build_agent
from local_toolkit import set_agent_documents
from langchain_core.messages import HumanMessage
import threading

from dotenv import load_dotenv
load_dotenv()

DEMO_MODE = os.getenv('VITE_DEMO_MODE', 'true').lower() == 'true'
DEMO_PATH = os.getenv('VITE_DEMO_PATH', 'tests/data/')

# Global variable to hold the agent's last response
agent_response = None
agent = None

# ==============================
# Flask app setup
# ==============================
app = Flask(__name__, static_folder='../frontend/dist', static_url_path='')
CORS(app, origins=["http://localhost:5173"])
documents = []       # Stored as relative paths

# Serve index.html at root
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# ------------------------------
# File endpoints
# ------------------------------
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

def build_index(path):
    global documents
    results = get_cached_index_only(path)
    documents = results
    set_agent_documents(results)

@app.route('/api/set-path', methods=['POST'])
def set_path():

    if not DEMO_MODE:
        return jsonify({'error': 'Not allowed in non-demo mode'}), 403

    global documents
    data = request.get_json()
    path = data.get('path')

    if not path or not os.path.isdir(path):
        return jsonify({'error': 'Invalid directory path'}), 400

    # Start the indexing in a separate thread
    index_thread = threading.Thread(target=build_index, args=(path,))
    index_thread.start()

    return jsonify({
        'status': 'Index created',
        'num_documents': len(documents),
    })

# ------------------------------
# Search endpoint
# ------------------------------
@app.route('/api/search', methods=['POST'])
def search():
    global documents

    data = request.get_json()
    query = data.get('query')
    path = data.get('path')

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

# ------------------------------
# Agent endpoints
# ------------------------------
@app.route('/api/agent/send', methods=['POST'])
def send_agent_prompt():
    global agent_response
    data = request.get_json()
    prompt = data.get('prompt')
    if not prompt:
        return jsonify({'error': 'No prompt provided'}), 400

    try:
        user_question = HumanMessage(content=prompt)
        agent_response = agent.invoke({"messages": [user_question]})

        # Extract non-empty AIMessage content (summary)
        ai_contents = [
            msg.content for msg in agent_response["messages"]
            if msg.__class__.__name__ == "AIMessage" and msg.content.strip() != ""
        ]
        agent_summary = ai_contents[0] if ai_contents else ""
    except Exception as e:
        agent_summary = {"error": str(e)}

    return jsonify({'ok': True, 'response': agent_summary})

if __name__ == '__main__':
    # Initialize agent in main
    agent = build_agent()

    # Create index before starting server
    get_cached_index_only('tests/data/')

    # if VITE_DEMO_MODE=false, build index from VITE_DEMO_PATH
    if not DEMO_MODE:
        build_index(DEMO_PATH)

    # Start Flask app
    app.run(debug=True, port=5000)
