from flask import Flask, request, render_template_string, session, redirect, url_for
import random
import re

app = Flask(__name__)
app.secret_key = "your_secret_key"  # 用來加密 session

# ------------------------------
# 1. 定義問題與排行榜資料
# ------------------------------
# 定義問題數據
quiz_data = [
    {"q": "哪種蔬菜是橘色的？", "choices": ["胡蘿蔔", "菠菜", "馬鈴薯"], "answer": "胡蘿蔔", "image": "https://upload.wikimedia.org/wikipedia/commons/6/63/Carrot.jpg"},
    {"q": "哪種蔬菜是綠色的？", "choices": ["胡蘿蔔", "菠菜", "馬鈴薯"], "answer": "菠菜", "image": "https://upload.wikimedia.org/wikipedia/commons/4/45/Spinach_leaves.jpg"},
    {"q": "哪種蔬菜是生長在地下的？", "choices": ["胡蘿蔔", "菠菜", "馬鈴薯"], "answer": "馬鈴薯", "image": "https://upload.wikimedia.org/wikipedia/commons/a/ab/Patates.jpg"},
    {"q": "青椒是什麼顏色？", "choices": ["綠色", "黃色", "紅色"], "answer": "綠色", "image": "https://upload.wikimedia.org/wikipedia/commons/2/2f/Green_bell_pepper.jpg"},
    {"q": "茄子是哪種顏色？", "choices": ["紫色", "橙色", "白色"], "answer": "紫色", "image": "https://upload.wikimedia.org/wikipedia/commons/5/56/Eggplant.jpg"},
    {"q": "蘿蔔含有什麼豐富的營養成分？", "choices": ["維生素A", "鈣", "維生素C"], "answer": "維生素C", "image": "https://upload.wikimedia.org/wikipedia/commons/c/cb/Radishes_bunch.jpg"},
    {"q": "哪種蔬菜被稱為“地瓜”？", "choices": ["紅薯", "菠菜", "南瓜"], "answer": "紅薯", "image": "https://upload.wikimedia.org/wikipedia/commons/2/2b/Sweet_potato.jpg"},
    {"q": "菠菜對哪種健康問題有幫助？", "choices": ["貧血", "視力", "骨骼"], "answer": "貧血", "image": "https://upload.wikimedia.org/wikipedia/commons/4/45/Spinach_leaves.jpg"},
    {"q": "西紅柿是什麼顏色的？", "choices": ["紅色", "黃色", "綠色"], "answer": "紅色", "image": "https://upload.wikimedia.org/wikipedia/commons/8/89/Tomato_je.jpg"},
    {"q": "哪種水果被稱為“熱帶水果之王”？", "choices": ["鳳梨", "芒果", "榴槤"], "answer": "榴槤", "image": "https://upload.wikimedia.org/wikipedia/commons/e/e0/Durian.jpg"},
    {"q": "哪種水果富含維生素C？", "choices": ["橙子", "香蕉", "蘋果"], "answer": "橙子", "image": "https://upload.wikimedia.org/wikipedia/commons/c/c4/Orange-Fruit-Pieces.jpg"},
    {"q": "香蕉是什麼顏色的？", "choices": ["黃色", "綠色", "紅色"], "answer": "黃色", "image": "https://upload.wikimedia.org/wikipedia/commons/8/8a/Banana-Single.jpg"},
    {"q": "哪種水果有助於改善消化？", "choices": ["鳳梨", "蘋果", "西瓜"], "answer": "鳳梨", "image": "https://upload.wikimedia.org/wikipedia/commons/c/cb/Pineapple_and_cross_section.jpg"},
    {"q": "哪種蔬菜被稱為“天然抗氧化劑”？", "choices": ["胡蘿蔔", "西紅柿", "茄子"], "answer": "西紅柿", "image": "https://upload.wikimedia.org/wikipedia/commons/8/89/Tomato_je.jpg"},
    {"q": "哪種水果有多種顏色，如紅、綠、黃？", "choices": ["蘋果", "梨", "葡萄"], "answer": "蘋果", "image": "https://upload.wikimedia.org/wikipedia/commons/1/15/Red_Apple.jpg"},
    {"q": "哪種蔬菜經常用於做沙拉？", "choices": ["黃瓜", "南瓜", "青椒"], "answer": "黃瓜", "image": "https://upload.wikimedia.org/wikipedia/commons/9/91/Cucumber.jpg"},
    {"q": "草莓是什麼顏色的？", "choices": ["紅色", "白色", "綠色"], "answer": "紅色", "image": "https://upload.wikimedia.org/wikipedia/commons/2/29/PerfectStrawberry.jpg"},
    {"q": "什麼水果被稱為“夏季之王”？", "choices": ["西瓜", "哈密瓜", "芒果"], "answer": "西瓜", "image": "https://upload.wikimedia.org/wikipedia/commons/3/3a/Cut_watermelon.jpg"},
    {"q": "哪種水果有著豐富的鉀元素？", "choices": ["香蕉", "蘋果", "葡萄"], "answer": "香蕉", "image": "https://upload.wikimedia.org/wikipedia/commons/8/8a/Banana-Single.jpg"},
    {"q": "哪種蔬菜是深紫色的？", "choices": ["茄子", "洋蔥", "卷心菜"], "answer": "茄子", "image": "https://upload.wikimedia.org/wikipedia/commons/5/56/Eggplant.jpg"},
    {"q": "什麼水果的種子分佈在外皮上？", "choices": ["草莓", "櫻桃", "桃子"], "answer": "草莓", "image": "https://upload.wikimedia.org/wikipedia/commons/2/29/PerfectStrawberry.jpg"},
    {"q": "胡蘿蔔的主要營養成分是什麼？", "choices": ["維生素A", "維生素C", "鐵"], "answer": "維生素A", "image": "https://upload.wikimedia.org/wikipedia/commons/6/63/Carrot.jpg"},
    {"q": "哪種水果是最常見的“柑橘類水果”？", "choices": ["橙子", "葡萄柚", "檸檬"], "answer": "橙子", "image": "https://upload.wikimedia.org/wikipedia/commons/c/c4/Orange-Fruit-Pieces.jpg"},
    {"q": "什麼蔬菜的葉子經常被用來泡茶？", "choices": ["薄荷", "香菜", "九層塔"], "answer": "薄荷", "image": "https://upload.wikimedia.org/wikipedia/commons/7/71/Mint_leaves.jpg"},
]
leaderboard = []

