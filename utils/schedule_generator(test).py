import sqlite3
import random
import math
import os
from collections import defaultdict

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(base_dir, 'database', 'tournament_data.db')

# Kết nối
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Lấy danh sách đội
cursor.execute("SELECT teamID, teamName, teamSchool FROM teamData")
teams_raw = cursor.fetchall()
teams = [f"{name}_{school}" for _, name, school in teams_raw]
random.shuffle(teams)

num_teams = len(teams)
min_matches_per_team = 4
total_estimated_matches = num_teams * min_matches_per_team // 4

# Làm tròn lên để chia hết cho 4
if total_estimated_matches % 4 != 0:
    total_matches = math.ceil(total_estimated_matches / 4) * 4
else:
    total_matches = total_estimated_matches

extra_matches = total_matches - total_estimated_matches
num_teams_with_5_matches = extra_matches * 4

team_match_count = {team: 4 for team in teams}
extra_teams = random.sample(teams, num_teams_with_5_matches)
for team in extra_teams:
    team_match_count[team] = 5

# === Lập lịch ===
while True:
    try:
        scheduled_matches = []
        team_occurrences = defaultdict(int)
        team_last_match_index = defaultdict(lambda: -2)
        team_matches_in_round = defaultdict(lambda: defaultdict(list))

        match_number = 1
        rounds = 4
        match_per_rounds = total_matches // rounds

        for rnd in range(1, rounds + 1):
            for i in range(match_per_rounds):
                # Tìm đội hợp lệ:
                valid_teams = []
                for team in teams:
                    # Đã đủ số trận chưa?
                    if team_occurrences[team] >= team_match_count[team]:
                        continue
                    # Tránh trận liên tiếp
                    if match_number - team_last_match_index[team] <= 1:
                        continue
                    # Tránh thi quá 2 lần trong 1 vòng
                    times_this_round = team_matches_in_round[team][rnd]
                    if len(times_this_round) >= 2:
                        continue
                    # Nếu đã có 1 trận trong vòng thì phải cách ≥ 4 trận
                    if len(times_this_round) == 1:
                        if abs(match_number - times_this_round[0]) < 4:
                            continue
                    valid_teams.append(team)

                if len(valid_teams) < 4:
                    raise ValueError("Không đủ đội hợp lệ cho trận.")

                selected = random.sample(valid_teams, 4)
                blue = selected[:2]
                red = selected[2:]

                for t in selected:
                    team_occurrences[t] += 1
                    team_last_match_index[t] = match_number
                    team_matches_in_round[t][rnd].append(match_number)

                match = {
                    'match_number': f"Q{match_number:02}",
                    'blue1': blue[0],
                    'blue2': blue[1],
                    'red1': red[0],
                    'red2': red[1],
                    'field': (match_number - 1) % 2 + 1,
                    'round': rnd
                }
                scheduled_matches.append(match)
                match_number += 1

        # Thành công
        break

    except ValueError:
        continue  # Thử lại lịch mới nếu lỗi

# === In lịch
print("Trận | Xanh 1 | Xanh 2 | Đỏ 1 | Đỏ 2 | Sân | Vòng")
for m in scheduled_matches:
    print(f"{m['match_number']} | {m['blue1']} | {m['blue2']} | {m['red1']} | {m['red2']} | {m['field']} | {m['round']}")
# Xoá dữ liệu cũ trong bảng schedule
cursor.execute("DELETE FROM schedule")

# Chèn lịch thi đấu mới vào bảng schedule
for m in scheduled_matches:
    cursor.execute("""
        INSERT INTO schedule (
            matchNumber, blueTeam1, blueTeam2, redTeam1, redTeam2, field, round
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        m['match_number'],  # Giữ nguyên dạng "Q01", "Q02", ...
        m['blue1'],
        m['blue2'],
        m['red1'],
        m['red2'],
        m['field'],
        m['round']
    ))

# Lưu thay đổi và đóng kết nối
conn.commit()
conn.close()

print("Đã cập nhật bảng schedule với lịch thi đấu mới.")