from flask import Flask, request, render_template_string, session, redirect, url_for
import random, re, os

app = Flask(__name__)
app.secret_key = "your_secret_key"

def load_quiz_data_from_txt(file_path):
    """
    讀取單行格式 QA.txt，假設：
    (題號,'題目','選項1','選項2','選項3','出題者'),
    第一個選項為正解。
    """
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
            question_num = match.group(1)   
            question_text = match.group(2)
            choice1 = match.group(3)
            choice2 = match.group(4)
            choice3 = match.group(5)
            author = match.group(6)

            quiz_list.append({
                "q": question_text,
                "choices": [choice1, choice2, choice3],
                "answer": choice1,
                "image": author
            })
    return quiz_list

# 修改此路徑，指向你的 QA.txt
QA_FILE_PATH = "E:/temp/temp/QA.txt"
if not os.path.exists(QA_FILE_PATH):
    raise FileNotFoundError(f"找不到 QA.txt：{QA_FILE_PATH}")

quiz_data = load_quiz_data_from_txt(QA_FILE_PATH)
leaderboard = []

home_template = """
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <title>果菜知識達人 - 支援中文姓名</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
  <div class="container text-center mt-5">
    <h1>果菜知識達人</h1>
    <p>從 QA.txt 載入題目，只存索引至 Session</p>
    <form action="/start_game" method="POST">
      <!-- 前端 pattern 改成包含中文 (\u4e00-\u9fa5) -->
      <label>請輸入姓名 (1~10中英數):
        <input type="text" 
               name="player_name" 
               required 
               pattern="[A-Za-z0-9\u4e00-\u9fa5]{1,10}" 
               maxlength="10"
               title="1~10字，可包含中文、英文、數字">
      </label>
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
  <title>第{{ level }}關</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
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
    <p>玩家：{{ player_name }} | 累計分數：{{ score }}</p>
    <form method="POST" action="/submit">
      <div class="row g-4">
        {% for i in range(question_indices|length) %}
          {% set qidx = question_indices[i] %}
          {% set question = quiz_data[qidx] %}
          <div class="col-md-4">
            <div class="card">
              <img 
                src="https://via.placeholder.com/150?text={{ question.image|replace(' ','%20') }}"
                class="card-img-top" alt="Author">
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
      <div class="text-center mt-3">
        <button class="btn btn-success btn-lg" type="submit">交卷</button>
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
  <title>結果 - 第{{ level }}關</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
  <div class="container mt-4">
    <h2>答題結果 - 第{{ level }}關</h2>
    <p>玩家：{{ player_name }}</p>
    <p>本關得分：{{ round_score }} | 累計分數：{{ total_score }}</p>
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
    {% if level < 3 %}
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
    <a href="/" class="btn btn-primary btn-lg mt-3">回首頁</a>
  </div>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(home_template)

@app.route("/start_game", methods=["POST"])
def start_game():
    player_name = request.form.get("player_name", "").strip()
    # 後端也用相同的正則，允許中文 (\u4e00-\u9fa5) + 英數
    if not re.match(r'^[A-Za-z0-9\u4e00-\u9fa5]{1,10}$', player_name):
        return "<p>姓名格式錯誤(必須 1~10 字，可含中英數)。<a href='/'>返回</a></p>"

    session['player_name'] = player_name
    session['score'] = 0
    session['level'] = 1
    session['remaining_indices'] = list(range(len(quiz_data)))

    return redirect(url_for('challenge', level=1))

@app.route("/challenge")
def challenge():
    if 'player_name' not in session:
        return redirect(url_for('home'))

    level = int(request.args.get("level", 1))
    session['level'] = level

    remaining = session.get('remaining_indices', [])
    if len(remaining) < 3:
        return "<p>題目不足或遊戲已結束。<a href='/'>回首頁</a></p>"

    selected_indices = random.sample(remaining, 3)
    for idx in selected_indices:
        remaining.remove(idx)

    session['question_indices'] = selected_indices
    session['remaining_indices'] = remaining

    return render_template_string(
        challenge_template,
        level=level,
        player_name=session['player_name'],
        score=session['score'],
        question_indices=selected_indices,
        quiz_data=quiz_data
    )

@app.route("/submit", methods=["POST"])
def submit():
    if 'player_name' not in session:
        return redirect(url_for('home'))

    question_indices = session.get('question_indices', [])
    level = session.get('level', 1)
    total_score = session.get('score', 0)

    user_answers = []
    round_score = 0

    for i, qidx in enumerate(question_indices):
        question = quiz_data[qidx]
        user_answer = request.form.get(f"q{i}", "未作答")
        user_answers.append(user_answer)
        if user_answer == question["answer"]:
            round_score += 1

    total_score += round_score
    session['score'] = total_score

    if level == 3:
        leaderboard.append({
            "name": session['player_name'],
            "score": total_score
        })
        leaderboard.sort(key=lambda x: x['score'], reverse=True)

    return render_template_string(
        result_template,
        level=level,
        player_name=session['player_name'],
        round_score=round_score,
        total_score=total_score,
        question_indices=question_indices,
        user_answers=user_answers,
        quiz_data=quiz_data
    )

@app.route("/ranking")
def ranking():
    return render_template_string(ranking_template, ranking=leaderboard)

if __name__ == "__main__":
    # 監聽 0.0.0.0 以允許區網連線
    app.run(host="0.0.0.0", port=5000, debug=True)
