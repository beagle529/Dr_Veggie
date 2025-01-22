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
    import re
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

            # 隨機排序選項
            random.shuffle(choices)

            quiz_list.append({
                "q": question_text,
                "choices": choices,
                "answer": match.group(3),  # 第一個選項為正解
                "image": author           # 出題者
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
  <title>Dr.Veggie</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  
<style>
    body {
      background: url("{{ url_for('static', filename='images/body_all.jpg') }}") 
                  no-repeat center center fixed;
      background-size: cover;
      height: 100vh; /* 設置視窗高度填滿 */
      margin: 0;
      display: flex; /* 啟用 Flexbox 布局 */
      justify-content: center; /* 水平置中 */
      align-items: center; /* 垂直置中 */
    }
    .container {
      background-color: rgba(255, 255, 255, 0.8); /* 半透明白色背景 */
      border-radius: 8px;
      padding: 2rem;
      text-align: center;
      max-width: 500px;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); /* 添加陰影提升層次 */
    }
</style>
</head>
<body>
  <div class="container">
    <h1>Ðя▣Ṽ℮❡ℊїℯ</h1>
    <p>每關 3 題，共 10 關，累計錯 3 題即中止遊戲。</p>
    <p>第一關限時40秒，每關減少2秒，超過時間即中止遊戲。</p>
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

# 闖關頁（在進入新遊戲時，會偵測並移除 localStorage 的 pauseTimeLeft）
challenge_template = """
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <title>第{{ level }}關</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  
  <script>
  document.addEventListener("DOMContentLoaded", () => {
    // 若 URL 傳參數 reset_pause=1，表示新玩家開始，需要重置暫停秒數
    let urlParams = new URLSearchParams(window.location.search);
    let resetPause = urlParams.get("reset_pause");
    if (resetPause === "1") {
      localStorage.removeItem("pauseTimeLeft");
    }

    // -- 1. 取得本關題目秒數 --
    const timeLimit = {{ time_limit }}; // 從後端傳遞的本關時間（秒）

    // -- 2. 讀/寫 localStorage 暫停時間 --
    //    如果尚未存過 pauseTimeLeft，就預設為 30
    //    若使用部分暫停後，下次載入需繼續扣除後的值
    let pauseTimeLeft = localStorage.getItem("pauseTimeLeft");
    if (!pauseTimeLeft) {
      pauseTimeLeft = 30; // 最多可暫停的總秒數
      localStorage.setItem("pauseTimeLeft", pauseTimeLeft);
    } else {
      pauseTimeLeft = parseInt(pauseTimeLeft, 10);
    }

    // -- 3. 控制倒數計時 + 暫停 --
    let timeLeft = timeLimit;    // 本關剩餘答題秒數
    let isPaused = false;        // 是否正在暫停
    let pauseInterval = null;    // 計算「暫停秒數」的 interval
    let mainInterval = null;     // 計算「題目倒數」的 interval

    const progressBar = document.getElementById("progress-bar");
    const timerText = document.getElementById("timer-text");
    const pauseBtn = document.getElementById("pause-btn");
    const form = document.getElementById("challenge-form");

    // 若已經沒有可用的暫停秒數，就關閉按鈕
    if (pauseTimeLeft <= 0) {
      pauseBtn.disabled = true;
      pauseBtn.innerText = "暫停不可用(0)";
    }

    // 每秒更新題目倒數
    function startMainCountdown() {
      mainInterval = setInterval(() => {
        if (!isPaused) {
          timeLeft -= 1;
          updateDisplay();
          if (timeLeft <= 0) {
            // 題目時間用完 => 不作答、直接結束
            clearInterval(mainInterval);
            alert("時間到，遊戲結束！");
            window.location.href = "/time_up"; 
          }
        }
      }, 1000);
    }

    // 每秒更新進度條/顯示
    function updateDisplay() {
      const progress = (timeLeft / timeLimit) * 100;
      progressBar.style.width = progress + "%";
      timerText.textContent = timeLeft + " 秒";
    }

    // 切換暫停的函式
    function togglePause() {
      if (!isPaused) {
        // 進入暫停狀態
        if (pauseTimeLeft > 0) {
          isPaused = true;
          pauseBtn.innerText = "繼續";
          // 啟動暫停倒數
          pauseInterval = setInterval(() => {
            pauseTimeLeft -= 1;
            if (pauseTimeLeft <= 0) {
              // 暫停秒數用盡，強制恢復倒數
              pauseTimeLeft = 0;
              stopPause();
            }
            // 同步回 localStorage
            localStorage.setItem("pauseTimeLeft", pauseTimeLeft);
            pauseBtn.innerText = "繼續(剩餘 " + pauseTimeLeft + " 秒)";
          }, 1000);
        }
      } else {
        // 解除暫停
        stopPause();
      }
    }

    // 解除暫停的細節
    function stopPause() {
      isPaused = false;
      pauseBtn.innerText = (pauseTimeLeft > 0) 
          ? "暫停(剩餘 " + pauseTimeLeft + " 秒)" 
          : "暫停不可用(0)";
      clearInterval(pauseInterval);
      pauseInterval = null;
      if (pauseTimeLeft <= 0) {
        // 沒有剩餘暫停秒數 => disable 按鈕
        pauseBtn.disabled = true;
      }
    }

    // 首次畫面更新
    updateDisplay();
    // 啟動題目倒數
    startMainCountdown();

    // 綁定按鈕事件
    pauseBtn.addEventListener("click", togglePause);
  });
  </script>
  <style>
    .card-img-top {
      height: 120px; 
      object-fit: cover;
    }
  </style>
</head>
<body class="bg-light">
  <div class="container mt-4">
    <h2>第{{ level }}關</h2>
    <p>玩家：{{ player_name }} | 累計分數：{{ score }} | 累計錯誤：{{ mistakes }}/3</p>
    <form id="challenge-form" method="POST" action="/submit">
      <div class="row g-4">
        {% for i in range(question_indices|length) %}
          {% set qidx = question_indices[i] %}
          {% set question = quiz_data[qidx] %}
          <div class="col-md-4">
            <div class="card">
              <img 
                src="{{ url_for('static', filename='images/banner.gif') }}"
                class="card-img-top" 
                alt="Author"
                style="width: 100%; height: auto;">
              <div class="card-body">
                <h5>{{ i+1 }}. {{ question.q }}</h5>
                {% for c in range(question.choices|length) %}
                  <div class="form-check">
                    <input class="form-check-input" type="radio"
                           id="q{{ i }}c{{ c }}" name="q{{ i }}"
                           value="{{ question.choices[c] }}" required>
                    <label class="form-check-label" for="q{{ i }}c{{ c }}">
                      {{ question.choices[c] }}
                    </label>
                  </div>
                {% endfor %}
                <p class="text-muted small mt-2 text-end">出題者：{{ question.image }}</p>
              </div>
            </div>
          </div>
        {% endfor %}
      </div>
      <div class="progress mb-3" style="height: 25px;">
        <div id="progress-bar" 
            class="progress-bar bg-warning" 
            role="progressbar" 
            style="width: 100%;" 
            aria-valuenow="100" 
            aria-valuemin="0" 
            aria-valuemax="100">
        </div>
      </div>
      <p id="timer-text" class="text-center fw-bold"> -- 秒</p>
   
      <div class="text-center mt-3">
        <button type="button" id="pause-btn" class="btn btn-warning btn-lg mb-2">
          暫停(最多 30 秒)
        </button>
        <br>
        <button class="btn btn-success btn-lg" type="submit">交卷</button>
      </div>
    </form>
  </div>
</body>
</html>
"""

# 答題結果頁
result_template = """
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <title>結果 - 第{{ level }}關</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
  <div class="container mt-4">
    <h2>答題結果 - 第{{ level }}關</h2>
    <p>玩家：{{ player_name }}</p>
    <p>本關得分：{{ round_score }} | 累計分數：{{ total_score }} | 累計錯誤：{{ mistakes }}/3</p>
    <ul class="list-group">
      {% for i in range(question_indices|length) %}
        {% set qidx = question_indices[i] %}
        {% set question = quiz_data[qidx] %}
        <li class="list-group-item">
          <strong>{{ i+1 }}. {{ question.q }}</strong><br>
          您的答案：{{ user_answers[i] }}
          {% if user_answers[i] == question.answer %}
            <span class="text-success">（答對）</span>
          {% else %}
            <span class="text-danger">（答錯，正解：{{ question.answer }}）</span>
          {% endif %}
          <p class="text-muted small mt-2 text-end">出題者：{{ question.image }}</p>
        </li>
      {% endfor %}
    </ul>
    {% if mistakes < 3 and level < 10 %}
      <div class="text-center mt-3">
        <a href="/challenge?level={{ level + 1 }}" class="btn btn-primary btn-lg">進入第{{ level + 1 }}關</a>
      </div>
    {% else %}
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
          <td>{{ loop.index + (page - 1) * 20 }}</td>
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
    session['remaining_indices'] = list(range(len(quiz_data)))

    # 在此帶上 reset_pause=1，表示新玩家開始 => 要重置暫停秒數
    return redirect(url_for('challenge', level=1, reset_pause=1))

@app.route("/challenge")
def challenge():
    if 'player_name' not in session:
        return redirect(url_for('home'))

    level = int(request.args.get("level", 1))
    session['level'] = level

    # 計算每關的答題時間
    base_time = 40  # 第一關40秒
    time_limit = max(10, base_time - (level - 1) * 2)  # 每關減少2秒，最低保證10秒

    # 若錯誤達 3 或題目不夠，就強制結束
    remaining = session.get('remaining_indices', [])
    if len(remaining) < 3 or session['mistakes'] >= 3:
        return redirect(url_for('home'))

    # 每關抽 3 題
    selected_indices = random.sample(remaining, 3)
    for idx in selected_indices:
        remaining.remove(idx)

    session['question_indices'] = selected_indices
    session['remaining_indices'] = remaining

    # 將 reset_pause 參數原封不動傳給模板，以便模板前端判斷是否要重置
    reset_pause = request.args.get("reset_pause", "0")

    return render_template_string(
        challenge_template,
        level=level,
        player_name=session['player_name'],
        score=session['score'],
        mistakes=session['mistakes'],
        question_indices=selected_indices,
        quiz_data=quiz_data,
        time_limit=time_limit,
        reset_pause=reset_pause
    )

@app.route("/submit", methods=["POST"])
def submit():
    if 'player_name' not in session:
        return redirect(url_for('home'))

    question_indices = session.get('question_indices', [])
    level = session.get('level', 1)
    total_score = session.get('score', 0)
    mistakes = session.get('mistakes', 0)

    user_answers = []
    round_score = 0

    for i, qidx in enumerate(question_indices):
        question = quiz_data[qidx]
        user_answer = request.form.get(f"q{i}", "未作答")
        user_answers.append(user_answer)
        if user_answer == question["answer"]:
            round_score += 1
        else:
            mistakes += 1

    total_score += round_score
    session['score'] = total_score
    session['mistakes'] = mistakes

    # 若累計錯誤 >=3 或到第10關 => 遊戲結束
    if mistakes >= 3 or level == 10:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        leaderboard.append({
            "name": session['player_name'],
            "score": total_score,
            "level": level,
            "timestamp": now_str
        })
        leaderboard.sort(key=lambda x: x['score'], reverse=True)
        save_leaderboard(LEADERBOARD_FILE_PATH, leaderboard)

    return render_template_string(
        result_template,
        level=level,
        player_name=session['player_name'],
        round_score=round_score,
        total_score=total_score,
        mistakes=mistakes,
        question_indices=question_indices,
        user_answers=user_answers,
        quiz_data=quiz_data
    )

@app.route("/time_up")
def time_up():
    """
    題目答題時間已用完，強制結束遊戲，不用作答。
    直接記錄當前累計分數到排行榜。
    """
    if 'player_name' in session:
        level = session.get('level', 1)
        total_score = session.get('score', 0)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        leaderboard.append({
            "name": session['player_name'],
            "score": total_score,
            "level": level,
            "timestamp": now_str
        })
        leaderboard.sort(key=lambda x: x['score'], reverse=True)
        save_leaderboard(LEADERBOARD_FILE_PATH, leaderboard)
    # 清空 session 或保留皆可
    session.clear()

    return """
    <html>
    <head>
      <meta charset="UTF-8">
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
    # 每頁顯示的記錄數量
    records_per_page = 10
    
    # 當前頁數，默認為第 1 頁
    page = request.args.get("page", 1, type=int)

    # 總記錄數
    total_records = len(leaderboard)

    # 計算總頁數
    total_pages = (total_records + records_per_page - 1) // records_per_page

    # 獲取當前頁的記錄範圍
    start_index = (page - 1) * records_per_page
    end_index = start_index + records_per_page
    current_page_records = leaderboard[start_index:end_index]

    return render_template_string(
        ranking_template,
        ranking=current_page_records,
        page=page,
        total_pages=total_pages,
    )


# ------------------------------
# 6. 主程式啟動
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
