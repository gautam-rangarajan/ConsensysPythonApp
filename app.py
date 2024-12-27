from flask import abort, Flask, jsonify, request
from flask_cors import CORS
from enhanced_room import EnhancedRoom
import uuid
import numpy as np
from constants import VoteStatus

app = Flask(__name__)
CORS(app)

@app.route('/')
def hello():
    return "Hello, World!"

@app.route('/api/enhanced/createRoom', methods=['POST'])
def create_enhanced_room():
    room = EnhancedRoom()
    return jsonify(room_id=room.id)

@app.route('/api/enhanced/createUser', methods=['POST'])
def create_enhanced_user():
    data = request.get_json()
    if data is None:
        abort(400, "Invalid JSON data")

    room_id = data.get('roomId')
    user_name = data.get('userName')

    if not room_id:
        abort(400, "Room ID is empty or missing!")
    if not user_name:
        abort(400, "User name is empty or missing!")

    room = EnhancedRoom.get_room_by_id(room_id)
    if not room:
        abort(404, "Room not found")

    try:
        user_id = room.add_user(user_name)
        return jsonify(user_id=user_id)
    except ValueError as e:
        abort(400, str(e))

@app.route('/api/enhanced/getNextMovie', methods=['GET'])
def get_next_movie():
    user_id = request.args.get('userId')
    if not user_id:
        abort(400, "User ID is empty or missing!")

    # Find room containing this user
    room = next((r for r in EnhancedRoom.rooms_by_id.values() if user_id in r.users), None)
    if not room:
        abort(404, "Room not found for this user")

    try:
        movie_info = room.get_movie_to_vote(user_id)
        # Convert int64 to int
        movie_info = {k: int(v) if isinstance(v, (int, np.integer)) else v for k, v in movie_info.items()}
        return jsonify(movie_info)
    except ValueError as e:
        abort(404, str(e))

@app.route('/api/enhanced/vote', methods=['POST'])
def enhanced_vote():
    data = request.get_json()
    if data is None:
        abort(400, "Invalid JSON data")

    user_id = data.get('userId')
    movie_id = data.get('movieId')
    vote = data.get('vote')  # should be 'like' or 'dislike'

    if not user_id:
        abort(400, "User ID is empty or missing!")
    if not movie_id:
        abort(400, "Movie ID is empty or missing!")
    if vote not in ['like', 'dislike', 'not seen']:
        abort(400, "Vote must be 'like', 'dislike', or 'not seen'")

    # Find room containing this user
    room = next((r for r in EnhancedRoom.rooms_by_id.values() if user_id in r.users), None)
    if not room:
        abort(404, "Room not found for this user")

    try:
        vote_status = room.submit_vote(user_id, movie_id, vote)
        return jsonify(status=vote_status.value)
    except ValueError as e:
        abort(400, str(e))

@app.route('/api/enhanced/getRecommendations', methods=['GET'])
def get_recommendations():
    user_id = request.args.get('userId')
    if not user_id:
        abort(400, "User ID is empty or missing!")

    # Find room containing this user
    room = next((r for r in EnhancedRoom.rooms_by_id.values() if user_id in r.users), None)
    if not room:
        abort(404, "Room not found for this user")

    try:
        recommendations = room.get_recommendations()
        if recommendations["status"] == "error":
            abort(500, recommendations["message"])
        return jsonify(
            userQueues=recommendations["queues"],
            topMovies=recommendations["top_movies"],
            movieTitles=recommendations["movie_titles"]
        )
    except ValueError as e:
        abort(400, str(e))

@app.route('/api/enhanced/updateRoomConfig', methods=['POST'])
def update_room_config():
    data = request.get_json()
    if data is None:
        abort(400, "Invalid JSON data")

    room_id = data.get('roomId')
    years = data.get('years')
    genres = data.get('genres')

    if not room_id:
        abort(400, "Room ID is empty or missing!")
    if not years:
        abort(400, "Years list is empty or missing!")

    room = EnhancedRoom.get_room_by_id(room_id)
    if not room:
        abort(404, "Room not found")

    try:
        room.update_config(years=years, genres=genres)
        return jsonify({"status": "success"})
    except ValueError as e:
        abort(400, str(e))