# ------------------------------
# 2. 定義前端模板 (HTML)
# ------------------------------

# 首頁：讓玩家輸入姓名（10 字英數內）
home_template = """
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>蔬菜知識問答</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>.container { max-width: 500px; }</style>
</head>
<body class="bg-light">
    <div class="container text-center mt-5">
        <h1 class="mb-4">歡迎來到蔬菜知識問答遊戲！</h1>
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

# 挑戰頁面：顯示玩家姓名、顯示「累計分數」，每關抽 3 題不重複
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

# 結果頁面：顯示本關答對多少，總分也一起顯示
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

# 排行榜頁面
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

# ------------------------------
# 3. 設定路由 (Views)
# ------------------------------

@app.route("/")
def home():
    """
    首頁：玩家先輸入姓名，限制英數 10 字元以內。
    """
    return render_template_string(home_template)

@app.route("/start_game", methods=["POST"])
def start_game():
    """
    接收玩家姓名，驗證後初始化：
      1) level = 1
      2) score = 0 (累計分數)
      3) remaining_questions = quiz_data 的複本 (防止題目重複)
    然後導向 /challenge?level=1
    """
    player_name = request.form.get("player_name", "").strip()

    # 後端再檢查一次，避免跳過前端限制
    if not re.match(r"^[A-Za-z0-9]{1,10}$", player_name):
        return """
        <p>姓名格式錯誤，請重新輸入 (只能英文數字，1~10字)。</p>
        <a href="/">返回首頁</a>
        """

    # 將玩家資料存入 session
    session['player_name'] = player_name
    session['level'] = 1
    session['score'] = 0

    # 為了「題目不重複」，把原始 quiz_data 複製到 session['remaining_questions']
    # 這裡直接存成清單；稍後每抽 3 題就從裡面移除
    session['remaining_questions'] = quiz_data.copy()

    return redirect(url_for('challenge', level=1))

@app.route("/challenge", methods=["GET"])
def challenge():
    """
    每次進入 challenge:
      1) 讀取目前第幾關(level)與累計分數(score)
      2) 從 remaining_questions 隨機抽 3 題並移除
      3) 存到 session['questions']，顯示給玩家作答
    """
    if 'player_name' not in session:
        return redirect(url_for('home'))

    level = int(request.args.get("level", 1))
    session['level'] = level  # 更新 session 的關卡（保險）

    # 如果 remaining_questions 剩餘不足 3 題，就保護性處理；理論上不會發生
    remaining = session.get('remaining_questions', [])
    if len(remaining) < 3:
        # 題目不夠就強制重置或導回首頁
        return redirect(url_for('home'))

    # 從 remaining 裡隨機抽 3 題
    selected = random.sample(remaining, 3)
    # 再從 remaining 裡移除這 3 題，避免下關重複
    for q in selected:
        remaining.remove(q)

    # 抽出來的 3 題存 session，之後 /submit 要對這 3 題判分
    session['questions'] = selected
    # 更新 session 中剩餘題目
    session['remaining_questions'] = remaining

    return render_template_string(
        challenge_template,
        level=level,
        player_name=session['player_name'],
        current_score=session['score'],  # 累計分數
        questions=selected
    )

@app.route("/submit", methods=["POST"])
def submit():
    """
    提交本關答案：
      1) 讀取 session['questions'] (本關題目) 與 session['score'] (累計分數)
      2) 計算本關得分，加到累計分數
      3) 若 level < 3，導到下一關；level=3 時存到排行榜
    """
    if 'player_name' not in session:
        return redirect(url_for('home'))

    questions = session.get('questions', [])
    level = session.get('level', 1)
    total_score = session.get('score', 0)  # 目前累計分數
    player_name = session['player_name']

    round_score = 0
    user_answers = []

    # 遍歷本關 3 題
    for i, q in enumerate(questions):
        user_answer = request.form.get(f"q{i}", "未作答")
        user_answers.append(user_answer)
        if user_answer == q['answer']:
            round_score += 1

    # 累計分數更新
    total_score += round_score
    session['score'] = total_score  # 存回 session

    # 如果已到第 3 關，將最終分數存入排行榜
    if level == 3:
        leaderboard.append({
            'name': player_name,
            'score': total_score
        })
        leaderboard.sort(key=lambda x: x['score'], reverse=True)

    # 渲染結果
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
    """顯示排行榜"""
    return render_template_string(ranking_template, ranking=leaderboard)

# ------------------------------
# 4. 啟動伺服器
# ------------------------------
if __name__ == "__main__":
    app.run(debug=True)
