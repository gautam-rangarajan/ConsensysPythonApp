from flask import abort, Flask, jsonify, request
from flask_cors import CORS
from room import Room, User

app = Flask(__name__)
CORS(app)

@app.route('/')
def hello():
    return "Hello, World!"

@app.route('/api/createRoom')
def create_room():
    # Sample local endpoint http://127.0.0.1:5000/api/greeting?user=Gautam
    room = Room()
    return jsonify(message=f"Your room id is: {room.id}.")

@app.route('/api/createUser')
def create_user():
    room_id = request.args.get('roomId')
    user_name = request.args.get('userName')
    if room_id is None or room_id == "":
        abort(400, "Room ID is empty!")
    if user_name is None or user_name == "":
        abort(400, "User ID is empty!")
    user = Room.create_user(user_name, room_id)
    return jsonify(message=f"Hello {user_name}! \n"
                           f"You are in room {room_id}. \n"
                           f"You're user id is {user.id}.")

@app.route('/api/voteUpdate')
def vote_update():
    user_id = request.args.get('userId')
    movie_id = request.args.get('movieId')
    if user_id is None or user_id == "":
        abort(400, "User ID is empty!")
    if movie_id is None or movie_id == "":
        abort(400, "Movie ID is empty!")
    user = User.get_user_by_id(user_id)
    user.vote_for_movie(movie_id)
    return jsonify(message=user.get_movie_stack().get_top_movies_str(5))

@app.route('/api/getStack')
def get_stack():
    user_id = request.args.get('userId')
    if user_id is None or user_id == "":
        abort(400, "User ID is empty!")
    user = User.get_user_by_id(user_id)
    return jsonify(message=user.get_movie_stack().get_top_movies_str(5))



