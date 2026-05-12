from flask import Flask, request, send_file, render_template_string, jsonify
import os
import tempfile
from pathlib import Path
import sys

# Add parent directory to path so we can import nexus
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from nexus import NexusCompressor
except ImportError:
    # Fallback if nexus.py not present yet
    class NexusCompressor:
        def compress(self, data):
            import lzma
            return lzma.compress(data, preset=9)
        def decompress(self, data):
            import lzma
            return lzma.decompress(data)

app = Flask(__name__)

# Simple in-memory storage (use database or Redis in production)
UPLOAD_FOLDER = tempfile.gettempdir()

@app.route('/')
def index():
    with open('index.html', 'r') as f:
        html = f.read()
    return render_template_string(html)

@app.route('/compress', methods=['POST'])
def compress():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Security: limit file size (e.g. 50MB)
    if len(file.read()) > 50 * 1024 * 1024:
        return jsonify({'error': 'File too large (max 50MB)'}), 400
    file.seek(0)
    
    original_data = file.read()
    original_name = file.filename
    
    compressor = NexusCompressor()
    compressed_data = compressor.compress(original_data)
    
    compressed_name = original_name + '.nexus'
    
    # Save to temp file for download
    temp_path = os.path.join(UPLOAD_FOLDER, compressed_name)
    with open(temp_path, 'wb') as f:
        f.write(compressed_data)
    
    return send_file(temp_path, as_attachment=True, download_name=compressed_name)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
