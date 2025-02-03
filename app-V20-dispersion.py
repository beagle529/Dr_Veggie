import os
import re
import json
import random
import base64
from datetime import datetime
from flask import Flask, request, render_template, session, redirect, url_for
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------------------------------------
# Google Sheet 參數 (請自行調整)
# ---------------------------------------
SHEET_NAME = "Dr-Veggie-Leaderboard"   # 您的 Google Sheet 名稱
WORKSHEET_NAME = "Leaderboard"         # 工作表名稱
ENV_VAR_FOR_SERVICE_ACCOUNT = "GSPREAD_SERVICE_ACCOUNT_B64"  # 環境變數名稱

def get_gspread_client_from_env():
    sa_base64 = os.environ.get(ENV_VAR_FOR_SERVICE_ACCOUNT, "")
    if not sa_base64:
        raise ValueError(f"找不到環境變數 {ENV_VAR_FOR_SERVICE_ACCOUNT}，請先設定！")
    sa_json = base64.b64decode(sa_base64).decode("utf-8")
    sa_dict = json.loads(sa_json)
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(sa_dict, scope)
    return gspread.authorize(creds)

def open_worksheet():
    client = get_gspread_client_from_env()
    spreadsheet = client.open(SHEET_NAME)
    ws = spreadsheet.worksheet(WORKSHEET_NAME)
    return ws

# ---------------------------------------
# Flask App 初始化
# ---------------------------------------
app = Flask(__name__, static_url_path="/static", static_folder="static")
app.secret_key = "your_secret_key"  # 請替換成安全的金鑰

# ---------------------------------------
# 讀取題目資料 (假設檔案 QA.txt 與特定格式)
# ---------------------------------------
QA_FILE_PATH = "QA.txt"
if not os.path.exists(QA_FILE_PATH):
    raise FileNotFoundError(f"找不到 QA.txt：{QA_FILE_PATH}")

def load_quiz_data_from_txt(file_path):
    quiz_list = []
    pattern = re.compile(
        r'^\(\s*(\d+)\s*,\s*'
        r"'([^']*)'\s*,\s*"
        r"'([^']*)'\s*,\s*"
        r"'([^']*)'\s*,\s*"
        r"'([^']*)'\s*,\s*"
        r"'([^']*)'\s*\),?"
    )
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            match = pattern.match(line)
            if not match:
                raise ValueError(f"行格式不符：{line}")
            question_text = match.group(2)
            choices = [match.group(3), match.group(4), match.group(5)]
            author = match.group(6)
            correct_answer = match.group(3)
            random.shuffle(choices)
            quiz_list.append({
                "q": question_text,
                "choices": choices,
                "answer": correct_answer,
                "author": author
            })
    return quiz_list

quiz_data = load_quiz_data_from_txt(QA_FILE_PATH)

def get_time_limit(level):
    base_time = 40
    return max(base_time - (level - 1) * 2, 10)

# ---------------------------------------
# Flask 路由定義 (使用 render_template 載入模板檔案)
# ---------------------------------------

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/start_game", methods=["POST"])
def start_game():
    player_name = request.form.get("player_name", "").strip()
    if not re.match(r'^[A-Za-z0-9一-龥]{1,10}$', player_name):
        return "<p>姓名格式錯誤。<a href='/'>返回</a></p>"
    session['player_name'] = player_name
    session['score'] = 0
    session['level'] = 1
    session['mistakes'] = 0
    indices = list(range(len(quiz_data)))
    random.shuffle(indices)
    session['remaining_indices'] = indices
    return redirect(url_for('setup_level'))

@app.route("/setup_level")
def setup_level():
    if 'player_name' not in session:
        return redirect(url_for('home'))
    level = session['level']
    mistakes = session['mistakes']
    if mistakes >= 3 or level > 10:
        return redirect(url_for('home'))
    remaining = session.get('remaining_indices', [])
    if len(remaining) < 3:
        return redirect(url_for('home'))
    current_questions = remaining[:3]
    session['current_questions'] = current_questions
    session['remaining_indices'] = remaining[3:]
    session['sub_q'] = 1
    session['level_user_answers'] = [None, None, None]
    return redirect(url_for('show_question'))

