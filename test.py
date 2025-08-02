from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import time
import os
import threading
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, Column, Integer, String, Float

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'database', 'tournament_data.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

with app.app_context():
    db.create_all()

stop_flags = {
    'field-one': {"stop": False, "reset": False, "current_time": 150, "is_counting_down": False},
    'field-two': {"stop": False, "reset": False, "current_time": 150, "is_counting_down": False}
}
current_match_datas = {
    'field-one': {
        'matchNumber': 'N/A',
        'blueTeam1': 'Chưa có',
        'blueTeam2': 'Đội',
        'redTeam1': 'Chưa có',
        'redTeam2': 'Đội'
    },
    'field-two': {
        'matchNumber': 'N/A',
        'blueTeam1': 'Chưa có',
        'blueTeam2': 'Đội',
        'redTeam1': 'Chưa có',
        'redTeam2': 'Đội'
    }
}


class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    matchNumber = db.Column(db.String(10))
    blueTeam1 = db.Column(db.String(64))
    blueTeam2 = db.Column(db.String(64))
    redTeam1 = db.Column(db.String(64))
    redTeam2 = db.Column(db.String(64))
    field = db.Column(db.Integer)
    round = db.Column(db.Integer)

    def to_dict(self):
        return {
            'id': self.id,
            'matchNumber': self.matchNumber,
            'blueTeam1': self.blueTeam1,
            'blueTeam2': self.blueTeam2,
            'redTeam1': self.redTeam1,
            'redTeam2': self.redTeam2,
            'field': self.field,
            'round': self.round
        }


class Temp(db.Model):
    id = db.Column(Integer, primary_key=True)
    matchNumber = db.Column(String(10), unique=True)
    blueTeam1 = db.Column(String(64))
    blueTeam2 = db.Column(String(64))
    blueScore = db.Column(Float)
    redScore = db.Column(Float)
    redTeam1 = db.Column(String(64))
    redTeam2 = db.Column(String(64))
    scoreBlue1 = db.Column(Float)
    scoreBlue2 = db.Column(Float)
    scoreRed1 = db.Column(Float)
    scoreRed2 = db.Column(Float)
    GHBlue_Dirt = db.Column(Integer)
    GHBlue_Seed = db.Column(Integer)
    blueProductionPoints = db.Column(Integer)
    GHRed_Dirt = db.Column(Integer)
    GHRed_Seed = db.Column(Integer)
    redProductionPoints = db.Column(Integer)
    blueGarden = db.Column(Integer)
    redGarden = db.Column(Integer)
    blueHarvest = db.Column(Integer)
    redHarvest = db.Column(Integer)
    balanceCoefficient = db.Column(Float)
    redBumperCrop = db.Column(Integer)
    blueBumperCrop = db.Column(Integer)
    blueFouls = db.Column(Integer)
    redFouls = db.Column(Integer)
    blueYellowCard = db.Column(Integer)
    redYellowCard = db.Column(Integer)
    blue1RedCard = db.Column(Boolean)
    blue2RedCard = db.Column(Boolean)
    red1RedCard = db.Column(Boolean)
    red2RedCard = db.Column(Boolean)

    def __repr__(self):
        return f"<Temp match {self.matchNumber}>"

    def to_dict(self):
        return {
            'matchNumber': self.matchNumber,
            'blueTeam1': self.blueTeam1,
            'blueTeam2': self.blueTeam2,
            'blueScore': self.blueScore,
            'redScore': self.redScore,
            'redTeam1': self.redTeam1,
            'redTeam2': self.redTeam2,
            'scoreBlue1': self.scoreBlue1,
            'scoreBlue2': self.scoreBlue2,
            'scoreRed1': self.scoreRed1,
            'scoreRed2': self.scoreRed2,
            'GHBlue_Dirt': self.GHBlue_Dirt,
            'GHBlue_Seed': self.GHBlue_Seed,
            'blueProductionPoints': self.blueProductionPoints,
            'GHRed_Dirt': self.GHRed_Dirt,
            'GHRed_Seed': self.GHRed_Seed,
            'redProductionPoints': self.redProductionPoints,
            'blueGarden': self.blueGarden,
            'redGarden': self.redGarden,
            'blueHarvest': self.blueHarvest,
            'redHarvest': self.redHarvest,
            'balanceCoefficient': self.balanceCoefficient,
            'redBumperCrop': self.redBumperCrop,
            'blueBumperCrop': self.blueBumperCrop,
            'blueFouls': self.blueFouls,
            'redFouls': self.redFouls,
            'blueYellowCard': self.blueYellowCard,
            'redYellowCard': self.redYellowCard,
            'blue1RedCard': self.blue1RedCard,
            'blue2RedCard': self.blue2RedCard,
            'red1RedCard': self.red1RedCard,
            'red2RedCard': self.red2RedCard,
        }


