from flask import abort, Flask, jsonify, request
from flask_cors import CORS
from room import Room, User

app = Flask(__name__)
CORS(app)

@app.route('/')
def hello():
    return "Hello, World!"

@app.route('/api/createRoom', methods=['POST'])
def create_room():
    room = Room()
    return jsonify(room_id=room.id)

@app.route('/api/createUser', methods=['POST'])
def create_user():
    data = request.get_json()
    if data is None:
        abort(400, "Invalid JSON data")

    room_id = data.get('roomId')
    user_name = data.get('userName')

    if not room_id:
        abort(400, "Room ID is empty or missing!")
    if not user_name:
        abort(400, "User name is empty or missing!")

    user = Room.create_user(user_name, room_id)
    return jsonify(user_id=user.id)

@app.route('/api/voteUpdate', methods=['POST'])
def vote_update():
    data = request.get_json()
    if data is None:
        abort(400, "Invalid JSON data")

    user_id = data.get('userId')
    movie_id = data.get('movieId')

    if not user_id:
        abort(400, "User ID is empty or missing!")
    if not movie_id:
        abort(400, "Movie ID is empty or missing!")

    user = User.get_user_by_id(user_id)
    user.vote_for_movie(movie_id)
    return jsonify(message=user.get_movie_stack().get_top_movies_str(5))

@app.route('/api/getStack')
def get_stack():
    user_id = request.args.get('userId')
    if not user_id:
        abort(400, "User ID is empty or missing!")
    user = User.get_user_by_id(user_id)
    return jsonify(top_movies=user.get_movie_stack().get_top_n_movies(5))



