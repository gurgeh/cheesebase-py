from flask import Flask, jsonify, send_from_directory
app = Flask(__name__)

import db
import chess

TheDB = db.DB('testy')
TheDB.load_scores('testy')


@app.route("/fenstats/<path:fen>")
def fenstats(fen):
    b = chess.Board(fen)
    stats = TheDB.full_board_stat(b)
    return jsonify(stats)


@app.route('/')
def board():
    return app.send_static_file('board.html')


@app.route("/js/<path:path>")
def send_js(path):
    return send_from_directory('static/js', path)


@app.route("/css/<path:path>")
def send_css(path):
    return send_from_directory('static/css', path)


@app.route("/img/<path:path>")
def send_img(path):
    return send_from_directory('static/img', path)


if __name__ == "__main__":
    app.run()