class QualificationRanking(db.Model):
    __tablename__ = "qualificationRanking"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ranking = db.Column(db.Integer)
    teamID = db.Column(db.String(10))
    teamName = db.Column(db.String(64))
    totalMatchScore = db.Column(db.Float)
    highest1 = db.Column(db.Float)
    highest2 = db.Column(db.Float)
    totalHarvestScore = db.Column(db.Integer)
    matchesPlayed = db.Column(db.Integer)


def calculate_and_update_ranking():
    matches = Temp.query.all()
    team_stats = {}

    for match in matches:
        for team, score, harvest in [
            (match.blueTeam1, match.scoreBlue1, match.blueHarvest),
            (match.blueTeam2, match.scoreBlue2, match.blueHarvest),
            (match.redTeam1, match.scoreRed1, match.redHarvest),
            (match.redTeam2, match.scoreRed2, match.redHarvest)
        ]:
            if not team:
                continue

            if team not in team_stats:
                team_stats[team] = {
                    "scores": [],
                    "harvest": 0,
                    "matches": 0
                }

            team_stats[team]["scores"].append(score or 0)
            team_stats[team]["harvest"] += harvest or 0
            team_stats[team]["matches"] += 1

    ranking_data = []
    for team, stat in team_stats.items():
        sorted_scores = sorted(stat["scores"], reverse=True)
        total_score = sum(sorted_scores)
        highest1 = sorted_scores[0] if len(sorted_scores) >= 1 else 0
        highest2 = sorted_scores[1] if len(sorted_scores) >= 2 else 0

        ranking_data.append({
            "teamID": team,
            "teamName": team,
            "totalMatchScore": total_score,
            "highest1": highest1,
            "highest2": highest2,
            "totalHarvestScore": stat["harvest"],
            "matchesPlayed": stat["matches"]
        })

    ranking_data.sort(key=lambda x: (
        -x["totalMatchScore"],
        -x["highest1"],
        -x["highest2"],
        -x["totalHarvestScore"],
        x["teamName"]
    ))

    QualificationRanking.query.delete()
    db.session.commit()

    for idx, team in enumerate(ranking_data, 1):
        db.session.add(QualificationRanking(
            ranking=idx,
            teamID=team["teamID"],
            teamName=team["teamName"],
            totalMatchScore=team["totalMatchScore"],
            highest1=team["highest1"],
            highest2=team["highest2"],
            totalHarvestScore=team["totalHarvestScore"],
            matchesPlayed=team["matchesPlayed"]
        ))

    db.session.commit()
    socketio.emit("update_ranking", {"ranking": ranking_data})


@app.route('/save_temp', methods=['POST'])
def save_temp():
    data = request.json
    print("Received data from client (save_temp):", data)  # Debugging log
    match_number = data.get('matchNumber')
    if match_number is None:
        print("Error: Missing matchNumber in save_temp request.")  # Debugging log
        return jsonify({"success": False, "message": "Missing matchNumber"}), 400
    with app.app_context():
        match = Temp.query.filter_by(matchNumber=match_number).first()

        if not match:
            match = Temp(matchNumber=match_number)
            db.session.add(match)

        # Cập nhật các trường từ dữ liệu nhận được
        match.blueTeam1 = data.get('blueTeam1')
        match.blueTeam2 = data.get('blueTeam2')
        match.redTeam1 = data.get('redTeam1')
        match.redTeam2 = data.get('redTeam2')

        match.blueScore = data.get('blueScore')
        match.redScore = data.get('redScore')
        match.scoreBlue1 = data.get('scoreBlue1')
        match.scoreBlue2 = data.get('scoreBlue2')
        match.scoreRed1 = data.get('scoreRed1')
        match.scoreRed2 = data.get('scoreRed2')

        match.GHBlue_Dirt = data.get('GHBlue_Dirt')
        match.GHBlue_Seed = data.get('GHBlue_Seed')
        match.blueProductionPoints = data.get('blueProductionPoints')
        match.GHRed_Dirt = data.get('GHRed_Dirt')
        match.GHRed_Seed = data.get('GHRed_Seed')
        match.redProductionPoints = data.get('redProductionPoints')

        match.blueGarden = data.get('blueGarden')
        match.redGarden = data.get('redGarden')
        match.blueHarvest = data.get('blueHarvest')
        match.redHarvest = data.get('redHarvest')
        match.balanceCoefficient = data.get('balanceCoefficient')

        match.redBumperCrop = data.get('redBumperCrop')
        match.blueBumperCrop = data.get('blueBumperCrop')

        match.blueFouls = data.get('blueFouls')
        match.redFouls = data.get('redFouls')
        match.blueYellowCard = data.get('blueYellowCard')
        match.redYellowCard = data.get('redYellowCard')

        match.blue1RedCard = bool(data.get('blue1RedCard'))
        match.blue2RedCard = bool(data.get('blue2RedCard'))
        match.red1RedCard = bool(data.get('red1RedCard'))
        match.red2RedCard = bool(data.get('red2RedCard'))

        db.session.commit()
        print(f"Match {match_number} saved/updated successfully in Temp table.")  # Debugging log
        calculate_and_update_ranking()
        return jsonify({"message": "Score saved to temp successfully!", "success": True}), 200  # Added success: True


