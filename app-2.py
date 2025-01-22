from flask import Flask, request, render_template_string

app = Flask(__name__)

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

# 挑戰模板
challenge_template = """
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>挑戰頁面</title>
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
        <h1 class="mb-4">蔬菜問答挑戰</h1>
        <form method="post" action="/submit">
            <div class="row g-4">
                {% for question_index, question in enumerate(questions) %}
                <div class="col-md-4">
                    <div class="card">
                        <img src="{{ question['image'] }}" class="card-img-top" alt="Question Image">
                        <div class="card-body">
                            <p class="card-title">{{ question_index + 1 }}. {{ question['q'] }}</p>
                            {% for choice_index, choice in enumerate(question['choices']) %}
                            <div class="form-check">
                                <input 
                                    class="form-check-input" 
                                    type="radio" 
                                    id="q{{ question_index }}-choice{{ choice_index }}" 
                                    name="q{{ question_index }}" 
                                    value="{{ choice }}" 
                                    {% if user_answers and user_answers[question_index] == choice %}checked{% endif %}>
                                <label 
                                    class="form-check-label" 
                                    for="q{{ question_index }}-choice{{ choice_index }}">
                                    {{ choice }}
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

# 結果模板
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
        <h1 class="mb-4">答題結果</h1>
        <p class="fs-4">您的分數是：<strong>{{ score }}</strong></p>
        <h2>答題詳情：</h2>
        <ul class="list-group">
            {% for index, question in enumerate(questions) %}
            <li class="list-group-item">
                <strong>{{ index + 1 }}. {{ question['q'] }}</strong><br>
                您的答案：{{ user_answers[index] }}<br>
                {% if user_answers[index] == question['answer'] %}
                <span class="text-success">答對了！</span>
                {% else %}
                <span class="text-danger">答錯了！正確答案是：{{ question['answer'] }}</span>
                {% endif %}
            </li>
            {% endfor %}
        </ul>
        <div class="text-center mt-4">
            <a href="/ranking" class="btn btn-secondary btn-lg mx-2">查看排行榜</a>
            <a href="/" class="btn btn-primary btn-lg mx-2">返回首頁</a>
        </div>
    </div>
</body>
</html>
"""

# 排行榜模板
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
                {% for rank, player in enumerate(ranking, start=1) %}
                <tr>
                    <td>{{ rank }}</td>
                    <td>{{ player['name'] }}</td>
                    <td>{{ player['score'] }}</td>
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
                <a href="/challenge" class="btn btn-primary btn-lg mx-2">開始挑戰</a>
                <a href="/ranking" class="btn btn-secondary btn-lg mx-2">排行榜</a>
            </nav>
        </div>
    </body>
    </html>
    """

@app.route("/challenge", methods=["GET", "POST"])
def challenge():
    user_answers = [None] * len(quiz_data)
    if request.method == "POST":
        for i in range(len(quiz_data)):
            user_answers[i] = request.form.get(f"q{i}")
    return render_template_string(challenge_template, questions=quiz_data, user_answers=user_answers, enumerate=enumerate)

@app.route("/submit", methods=["POST"])
def submit():
    score = 0
    user_answers = []
    for i, question in enumerate(quiz_data):
        user_answer = request.form.get(f"q{i}")
        user_answers.append(user_answer or "未作答")
        if user_answer == question['answer']:
            score += 1
    leaderboard.append({"name": f"玩家{len(leaderboard) + 1}", "score": score})
    leaderboard.sort(key=lambda x: x['score'], reverse=True)
    return render_template_string(result_template, score=score, questions=quiz_data, user_answers=user_answers, enumerate=enumerate)

@app.route("/ranking")
def ranking():
    return render_template_string(ranking_template, ranking=leaderboard, enumerate=enumerate)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
