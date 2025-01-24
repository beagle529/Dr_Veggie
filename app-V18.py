import os
import re
import json
import random
from datetime import datetime
from flask import Flask, request, render_template_string, session, redirect, url_for

app = Flask(__name__, static_url_path="/static", static_folder="static")
app.secret_key = "your_secret_key"  # 必須設定，以使用 session

# ------------------------------
# 1. 檔案路徑設定
# ------------------------------
QA_FILE_PATH = "QA.txt"       # 題目檔案路徑
LEADERBOARD_FILE_PATH = "leaderboard.json"  # 排行榜檔案路徑

# ------------------------------
# 2. 排行榜存取函式
# ------------------------------
def load_leaderboard(file_path):
    """從 JSON 檔案中讀取排行榜資料"""
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_leaderboard(file_path, data):
    """將排行榜資料以 JSON 格式寫回檔案"""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 初始化全域排行榜（程式啟動時讀取一次）
leaderboard = load_leaderboard(LEADERBOARD_FILE_PATH)

# ------------------------------
# 3. 載入題目
# ------------------------------
def load_quiz_data_from_txt(file_path):
    """
    讀取單行格式 QA.txt，假設：
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
                continue  # 跳過空白行
            match = pattern.match(line)
            if not match:
                raise ValueError(f"行格式不符：{line}")

            question_text = match.group(2)
            choices = [match.group(3), match.group(4), match.group(5)]
            author = match.group(6)

            # 保留正解，再打亂選項
            correct_answer = match.group(3)
            random.shuffle(choices)

            quiz_list.append({
                "q": question_text,
                "choices": choices,
                "answer": correct_answer,
                "author": author
            })
    return quiz_list

if not os.path.exists(QA_FILE_PATH):
    raise FileNotFoundError(f"找不到 QA.txt：{QA_FILE_PATH}")

quiz_data = load_quiz_data_from_txt(QA_FILE_PATH)

# ------------------------------
# 4. HTML 模板
# ------------------------------

# 首頁
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

# 單題顯示頁
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
    <form id="challenge-form" method="POST" action="/submit_question">
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
        <button class="btn btn-success btn-lg" type="submit">送出答案</button>
        <br><br>
        <button type="button" id="pause-btn" class="btn btn-warning btn-lg mb-2">暫停 (最多 30 秒)</button>
      </div>
    </form>
  </div>
</body>
</html>
"""

# 本關結果（顯示 3 題答題情況）
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

# 排行榜
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

# ------------------------------
# 5. Flask 路由
# ------------------------------

def get_time_limit(level):
    """第一關 40 秒，每完成一關減 2 秒，最少 10 秒。"""
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

    # 初始化
    session['player_name'] = player_name
    session['score'] = 0
    session['level'] = 1
    session['mistakes'] = 0

    # 抽題所需的索引洗牌
    indices = list(range(len(quiz_data)))
    random.shuffle(indices)
    session['remaining_indices'] = indices

    # 進入第一關
    return redirect(url_for('setup_level'))

@app.route("/setup_level")
def setup_level():
    """
    在進入新關卡時：抽 3 題，sub_q=1
    """
    if 'player_name' not in session:
        return redirect(url_for('home'))

    level = session['level']
    mistakes = session['mistakes']

    # 結束判斷
    if mistakes >= 3 or level > 10:
        return redirect(url_for('home'))

    remaining = session.get('remaining_indices', [])
    if len(remaining) < 3:
        # 題庫不足 -> 提早結束
        return redirect(url_for('home'))

    # 抽 3 題
    current_questions = remaining[:3]
    session['current_questions'] = current_questions
    session['remaining_indices'] = remaining[3:]
    
    # 重設此關答題記錄
    session['sub_q'] = 1
    session['level_user_answers'] = [None, None, None]

    return redirect(url_for('show_question'))