@app.route('/')
def index():
    return match_control_field('field-one')

@app.route('/match-control/<field_id>')
def match_control_field(field_id):
    with app.app_context():
        all_matches = Schedule.query.order_by(Schedule.id.asc()).all()
        if not all_matches:
            return "Không có trận đấu nào trong cơ sở dữ liệu."

        match_list = []
        for m in all_matches:
            try:
                match_num = int(m.matchNumber[1:])  # loại bỏ 'Q' nếu có
                if field_id == "field-one" and match_num % 2 == 1:  # Trận lẻ cho field-one
                    match_list.append(m)
                elif field_id == "field-two" and match_num % 2 == 0:  # Trận chẵn cho field-two
                    match_list.append(m)
            except ValueError:
                # Bỏ qua các matchNumber không đúng định dạng 'QXX'
                continue

        if not match_list:
            return f"Không có trận {'lẻ' if field_id == 'field-one' else 'chẵn'} nào trong cơ sở dữ liệu cho trường này."

        first_match_for_field = match_list[0]
        match_dicts = [m.to_dict() for m in match_list]

        # Cập nhật current_match_data cho trường cụ thể
        current_match_datas[field_id] = first_match_for_field.to_dict()

    return render_template('match_control.html',
                           match=first_match_for_field,
                           all_matches=match_dicts,
                           field_id=field_id,
                           field_number=1 if field_id == "field-one" else 2)


@app.route('/countdown/<field_id>')
def countdown_field(field_id):
    with app.app_context():
        # Lấy dữ liệu trận đấu hiện tại cho trường cụ thể
        current_match_data = current_match_datas.get(field_id)
        if current_match_data is None:
            # Khởi tạo nếu chưa có dữ liệu cho trường này
            first_match = Schedule.query.order_by(Schedule.id.asc()).first()
            if first_match:
                current_match_data = first_match.to_dict()
            else:
                current_match_data = {
                    'matchNumber': 'N/A',
                    'blueTeam1': 'Chưa có',
                    'blueTeam2': 'Đội',
                    'redTeam1': 'Chưa có',
                    'redTeam2': 'Đội'
                }
            current_match_datas[field_id] = current_match_data  # Lưu lại vào dictionary

    return render_template('field_display.html', field_id=field_id)


@app.route('/rankings')
def ranking_screen():
    return render_template('ranking_screen.html')

@app.route('/get_ranking_data')
def get_ranking_data():
    with app.app_context():
        rankings = QualificationRanking.query.order_by(QualificationRanking.ranking.asc()).all()
        result = []
        for team in rankings:
            result.append({
                "ranking": team.ranking,
                "teamID": team.teamID,
                "teamName": team.teamName,
                "totalMatchScore": team.totalMatchScore,
                "highest1": team.highest1,
                "highest2": team.highest2,
                "totalHarvestScore": team.totalHarvestScore,
                "matchesPlayed": team.matchesPlayed
            })
        return jsonify(result)

# ==================================================================================================
# Endpoint mới để hiển thị lịch thi đấu sử dụng template
# ==================================================================================================
@app.route('/schedule')
def show_schedule():
    return render_template('schedule.html')

