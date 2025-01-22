from flask import Flask, request, render_template_string, session, redirect, url_for
import random
import re
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"  # 必須設定，以使用 session

# ------------------------------------------------
# 1. 讀取 QA.txt 函式
# ------------------------------------------------

def load_quiz_data_from_txt(file_path):
    """
    從指定的檔案路徑 file_path 讀取 QA.txt，回傳 list[dict]
    每 4 行為一題（中間若有空白行會先被過濾）：
      1) 問題
      2) 選項（逗號分隔）
      3) 正確答案
      4) 圖片連結
    """
    quiz_list = []
    with open(file_path, "r", encoding="utf-8") as f:
        # 讀取全部行並去掉空白行
        lines = [line.strip() for line in f if line.strip()]

    # 檢查總行數是否為 4 的倍數
    if len(lines) % 4 != 0:
        raise ValueError("QA-old.txt 格式錯誤：每題應該是 4 行，不含空白行。")

    for i in range(0, len(lines), 4):
        question = lines[i]
        choices_line = lines[i + 1]
        answer = lines[i + 2]
        image_url = lines[i + 3]

        # 用逗號分隔成清單
        choices = [c.strip() for c in choices_line.split(",")]

        quiz_list.append({
            "q": question,
            "choices": choices,
            "answer": answer,
            "image": image_url
        })

    return quiz_list


# ------------------------------------------------
# 2. 讀取 QA.txt 到 quiz_data（在程式啟動時載入）
# ------------------------------------------------

# 假設 QA.txt 跟 app.py 放在同一層
# 也可換成絕對路徑，如 "C:/myproject/QA.txt"
QA_FILE_PATH = "E:/temp/temp/QA-old.txt"

if not os.path.exists(QA_FILE_PATH):
    raise FileNotFoundError(f"找不到檔案：{QA_FILE_PATH}")

quiz_data = load_quiz_data_from_txt(QA_FILE_PATH)

# 建立排行榜儲存結構
leaderboard = []

# ------------------------------------------------
# 3. HTML 模板（與之前類似）
# ------------------------------------------------

home_template = """
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>果菜知達人</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>.container { max-width: 500px; }</style>
</head>
<body class="bg-light">
    <div class="container text-center mt-5">
        <h1 class="mb-4">歡迎來到蔬菜知識問答遊戲（讀檔版）</h1>
        <form action="/start_game" method="post" class="mb-3">
            <div class="mb-3">
                <label for="player_name" class="form-label">請輸入您的姓名 (字母或數字，最多10字)</label>
                <input type="text" class="form-control" id="player_name" name="player_name"
                       required pattern="[A-Za-z0-9]{1,10}" maxlength="10"
                       title="只能輸入英文或數字，長度1~10">
            </div>
            <button type="submit" class="btn btn-primary btn-lg">開始挑戰</button>
        </form>
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
    <title>挑戰頁面 - 第{{ level }}關</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .form-check-input:checked + .form-check-label {
            background-color: #d1e7dd;
            border-radius: 5px;
        }
        .form-check-label {
            cursor: pointer;
        }
        .card-img-top {
            height: 150px;
            object-fit: cover;
        }
    </style>
</head>
<body class="bg-light">
    <div class="container mt-4">
        <h1 class="mb-3">蔬菜問答挑戰 - 第{{ level }}關</h1>
        <p>玩家：{{ player_name }}｜累計分數：{{ current_score }}</p>
        <form method="post" action="/submit">
            <div class="row g-4">
                {% for i in range(questions|length) %}
                <div class="col-md-4">
                    <div class="card">
                        <img 
                            src="{{ questions[i].image }}" 
                            class="card-img-top" 
                            alt="Question Image" 
                            onerror="this.src='https://via.placeholder.com/150?text=Image+Not+Found';">
                        <div class="card-body">
                            <p class="card-title">
                                {{ i + 1 }}. {{ questions[i].q }}
                            </p>
                            {% for c in range(questions[i].choices|length) %}
                            <div class="form-check">
                                <input 
                                    class="form-check-input" 
                                    type="radio" 
                                    id="q{{ i }}-choice{{ c }}" 
                                    name="q{{ i }}" 
                                    value="{{ questions[i].choices[c] }}" 
                                    required>
                                <label 
                                    class="form-check-label" 
                                    for="q{{ i }}-choice{{ c }}">
                                    {{ questions[i].choices[c] }}
                                </label>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
            <div class="text-center mt-4">
                <button type="submit" class="btn btn-success btn-lg">提交答案</button>
            </div>
        </form>
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
    <title>結果頁面</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container mt-4">
        <h1 class="mb-3">答題結果 - 第{{ level }}關</h1>
        <p>玩家：{{ player_name }}</p>
        <p>本關得分：<strong>{{ round_score }}</strong> / {{ questions|length }}</p>
        <p>累計分數：<strong>{{ total_score }}</strong></p>
        <h2>答題詳情：</h2>
        <ul class="list-group">
            {% for i in range(questions|length) %}
            <li class="list-group-item">
                <strong>
                    {{ i + 1 }}. {{ questions[i].q }}
                </strong><br>
                您的答案：{{ user_answers[i] }}<br>
                {% if user_answers[i] == questions[i].answer %}
                <span class="text-success">答對了！</span>
                {% else %}
                <span class="text-danger">答錯了！正確答案是：{{ questions[i].answer }}</span>
                {% endif %}
            </li>
            {% endfor %}
        </ul>
        {% if level < 3 %}
        <div class="text-center mt-4">
            <a href="/challenge?level={{ level + 1 }}" class="btn btn-primary btn-lg">
                進入第{{ level + 1 }}關
            </a>
        </div>
        {% else %}
        <div class="text-center mt-4">
            <a href="/ranking" class="btn btn-secondary btn-lg mx-2">查看排行榜</a>
            <a href="/" class="btn btn-primary btn-lg mx-2">返回首頁</a>
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
        <h1 class="mb-4">排行榜</h1>
        <table class="table table-striped">
            <thead>
                <tr>
                    <th>名次</th>
                    <th>玩家</th>
                    <th>分數</th>
                </tr>
            </thead>
            <tbody>
                {% for player in ranking %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td>{{ player.name }}</td>
                    <td>{{ player.score }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <div class="text-center mt-4">
            <a href="/" class="btn btn-primary btn-lg">返回首頁</a>
        </div>
    </div>
</body>
</html>
"""

