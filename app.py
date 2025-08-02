from flask import Flask, render_template, request, send_from_directory, jsonify
from flask_socketio import SocketIO, emit
import time
import threading
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Cấu hình SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tournament_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

countdown_interval = None
time_left = 150
current_match_index = 0

STATICS_FOLDER = 'static'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp3'}

app.config['STATICS_FOLDER'] = STATICS_FOLDER

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def countdown():
    global time_left
    while time_left > 0:
        time.sleep(1)
        time_left -= 1
        socketio.emit('countdown', time_left)
    global countdown_interval
    countdown_interval = None
    socketio.emit('countdown', time_left)

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_number = db.Column(db.Integer)
    red_team1 = db.Column(db.String(50))
    red_team2 = db.Column(db.String(50))
    blue_team1 = db.Column(db.String(50))
    blue_team2 = db.Column(db.String(50))
    red_total_score = db.Column(db.Integer)
    blue_total_score = db.Column(db.Integer)
    red_mission1 = db.Column(db.Integer)
    red_mission2 = db.Column(db.Integer)
    red_mission3 = db.Column(db.Integer)
    red_fouls = db.Column(db.Integer)
    blue_mission1 = db.Column(db.Integer)
    blue_mission2 = db.Column(db.Integer)
    blue_mission3 = db.Column(db.Integer)
    blue_fouls = db.Column(db.Integer)

    def __repr__(self):
        return f"<Match {self.match_number}>"

# Định nghĩa model Schedule
class Schedule(db.Model):
    __tablename__ = 'schedule'
    id = db.Column(db.Integer, primary_key=True)
    match_number = db.Column(db.Integer)
    red_team1 = db.Column(db.String(50))
    red_team2 = db.Column(db.String(50))
    blue_team1 = db.Column(db.String(50))
    blue_team2 = db.Column(db.String(50))

    def __repr__(self):
        return f'<Schedule {self.id}>'

class Ranking(db.Model):
    __tablename__ = 'ranking'  # Tên bảng trong database

    id = db.Column(db.Integer, primary_key=True)
    teamscore = db.Column(db.Integer)
    score_mission1 = db.Column(db.Integer)
    score_mission2 = db.Column(db.Integer)
    score_mission3 = db.Column(db.Integer)
    team_name = db.Column(db.String(50))
    ranking = db.Column(db.Integer)

    def __repr__(self):
        return f"<Ranking {self.team_name}>"



@app.route('/save_match', methods=['POST'])
def save_match():
    data = request.get_json()  # Lấy dữ liệu JSON từ request
    new_match = Match(         # Tạo một instance mới của Model Match
        match_number=data['matchNumber'],
        red_team1=data['redTeam1'],
        red_team2=data['redTeam2'],
        blue_team1=data['blueTeam1'],
        blue_team2=data['blueTeam2'],
        red_total_score=data['redTotalScore'],
        blue_total_score=data['blueTotalScore'],
        red_mission1=data['redMission1'],
        red_mission2=data['redMission2'],
        red_mission3=data['redMission3'],
        red_fouls=data['redFoulsPoint'],
        blue_mission1=data['blueMission1'],
        blue_mission2=data['blueMission2'],
        blue_mission3=data['blueMission3'],
        blue_fouls=data['blueFoulsPoint']
    )
    db.session.add(new_match)  # Thêm instance vào session
    db.session.commit()       # Lưu các thay đổi vào cơ sở dữ liệu
    return jsonify({'message': 'Match data saved successfully!'}), 200  # Trả về JSON

@app.route('/')
def index():
    return render_template('match_control.html')

@app.route('/countdown')
def countdown_page():
    return render_template('countdownscreen.html')

@socketio.on('connect')
def handle_connect():
    print('Client connected:', request.sid)
    emit('countdown', time_left)
    send_schedule_data()

@socketio.on('start-countdown')
def handle_start_countdown():
    global countdown_interval, time_left
    if countdown_interval is None:
        time_left = 153
        countdown_interval = threading.Thread(target=countdown)
        countdown_interval.start()

@socketio.on('get_match_data')  # Đổi tên event
def handle_get_match_data():  # Đổi tên hàm
    """Xử lý sự kiện 'get_match_data' từ client và gửi dữ liệu trận đấu."""
    send_schedule_data()

def send_schedule_data():
    """Lấy dữ liệu trận đấu từ bảng schedule và gửi cho client."""
    global current_match_index
    try:
        # Lấy tất cả các trận đấu từ bảng schedule, sắp xếp theo match_number
        all_schedules = Schedule.query.order_by(Schedule.match_number).all()
        # In ra số lượng trận đấu lấy được
        print(f"Số lượng trận đấu lấy từ bảng schedule: {len(all_schedules)}")
        if all_schedules:
            # Chuyển đổi các đối tượng Schedule thành list các dictionary
            schedule_list = []
            for schedule in all_schedules:
                schedule_list.append({
                    'id': schedule.id,
                    'match_number': schedule.match_number,
                    'red_team1': schedule.red_team1,
                    'red_team2': schedule.red_team2,
                    'blue_team1': schedule.blue_team1,
                    'blue_team2': schedule.blue_team2
                })
            socketio.emit('send_match_data', {'data': schedule_list})
        else:
            socketio.emit('send_match_data', {'data': []})
    except Exception as e:
        print(f"Lỗi khi truy vấn database: {e}")
        socketio.emit('send_match_data', {'data': []})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['STATICS_FOLDER'], filename)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='10.30.44.130',port=5000, allow_unsafe_werkzeug=True)