# ==================================================================================================
# Endpoint để cung cấp dữ liệu lịch thi đấu dưới dạng JSON
# ==================================================================================================
@app.route('/get_schedule_data')
def get_schedule_data():
    with app.app_context():
        # Truy vấn tất cả các bản ghi từ bảng Schedule và sắp xếp theo id
        schedule = Schedule.query.order_by(Schedule.id.asc()).all()
        # Chuyển đổi danh sách các object thành danh sách các dictionary
        result = [match.to_dict() for match in schedule]
        return jsonify(result)

@app.route('/get_match_score_content')
def get_match_score_content():
    return render_template('match_score.html')


@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")


@socketio.on('join_room')
def on_join(data):
    field_id = data.get('field_id')
    if field_id:
        join_room(field_id)
        print(f"Client {request.sid} joined room: {field_id}")
        # Gửi dữ liệu ban đầu chỉ đến client vừa kết nối
        with app.app_context():
            current_match_data_for_field = current_match_datas.get(field_id)
            if current_match_data_for_field:
                emit('update_teams_display', {
                    'blueTeam1': current_match_data_for_field['blueTeam1'],
                    'blueTeam2': current_match_data_for_field['blueTeam2'],
                    'redTeam1': current_match_data_for_field['redTeam1'],
                    'redTeam2': current_match_data_for_field['redTeam2'],
                    'matchNumber': current_match_data_for_field['matchNumber'],
                    'field_id': field_id
                }, room=request.sid)  # Gửi chỉ đến client hiện tại
            emit('timer_update', {
                'time': f"{stop_flags[field_id]['current_time'] // 60:02}:{stop_flags[field_id]['current_time'] % 60:02}",
                'field_id': field_id
            }, room=request.sid)  # Gửi chỉ đến client hiện tại
    else:
        print(f"Client {request.sid} tried to join room without field_id.")


@socketio.on('start_match')
def handle_start_match(data):
    field_id = data.get('field_id')
    if field_id not in stop_flags:
        print(f"Error: Invalid field_id '{field_id}' for start_match.")
        return

    stop_flag = stop_flags[field_id]
    stop_flag["stop"] = False
    stop_flag["reset"] = False
    stop_flag["current_time"] = 150
    stop_flag["is_counting_down"] = True  # Đặt là True khi bắt đầu đếm ngược

    def countdown_and_start():
        for i in range(3, 0, -1):
            if stop_flag["stop"]:
                stop_flag["is_counting_down"] = False  # Đặt là False nếu dừng thủ công
                return
            socketio.emit('countdown', {'value': i, 'field_id': field_id}, room=field_id)
            time.sleep(1)
        socketio.emit('countdown', {'value': 'GO', 'field_id': field_id}, room=field_id)

        while stop_flag["current_time"] >= 0:
            if stop_flag["stop"]:
                stop_flag["is_counting_down"] = False  # Đặt là False nếu dừng thủ công
                return
            minutes = stop_flag["current_time"] // 60
            seconds = stop_flag["current_time"] % 60
            timer_str = f"{minutes:02}:{seconds:02}"
            socketio.emit('timer_update', {'time': timer_str, 'field_id': field_id}, room=field_id)
            time.sleep(1)
            stop_flag["current_time"] -= 1

        # Khi đếm ngược kết thúc, đặt lại cờ
        stop_flag["is_counting_down"] = False  # Đặt là False khi đếm ngược kết thúc
        if not stop_flag["reset"]:
            socketio.emit('timer_finished', {'field_id': field_id})
            print(f"Countdown for {field_id} finished.")
        stop_flag["stop"] = True  # Đảm bảo dừng lại sau khi kết thúc

    threading.Thread(target=countdown_and_start).start()


@socketio.on('stop_match')
def handle_stop_match(data):
    field_id = data.get('field_id')
    if field_id not in stop_flags:
        print(f"Error: Invalid field_id '{field_id}' for stop_match.")
        return
    stop_flags[field_id]["stop"] = True
    stop_flags[field_id]["is_counting_down"] = False  # Đặt là False nếu dừng thủ công


@socketio.on('reset_match')
def handle_reset(data):
    field_id = data.get('field_id')
    if field_id not in stop_flags:
        print(f"Error: Invalid field_id '{field_id}' for reset_match.")
        return
    stop_flags[field_id]["stop"] = True
    stop_flags[field_id]["current_time"] = 150
    stop_flags[field_id]["is_counting_down"] = False  # Đặt là False khi reset
    socketio.emit('timer_update', {'time': "02:30", 'field_id': field_id}, room=field_id)
    socketio.emit('reset_done', {'field_id': field_id}, room=field_id)


