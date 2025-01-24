import os
import re
import json
import random
import base64
from datetime import datetime
from flask import Flask, request, render_template_string, session, redirect, url_for
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------------------------------------
# Google Sheet 參數 (請自行調整)
# ---------------------------------------
SHEET_NAME = "Dr-Veggie-Leaderboard"   # 您的 Google Sheet 名稱
WORKSHEET_NAME = "Leaderboard"        # 工作表名稱，預設 "Leaderboard"
ENV_VAR_FOR_SERVICE_ACCOUNT = "GSPREAD_SERVICE_ACCOUNT_B64"  # 環境變數名稱

# ---------------------------------------
# 1. 取得 Google Sheet Worksheet
# ---------------------------------------
def get_gspread_client_from_env():
    """
    從環境變數載入 base64 的 service account JSON，並回傳 gspread client。
    """
    sa_base64 = os.environ.get(ENV_VAR_FOR_SERVICE_ACCOUNT, "")
    if not sa_base64:
        raise ValueError(f"找不到環境變數 {ENV_VAR_FOR_SERVICE_ACCOUNT}，請先設定！")

    # Base64 decode -> JSON -> dict
    sa_json = base64.b64decode(sa_base64).decode("utf-8")
    sa_dict = json.loads(sa_json)

    scope = [
    "https://www.googleapis.com/auth/spreadsheets",  # 訪問 Google Sheets 讀寫權限
    "https://www.googleapis.com/auth/drive"    # 訪問與應用相關的 Google Drive 文件
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_dict(sa_dict, scope)
    return gspread.authorize(creds)

def open_worksheet():
    """
    開啟指定的 Google Sheet 及工作表
    """
    client = get_gspread_client_from_env()
    spreadsheet = client.open(SHEET_NAME)
    ws = spreadsheet.worksheet(WORKSHEET_NAME)
    return ws

# ---------------------------------------
# 2. Flask App 初始化
# ---------------------------------------
app = Flask(__name__, static_url_path="/static", static_folder="static")
app.secret_key = "your_secret_key"  # 必須設定，以使用 session

# ---------------------------------------
# 3. 題目檔案路徑
# ---------------------------------------
QA_FILE_PATH = "QA.txt"  # 請確保有此檔案
if not os.path.exists(QA_FILE_PATH):
    raise FileNotFoundError(f"找不到 QA.txt：{QA_FILE_PATH}")

# ---------------------------------------
# 4. 讀取題目
# ---------------------------------------
def load_quiz_data_from_txt(file_path):
    """
    假設題目格式：
    (題號,'題目','選項1','選項2','選項3','出題者'),
    第一個選項為正解。
    """
    quiz_list = []
    pattern = re.compile(
        r'^\(\s*(\d+)\s*,\s*'          # 題號 (group1)
        r"'([^']*)'\s*,\s*"            # 題目 (group2)
        r"'([^']*)'\s*,\s*"            # 選項1 (group3) → 視為正解
        r"'([^']*)'\s*,\s*"            # 選項2 (group4)
        r"'([^']*)'\s*,\s*"            # 選項3 (group5)
        r"'([^']*)'\s*\),?"            # 出題者 (group6)
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

            # 第一個選項為正解
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

# ---------------------------------------
# 5. HTML 模板
# ---------------------------------------

home_template = """
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dr.Veggie</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  
  <style>
    body {
      background: url("{{ url_for('static', filename='images/body_all.jpg') }}") 
                  no-repeat center center fixed;
      background-size: cover;
      height: 100vh; 
      margin: 0;
      display: flex;
      justify-content: center; 
      align-items: center; 
    }
    .container {
      background-color: rgba(255, 255, 255, 0.8);
      border-radius: 8px;
      padding: 2rem;
      text-align: center;
      max-width: 500px;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Ðя▣Ṽ℮❡ℊїℯ</h1>
    <p>10 關，每關 3 題，但一次只顯示「1 題」。<br> 累計答錯 3 題立即結束。</p>
    <p>第一關 40 秒，每完成一關減 2 秒，最低 10 秒。</p>
    <form action="/start_game" method="POST" class="mb-3">
      <label>請輸入姓名 (1~10中英數):
        <input type="text"
               name="player_name"
               required
               pattern="[A-Za-z0-9一-龥]{1,10}"
               maxlength="10"
               title="1~10字，可包含中文、英文、數字">
      </label>
      <p></p>
      <button class="btn btn-primary btn-lg" type="submit">開始挑戰</button>
    </form>
    <hr>
    <a href="/ranking" class="btn btn-secondary btn-lg">排行榜</a>
  </div>
</body>
</html>
"""

challenge_template = """
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>第{{ level }}關 - 第{{ sub_q }}/3 題</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">

  <script>
    document.addEventListener("DOMContentLoaded", () => {
      const timeLimit = {{ time_limit }};
      let timeLeft = timeLimit;
      let pauseTimeLeft = localStorage.getItem("pauseTimeLeft") || 30;
      let isPaused = false;

      const progressBar = document.getElementById("progress-bar");
      const timerText = document.getElementById("timer-text");
      const pauseBtn = document.getElementById("pause-btn");
      const form = document.getElementById("challenge-form");

      const updateDisplay = () => {
        const progress = (timeLeft / timeLimit) * 100;
        progressBar.style.width = progress + "%";
        timerText.textContent = timeLeft + " 秒";
      };

      const countdown = setInterval(() => {
        if (!isPaused) {
          timeLeft -= 1;
          updateDisplay();

          if (timeLeft <= 0) {
            clearInterval(countdown);
            alert("時間到，遊戲結束！");
            form.action = "/time_up";
            form.submit();
          }
        }
      }, 1000);

      pauseBtn.addEventListener("click", () => {
        if (isPaused) {
          isPaused = false;
          pauseBtn.textContent = `暫停 (剩餘 ${pauseTimeLeft} 秒)`;
        } else if (pauseTimeLeft > 0) {
          isPaused = true;
          pauseBtn.textContent = "繼續";
          const pauseCountdown = setInterval(() => {
            if (!isPaused || pauseTimeLeft <= 0) {
              clearInterval(pauseCountdown);
              isPaused = false;
              pauseBtn.textContent = `暫停 (剩餘 ${pauseTimeLeft} 秒)`;
              if (pauseTimeLeft <= 0) {
                pauseBtn.disabled = true;
              }
            } else {
              pauseTimeLeft -= 1;
              localStorage.setItem("pauseTimeLeft", pauseTimeLeft);
              pauseBtn.textContent = `繼續 (剩餘 ${pauseTimeLeft} 秒)`;
            }
          }, 1000);
        }
      });

      updateDisplay();
    });
  </script>

  <style>
    .container {
      max-width: 600px;
      margin: auto;
      padding: 1rem;
    }
    .progress {
      height: 25px;
    }
    .form-check-label {
      display: block;
      background-color: #f8f9fa;
      border: 1px solid #dee2e6;
      padding: 1rem;
      border-radius: 0.5rem;
      margin-bottom: 0.5rem;
      cursor: pointer;
      transition: background-color 0.2s ease;
    }
    .form-check-input:checked + .form-check-label {
      background-color: #0d6efd;
      color: #fff;
    }
  </style>
</head>
<body class="bg-light">
  <div class="container">
    <h2 class="text-center">第{{ level }}關 - 第{{ sub_q }}/3 題</h2>
    <p class="text-center">玩家：{{ player_name }} | 分數：{{ score }} | 錯誤：{{ mistakes }}/3</p>
    <form id="challenge-form" method="POST" action="/submit_question" onsubmit="disableSubmit()">
      <div class="mb-3">
        <h5>{{ question_data.q }}</h5>
        {% for i in range(question_data.choices|length) %}
          <div class="form-check">
            <input class="form-check-input"
                   type="radio"
                   name="answer"
                   id="choice{{ i }}"
                   value="{{ question_data.choices[i] }}"
                   required>
            <label class="form-check-label" for="choice{{ i }}">
              {{ question_data.choices[i] }}
            </label>
          </div>
        {% endfor %}
        <p class="text-muted small mt-2 text-end">出題者：{{ question_data.author }}</p>
      </div>

      <div class="progress mb-3">
        <div id="progress-bar" 
             class="progress-bar bg-warning" 
             role="progressbar" 
             style="width: 100%;" 
             aria-valuenow="100" 
             aria-valuemin="0" 
             aria-valuemax="100">
        </div>
      </div>
      <p id="timer-text" class="text-center fw-bold">-- 秒</p>

      <div class="text-center mt-3">
        <button id="submit-btn" class="btn btn-success btn-lg" type="submit">送出答案</button>
        <br><br>
        <button type="button" id="pause-btn" class="btn btn-warning btn-lg mb-2">暫停 (最多 30 秒)</button>
      </div>
    </form>
    <script>
      function disableSubmit() {
      const submitBtn = document.getElementById("submit-btn");
      submitBtn.disabled = true;
      submitBtn.textContent = "提交中...";
        }
    </script>
  </div>
</body>
</html>
"""

result_template = """
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>結果 - 第{{ level }}關</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
  <div class="container mt-4">
    <h2>第{{ level }}關 - 答題結果</h2>
    <p>玩家：{{ player_name }}</p>
    <p>本關得分：{{ round_score }} | 累計分數：{{ total_score }} | 錯誤：{{ mistakes }}/3</p>
    <ul class="list-group">
      {% for i in range(questions|length) %}
        <li class="list-group-item">
          <strong>{{ i+1 }}. {{ questions[i].question.q }}</strong><br>
          您的答案：{{ questions[i].user_answer }}
          {% if questions[i].user_answer == questions[i].question.answer %}
            <span class="text-success">（答對）</span>
          {% else %}
            <span class="text-danger">（答錯，正解：{{ questions[i].question.answer }}）</span>
          {% endif %}
          <p class="text-muted small mt-2 text-end">出題者：{{ questions[i].question.author }}</p>
        </li>
      {% endfor %}
    </ul>

    {% if mistakes < 3 and level < 10 %}
      <div class="text-center mt-3">
        <a href="/next_level" class="btn btn-primary btn-lg">進入第{{ level + 1 }}關</a>
      </div>
    {% else %}
      <!-- 遊戲結束 -->
      <div class="text-center mt-3">
        <a href="/ranking" class="btn btn-secondary btn-lg">查看排行榜</a>
        <a href="/" class="btn btn-primary btn-lg">回首頁</a>
      </div>
    {% endif %}
  </div>
</body>
</html>
"""

ranking_template = """
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>排行榜</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
  <div class="container mt-4">
    <h2>排行榜</h2>
    <table class="table table-striped">
      <thead>
        <tr>
          <th>名次</th>
          <th>玩家</th>
          <th>分數</th>
          <th>通關數</th>
          <th>完成時間</th>
        </tr>
      </thead>
      <tbody>
        {% for player in ranking %}
        <tr>
          <td>{{ loop.index + (page - 1) * 10 }}</td>
          <td>{{ player.name }}</td>
          <td>{{ player.score }}</td>
          <td>{{ player.level }}</td>
          <td>{{ player.timestamp }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    
    <!-- 分頁導航 -->
    <nav aria-label="Page navigation">
      <ul class="pagination justify-content-center">
        <!-- 上一頁 -->
        <li class="page-item {% if page <= 1 %}disabled{% endif %}">
          <a class="page-link" href="{{ url_for('ranking', page=page-1) }}" aria-label="Previous">
            <span aria-hidden="true">&laquo;</span>
          </a>
        </li>

        <!-- 頁碼 -->
        {% for p in range(1, total_pages + 1) %}
        <li class="page-item {% if p == page %}active{% endif %}">
          <a class="page-link" href="{{ url_for('ranking', page=p) }}">{{ p }}</a>
        </li>
        {% endfor %}

        <!-- 下一頁 -->
        <li class="page-item {% if page >= total_pages %}disabled{% endif %}">
          <a class="page-link" href="{{ url_for('ranking', page=page+1) }}" aria-label="Next">
            <span aria-hidden="true">&raquo;</span>
          </a>
        </li>
      </ul>
    </nav>

    <a href="/" class="btn btn-primary btn-lg mt-3">回首頁</a>
  </div>
</body>
</html>
"""

# ---------------------------------------
# 6. Flask 路由
# ---------------------------------------

def get_time_limit(level):
    """
    第一關 40 秒，每完成一關 -2 秒，最低 10 秒
    """
    base_time = 40
    return max(base_time - (level - 1)*2, 10)

@app.route("/")
def home():
    return render_template_string(home_template)

@app.route("/start_game", methods=["POST"])
def start_game():
    player_name = request.form.get("player_name", "").strip()
    if not re.match(r'^[A-Za-z0-9一-龥]{1,10}$', player_name):
        return "<p>姓名格式錯誤。<a href='/'>返回</a></p>"

    session['player_name'] = player_name
    session['score'] = 0
    session['level'] = 1
    session['mistakes'] = 0

    # 洗牌所有題目索引
    indices = list(range(len(quiz_data)))
    random.shuffle(indices)
    session['remaining_indices'] = indices

    # 進入第一關
    return redirect(url_for('setup_level'))

@app.route("/setup_level")
def setup_level():
    """
    每關 3 題 (但只一次顯示1題)
    sub_q = 1 (第一題)
    """
    if 'player_name' not in session:
        return redirect(url_for('home'))

    level = session['level']
    mistakes = session['mistakes']
    if mistakes >= 3 or level > 10:
        return redirect(url_for('home'))

    remaining = session.get('remaining_indices', [])
    if len(remaining) < 3:
        return redirect(url_for('home'))  # 題庫不足

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

    return render_template_string(
        challenge_template,
        level=level,
        sub_q=sub_q,
        player_name=session['player_name'],
        score=score,
        mistakes=mistakes,
        question_data=question_data,
        time_limit=time_limit
    )

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

    # 若錯誤滿3 或到第10關最後一題 -> finalize
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

    return render_template_string(
        result_template,
        level=level,
        player_name=session['player_name'],
        round_score=round_score,
        total_score=total_score,
        mistakes=mistakes,
        questions=questions
    )

@app.route("/next_level")
def next_level():
    if 'player_name' not in session:
        return redirect(url_for('home'))

    session['level'] += 1
    return redirect(url_for('setup_level'))

def finalize_game():
    """
    遊戲結束時，將成績寫入 Google Sheet
    """
    # 檢查是否已經完成過
    if session.get("finalized"):
        print(f"玩家 {session['player_name']} 的成績已提交，跳過重複寫入")
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws = open_worksheet()

    # 檢查 Google Sheet 中是否已經有這位玩家的成績
    existing_records = ws.get_all_records()  # 獲取所有現有數據
    for record in existing_records:
        if record.get("玩家") == session['player_name'] and record.get("完成時間") == now_str:
            print(f"成績重複，已跳過寫入：{session['player_name']}, {now_str}")
            session["finalized"] = True  # 標記已完成
            return

    # 將玩家分數寫入 Google Sheet
    ws.append_row([
        session['player_name'],
        session['score'],
        session['level'],
        now_str
    ])

    # 標記 session 遊戲已完成，避免重複執行
    session["finalized"] = True


@app.route("/time_up")
def time_up():
    """
    時間到 -> 終止遊戲 -> 寫排行榜
    """
    if 'player_name' in session:
        finalize_game()

    # 清除 session，防止重複寫入
    session.clear()

    return """
    <html>
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>時間到</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
      <div class="container mt-5">
        <h2>時間到，遊戲結束</h2>
        <p>您的答題時間已用完，未作答。</p>
        <a href="/ranking" class="btn btn-secondary btn-lg">查看排行榜</a>
        <a href="/" class="btn btn-primary btn-lg">回首頁</a>
      </div>
    </body>
    </html>
    """

@app.route("/ranking")
def ranking():
    ws = open_worksheet()

    all_data = ws.get_all_values()
    if len(all_data) < 2:
        # 可能沒有標題列或資料
        records = []
    else:
        # 假設第一列是 ["Name", "Score", "Level", "Timestamp"]
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

    # 排序
    records.sort(key=lambda x: x["score"], reverse=True)

    # 分頁
    records_per_page = 10
    page = request.args.get("page", 1, type=int)
    total_records = len(records)
    total_pages = (total_records + records_per_page - 1) // records_per_page

    start_idx = (page - 1) * records_per_page
    end_idx = start_idx + records_per_page
    current_page_records = records[start_idx:end_idx]

    return render_template_string(
        ranking_template,
        ranking=current_page_records,
        page=page,
        total_pages=total_pages
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
