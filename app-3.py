from flask import Flask, request, render_template_string, session, redirect, url_for
import random

app = Flask(__name__)
app.secret_key = "your_secret_key"  # 必須設定以使用 session

# ------------------------------
# 一、定義問題與排行榜資料
# ------------------------------
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
]

leaderboard = []

# ------------------------------
# 二、定義前端模板（HTML）
# ------------------------------

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
    <div class="container mt-5">
        <h1 class="mb-4">蔬菜問答挑戰 - 第{{ level }}關</h1>
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
    <div class="container mt-5">
        <h1 class="mb-4">答題結果 - 第{{ level }}關</h1>
        <p class="fs-4">您的分數是：<strong>{{ score }}</strong></p>
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
            <a href="/challenge?level={{ level + 1 }}" class="btn btn-primary btn-lg">進入第{{ level + 1 }}關</a>
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
    <div class="container mt-5">
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
# 三、設定路由 (Views)
# ------------------------------

@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html lang="zh-Hant">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>蔬菜知識問答</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <div class="container text-center mt-5">
            <h1 class="mb-4">歡迎來到蔬菜知識問答遊戲！</h1>
            <nav>
                <a href="/challenge?level=1" class="btn btn-primary btn-lg mx-2">開始挑戰</a>
                <a href="/ranking" class="btn btn-secondary btn-lg mx-2">排行榜</a>
            </nav>
        </div>
    </body>
    </html>
    """

@app.route("/challenge")
def challenge():
    # 取得關卡數（預設=1）
    level = int(request.args.get("level", 1))

    # 從 quiz_data 隨機取 3 題，以「清單」形式存入 session
    selected_questions = random.sample(quiz_data, 3)
    session['questions'] = selected_questions
    session['level'] = level
    
    return render_template_string(challenge_template,
                                  questions=selected_questions,
                                  level=level)

@app.route("/submit", methods=["POST"])
def submit():
    # 從 session 取出「清單」型態的題目
    questions = session.get('questions', [])
    level = session.get('level', 1)

    # 如果沒拿到題目，就導回首頁
    if not questions:
        return redirect(url_for('home'))

    score = 0
    user_answers = []
    
    # 用 enumerate(questions) 也行；這裡用 range(len()) 亦可
    for i in range(len(questions)):
        # 從表單裡取出對應題目的答案
        user_answer = request.form.get(f"q{i}")
        user_answers.append(user_answer or "未作答")

        if user_answer == questions[i]['answer']:
            score += 1

    # 如果到第3關，把分數記入排行榜
    if level == 3:
        leaderboard.append({
            'name': f"玩家{len(leaderboard) + 1}",
            'score': score
        })
        leaderboard.sort(key=lambda x: x['score'], reverse=True)

    return render_template_string(result_template,
                                  score=score,
                                  questions=questions,
                                  user_answers=user_answers,
                                  level=level)

@app.route("/ranking")
def ranking():
    return render_template_string(ranking_template, ranking=leaderboard)

if __name__ == "__main__":
    app.run(debug=True)