@socketio.on('change_match')
def handle_change_match(data):
    field_id = data.get('field_id')
    match_number = data['matchNumber']
    if field_id not in current_match_datas:
        print(f"Error: Invalid field_id '{field_id}' for change_match.")
        return

    with app.app_context():
        match = Schedule.query.filter_by(matchNumber=match_number).first()
        if match:
            current_match_datas[field_id] = match.to_dict()
            # CHỈ đẩy dữ liệu nếu countdown KHÔNG hoạt động
            if not stop_flags[field_id]["is_counting_down"]:
                print(f"Updating display for {field_id} with match {match_number} (countdown not active)")
                socketio.emit('update_teams_display', {
                    'blueTeam1': match.blueTeam1,
                    'blueTeam2': match.blueTeam2,
                    'redTeam1': match.redTeam1,
                    'redTeam2': match.redTeam2,
                    'matchNumber': match.matchNumber,
                    'field_id': field_id
                }, room=field_id)
            else:
                print(f"Countdown active for {field_id}. Not updating display for match {match_number}.")


@socketio.on('request_initial_match_data')
def handle_request_initial_match_data(data):
    # Lệnh này không còn cần thiết vì on_join đã gửi dữ liệu ban đầu
    pass


@socketio.on('show_score_request')
def handle_show_score_request(data):
    print("Received show_score_request:", data)  # Debugging log
    match_number_to_show = data.get('matchNumber')
    field_id = data.get('field_id')

    print(f"show_score_request - match_number: {match_number_to_show}, field_id: {field_id}")  # Debugging log

    if not match_number_to_show or not field_id:
        print("Error: matchNumber or field_id not provided in show_score_request.")  # Debugging log
        emit('error_message', {'message': 'Không tìm thấy số trận đấu hoặc ID trường để hiển thị điểm.'})
        return
    if field_id not in current_match_datas:
        print(f"Error: Invalid field_id '{field_id}' for show_score_request.")  # Debugging log
        return

    with app.app_context():
        score_data = Temp.query.filter_by(matchNumber=match_number_to_show).first()
        if score_data:
            print(f"Found score data for match {match_number_to_show} in Temp table.")  # Debugging log
            full_data = score_data.to_dict()
            schedule_match = Schedule.query.filter_by(matchNumber=match_number_to_show).first()
            if schedule_match:
                full_data['blueTeam1'] = schedule_match.blueTeam1
                full_data['blueTeam2'] = schedule_match.blueTeam2
                full_data['redTeam1'] = schedule_match.redTeam1
                full_data['redTeam2'] = schedule_match.redTeam2

            # THÊM field_id VÀO full_data TRƯỚC KHI GỬI
            full_data['field_id'] = field_id

            socketio.emit('show_score_data', full_data, room=field_id)
            print(f"Emitted show_score_data for match {match_number_to_show} to field {field_id}")  # Debugging log
        else:
            print(
                f"No score data found for match {match_number_to_show} in Temp table for field {field_id}. Emitting error message.")  # Debugging log
            socketio.emit('error_message',
                          {'message': f"Không tìm thấy điểm số cho trận {match_number_to_show}.", 'field_id': field_id},
                          room=field_id)  # Added field_id to error message


@socketio.on('hide_score_request')
def handle_hide_score_request(data):
    field_id = data.get('field_id')
    if not field_id:
        print("Error: field_id not provided in hide_score_request.")
        return
    if field_id not in current_match_datas:
        print(f"Error: Invalid field_id '{field_id}' for hide_score_request.")
        return

    print(f"Received hide_score_request for field {field_id}.")
    socketio.emit('hide_score_data', {'field_id': field_id}, room=field_id)


if __name__ == '__main__':
    with app.app_context():
        # Khởi tạo current_match_datas cho cả hai trường khi ứng dụng bắt đầu
        first_match_on_startup = Schedule.query.order_by(Schedule.id.asc()).first()
        if first_match_on_startup:
            # Gán cùng một trận đầu tiên cho cả hai trường nếu không có dữ liệu cụ thể
            current_match_datas['field-one'] = first_match_on_startup.to_dict()
            current_match_datas['field-two'] = first_match_on_startup.to_dict()
        else:
            # Khởi tạo mặc định nếu không có trận đấu nào
            default_data = {
                'matchNumber': 'N/A',
                'blueTeam1': 'Chưa có',
                'blueTeam2': 'Đội',
                'redTeam1': 'Chưa có',
                'redTeam2': 'Đội'
            }
            current_match_datas['field-one'] = default_data
            current_match_datas['field-two'] = default_data

    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