@app.route("/show_question")
def show_question():
    if 'player_name' not in session:
        return redirect(url_for('home'))
    level = session['level']
    sub_q = session['sub_q']
    mistakes = session['mistakes']
    score = session['score']
    current_questions = session.get('current_questions', [])
    if mistakes >= 3 or level > 10:
        return redirect(url_for('home'))
    if not (1 <= sub_q <= 3):
        return redirect(url_for('home'))
    qidx = current_questions[sub_q - 1]
    question_data = quiz_data[qidx]
    time_limit = get_time_limit(level)
    return render_template("challenge.html",
                           level=level,
                           sub_q=sub_q,
                           player_name=session['player_name'],
                           score=score,
                           mistakes=mistakes,
                           question_data=question_data,
                           time_limit=time_limit)

@app.route("/submit_question", methods=["POST"])
def submit_question():
    if 'player_name' not in session:
        return redirect(url_for('home'))
    level = session['level']
    sub_q = session['sub_q']
    mistakes = session['mistakes']
    score = session['score']
    current_questions = session.get('current_questions', [])
    level_user_answers = session.get('level_user_answers', [])
    user_answer = request.form.get("answer", "")
    qidx = current_questions[sub_q - 1]
    correct_answer = quiz_data[qidx]["answer"]
    if user_answer == correct_answer:
        score += 1
    else:
        mistakes += 1
    level_user_answers[sub_q - 1] = user_answer
    session['score'] = score
    session['mistakes'] = mistakes
    session['level_user_answers'] = level_user_answers
    if mistakes >= 3 or (level == 10 and sub_q == 3):
        finalize_game()
        return redirect(url_for('show_level_result'))
    if sub_q < 3:
        session['sub_q'] = sub_q + 1
        return redirect(url_for('show_question'))
    else:
        return redirect(url_for('show_level_result'))

@app.route("/show_level_result")
def show_level_result():
    if 'player_name' not in session:
        return redirect(url_for('home'))
    level = session['level']
    mistakes = session['mistakes']
    total_score = session['score']
    current_questions = session.get('current_questions', [])
    level_user_answers = session.get('level_user_answers', [])
    round_score = 0
    questions = []
    for i, qidx in enumerate(current_questions):
        qdata = quiz_data[qidx]
        user_ans = level_user_answers[i]
        if user_ans == qdata["answer"]:
            round_score += 1
        questions.append({
            "question": qdata,
            "user_answer": user_ans
        })
    return render_template("result.html",
                           level=level,
                           player_name=session['player_name'],
                           round_score=round_score,
                           total_score=total_score,
                           mistakes=mistakes,
                           questions=questions)

@app.route("/next_level")
def next_level():
    if 'player_name' not in session:
        return redirect(url_for('home'))
    session['level'] += 1
    return redirect(url_for('setup_level'))

def finalize_game():
    if session.get("finalized"):
        print(f"玩家 {session['player_name']} 的成績已提交，跳過重複寫入")
        return
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws = open_worksheet()
    existing_records = ws.get_all_records()
    for record in existing_records:
        if record.get("玩家") == session['player_name'] and record.get("完成時間") == now_str:
            print(f"成績重複，已跳過寫入：{session['player_name']}, {now_str}")
            session["finalized"] = True
            return
    ws.append_row([
        session['player_name'],
        session['score'],
        session['level'],
        now_str
    ])
    session["finalized"] = True

@app.route("/time_up")
def time_up():
    if 'player_name' in session:
        finalize_game()
    session.clear()
    return render_template("time_up.html")

@app.route("/ranking")
def ranking():
    ws = open_worksheet()
    all_data = ws.get_all_values()
    if len(all_data) < 2:
        records = []
    else:
        data_rows = all_data[1:]
        records = []
        for row in data_rows:
            if len(row) < 4:
                continue
            name = row[0]
            try:
                score = int(row[1])
            except:
                score = 0
            try:
                level = int(row[2])
            except:
                level = 0
            timestamp = row[3]
            records.append({
                "name": name,
                "score": score,
                "level": level,
                "timestamp": timestamp
            })
    records.sort(key=lambda x: x["score"], reverse=True)
    records_per_page = 10
    page = request.args.get("page", 1, type=int)
    total_records = len(records)
    total_pages = (total_records + records_per_page - 1) // records_per_page
    start_idx = (page - 1) * records_per_page
    end_idx = start_idx + records_per_page
    current_page_records = records[start_idx:end_idx]
    return render_template("ranking.html",
                           ranking=current_page_records,
                           page=page,
                           total_pages=total_pages)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
