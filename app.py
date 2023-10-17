from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def hello():
    return "Hello, World!"

@app.route('/api/createRoom')
def api_greeting():
    # Sample local endpoint http://127.0.0.1:5000/api/greeting?user=Gautam
    user = request.args.get('user', 'User')  # 'User' is a default value
    return jsonify(message=f"Hello {user}!")