# ------------------------------------------------
# 4. Flask 路由
# ------------------------------------------------

@app.route("/")
def home():
    return render_template_string(home_template)

@app.route("/start_game", methods=["POST"])
def start_game():
    """
    接收玩家姓名並驗證，若合法就初始化：
      1) level = 1
      2) score = 0
      3) remaining_questions = quiz_data.copy()
    """
    player_name = request.form.get("player_name", "").strip()
    if not re.match(r"^[A-Za-z0-9]{1,10}$", player_name):
        return """
        <p>姓名格式錯誤 (只能英文數字1~10字)。</p>
        <a href="/">返回首頁</a>
        """

    session['player_name'] = player_name
    session['level'] = 1
    session['score'] = 0
    # 不重複題目：複製整個 quiz_data 當剩餘題庫
    session['remaining_questions'] = quiz_data.copy()

    return redirect(url_for('challenge', level=1))

@app.route("/challenge", methods=["GET"])
def challenge():
    if 'player_name' not in session:
        return redirect(url_for('home'))

    level = int(request.args.get("level", 1))
    session['level'] = level

    remaining = session.get('remaining_questions', [])
    if len(remaining) < 3:
        # 題庫不夠 => 回首頁或自行處理
        return redirect(url_for('home'))

    # 隨機抽 3 題
    selected = random.sample(remaining, 3)
    # 從 remaining 中移除
    for q in selected:
        remaining.remove(q)

    # 更新 session
    session['questions'] = selected
    session['remaining_questions'] = remaining

    return render_template_string(
        challenge_template,
        level=level,
        player_name=session['player_name'],
        current_score=session['score'],
        questions=selected
    )

@app.route("/submit", methods=["POST"])
def submit():
    if 'player_name' not in session:
        return redirect(url_for('home'))

    questions = session.get('questions', [])
    level = session.get('level', 1)
    total_score = session.get('score', 0)
    player_name = session['player_name']

    round_score = 0
    user_answers = []

    for i, q in enumerate(questions):
        user_answer = request.form.get(f"q{i}", "未作答")
        user_answers.append(user_answer)
        if user_answer == q['answer']:
            round_score += 1

    # 更新累計分數
    total_score += round_score
    session['score'] = total_score

    # 第3關提交後 -> 更新排行榜
    if level == 3:
        leaderboard.append({
            'name': player_name,
            'score': total_score
        })
        leaderboard.sort(key=lambda x: x['score'], reverse=True)

    return render_template_string(
        result_template,
        level=level,
        player_name=player_name,
        round_score=round_score,
        total_score=total_score,
        questions=questions,
        user_answers=user_answers
    )

@app.route("/ranking")
def ranking():
    return render_template_string(ranking_template, ranking=leaderboard)

# ------------------------------------------------
# 5. 啟動 Flask
# ------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