@app.route("/show_question")
def show_question():
    """
    顯示本關當前 sub_q 的題目
    """
    if 'player_name' not in session:
        return redirect(url_for('home'))

    level = session['level']
    sub_q = session['sub_q']
    mistakes = session['mistakes']
    score = session['score']
    current_questions = session.get('current_questions', [])

    # 防呆檢查
    if mistakes >= 3 or level > 10:
        return redirect(url_for('home'))
    if not (1 <= sub_q <= 3):
        return redirect(url_for('home'))

    # 當前題目的索引
    qidx = current_questions[sub_q - 1]
    question_data = quiz_data[qidx]

    # 計算限時
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
    """
    接收單題作答，判斷對錯後：
    - 若錯誤滿3 或 已到第10關 -> finalize_game()
    - 否則繼續下一題或下一關
    """
    if 'player_name' not in session:
        return redirect(url_for('home'))

    level = session['level']
    sub_q = session['sub_q']
    mistakes = session['mistakes']
    score = session['score']
    current_questions = session.get('current_questions', [])
    level_user_answers = session.get('level_user_answers', [])

    # 取出答案
    user_answer = request.form.get("answer", "")
    qidx = current_questions[sub_q - 1]
    correct_answer = quiz_data[qidx]["answer"]

    # 判斷對錯
    if user_answer == correct_answer:
        score += 1
    else:
        mistakes += 1

    # 暫存
    level_user_answers[sub_q - 1] = user_answer

    # 更新 session
    session['score'] = score
    session['mistakes'] = mistakes
    session['level_user_answers'] = level_user_answers

    # 結束條件：錯誤 >= 3 或 level == 10 (且現在正答到最後一題?)
    # 不一定要檢查 sub_q==3，因為就算在第一題就錯到 3 也要結束
    if mistakes >= 3 or (level == 10 and sub_q == 3):
        finalize_game()  # 只呼叫這一次
        return redirect(url_for('show_level_result'))

    # 還沒 3 題，就 sub_q+1
    if sub_q < 3:
        session['score'] = score
        session['mistakes'] = mistakes
        session['sub_q'] = sub_q + 1
        return redirect(url_for('show_question'))
    else:
        # 已作答 3 題 -> 進入結果
        return redirect(url_for('show_level_result'))

@app.route("/show_level_result")
def show_level_result():
    """
    顯示本關 3 題情況。
    這裡不再呼叫 finalize_game()，避免重複寫入。
    """
    if 'player_name' not in session:
        return redirect(url_for('home'))

    level = session['level']
    mistakes = session['mistakes']
    total_score = session['score']
    current_questions = session.get('current_questions', [])
    level_user_answers = session.get('level_user_answers', [])

    # 計算本關得分
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
    """
    進入下一關
    """
    if 'player_name' not in session:
        return redirect(url_for('home'))
    session['level'] += 1
    return redirect(url_for('setup_level'))

def finalize_game():
    """
    遊戲結束時，記錄到排行榜（只呼叫一次）
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    leaderboard.append({
        "name": session['player_name'],
        "score": session['score'],
        "level": session['level'],
        "timestamp": now_str
    })
    leaderboard.sort(key=lambda x: x['score'], reverse=True)
    save_leaderboard(LEADERBOARD_FILE_PATH, leaderboard)

@app.route("/time_up")
def time_up():
    """
    時間到 -> 終止遊戲 -> 寫排行。
    """
    if 'player_name' in session:
        finalize_game()
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
    # 每頁顯示 10 筆
    records_per_page = 10
    page = request.args.get("page", 1, type=int)

    total_records = len(leaderboard)
    total_pages = (total_records + records_per_page - 1) // records_per_page

    start_index = (page - 1) * records_per_page
    end_index = start_index + records_per_page
    current_page_records = leaderboard[start_index:end_index]

    return render_template_string(
        ranking_template,
        ranking=current_page_records,
        page=page,
        total_pages=total_pages
    )

# ------------------------------
# 6. 主程式啟動
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
