from flask import Flask, render_template_string, jsonify, request, session, redirect, url_for, flash, make_response
import time
import threading
from collections import defaultdict
import hashlib
import secrets
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # セッション用のシークレットキー

# 永続的なログイントークンの保存
persistent_tokens = {}  # {token: {'username': str, 'expires': datetime}}

def cleanup_expired_tokens():
    """期限切れトークンの定期削除"""
    global persistent_tokens
    while True:
        current_time = datetime.now()
        persistent_tokens = {token: data for token, data in persistent_tokens.items()
                           if data['expires'] > current_time}
        time.sleep(3600)  # 1時間ごとにクリーンアップ

# バックグラウンドでトークンクリーンアップを実行
token_cleanup_thread = threading.Thread(target=cleanup_expired_tokens, daemon=True)
token_cleanup_thread.start()

# アクティブユーザー追跡
active_users = defaultdict(float)
user_counter = 0

# サーバー設定
server_settings = {
    "user_timeout": 30,  # アクティブユーザーのタイムアウト時間（秒）
    "debug_mode": True,  # デバッグモード
    "max_users": 100,    # 最大同時接続ユーザー数
    "heartbeat_interval": 15,  # ハートビート間隔（秒）
    "maintenance_mode": False,  # メンテナンスモード
    "server_name": "GAME SERVER",  # サーバー名
    "registration_enabled": True,  # 新規登録の有効/無効
}

# 簡単なユーザーデータベース（実際のアプリケーションではデータベースを使用してください）
users_db = {
    "admin": {
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "管理者",
        "user_id": "admin_001"
    },
    "superadmin": {
        "password_hash": hashlib.sha256("super2024".encode()).hexdigest(),
        "role": "管理者",
        "user_id": "admin_002"
    },
    "user1": {
        "password_hash": hashlib.sha256("password123".encode()).hexdigest(),
        "role": "一般ユーザー",
        "user_id": "user_001"
    },
    "gamer": {
        "password_hash": hashlib.sha256("game123".encode()).hexdigest(),
        "role": "ゲーマー",
        "user_id": "gamer_001"
    }
}

def cleanup_inactive_users():
    """非アクティブなユーザーを定期的に削除"""
    global active_users
    while True:
        current_time = time.time()
        # 設定されたタイムアウト時間以上更新がないユーザーを削除
        timeout = server_settings.get("user_timeout", 30)
        active_users = {uid: last_seen for uid, last_seen in active_users.items()
                       if current_time - last_seen < timeout}
        time.sleep(10)

# バックグラウンドでクリーンアップを実行
cleanup_thread = threading.Thread(target=cleanup_inactive_users, daemon=True)
cleanup_thread.start()

def verify_password(username, password):
    """ユーザー名とパスワードを検証"""
    if username in users_db:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return password_hash == users_db[username]["password_hash"]
    return False

def get_user_info(username):
    """ユーザー情報を取得"""
    if username in users_db:
        return users_db[username]
    return None

def check_persistent_login():
    """永続的なログインをチェック"""
    if 'username' not in session:
        remember_token = request.cookies.get('remember_token')
        if remember_token and remember_token in persistent_tokens:
            token_data = persistent_tokens[remember_token]
            if token_data['expires'] > datetime.now():
                # トークンが有効な場合、自動ログイン
                session['username'] = token_data['username']
                return True
            else:
                # 期限切れトークンを削除
                del persistent_tokens[remember_token]
    return False

@app.before_request
def before_request():
    """各リクエスト前に永続的なログインをチェック"""
    check_persistent_login()

# HTMLテンプレート
template = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GAME SERVER</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Orbitron', monospace;
            background: #0a0a0a;
            color: #ffffff;
            overflow-x: hidden;
        }

        /* Animated background */
        .bg-animation {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(45deg, #0a0a0a, #1a2e42, #163e42, #0a1a2e, #2e1a42);
            background-size: 400% 400%;
            animation: gradientShift 15s ease infinite;
            z-index: -1;
        }

        .bg-animation::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle at 20% 50%, rgba(0, 212, 255, 0.1) 0%, transparent 50%),
                        radial-gradient(circle at 80% 20%, rgba(0, 153, 255, 0.1) 0%, transparent 50%),
                        radial-gradient(circle at 40% 80%, rgba(0, 212, 255, 0.05) 0%, transparent 50%);
            animation: floatingLights 20s ease-in-out infinite;
        }

        .bg-animation::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background:
                linear-gradient(90deg, transparent 0%, rgba(0, 212, 255, 0.03) 50%, transparent 100%);
            animation: sweepingLight 8s linear infinite;
        }

        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            25% { background-position: 100% 100%; }
            50% { background-position: 100% 50%; }
            75% { background-position: 0% 0%; }
            100% { background-position: 0% 50%; }
        }

        @keyframes floatingLights {
            0%, 100% {
                transform: translate(0, 0) scale(1);
                opacity: 0.3;
            }
            25% {
                transform: translate(30px, -20px) scale(1.1);
                opacity: 0.5;
            }
            50% {
                transform: translate(-20px, 30px) scale(0.9);
                opacity: 0.4;
            }
            75% {
                transform: translate(20px, 10px) scale(1.05);
                opacity: 0.6;
            }
        }

        @keyframes sweepingLight {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }

        /* Navigation */
        nav {
            position: fixed;
            top: 0;
            width: 100%;
            padding: 1rem 2rem;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(10px);
            z-index: 1000;
            border-bottom: 2px solid #00d4ff;
        }

        .nav-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            max-width: 1200px;
            margin: 0 auto;
        }

        .logo {
            font-size: 1.8rem;
            font-weight: 900;
            color: #00d4ff;
            text-shadow: 0 0 20px #00d4ff;
        }

        .nav-links {
            display: flex;
            gap: 2rem;
            list-style: none;
        }

        .nav-links a {
            color: #ffffff;
            text-decoration: none;
            transition: all 0.3s ease;
            padding: 0.5rem 1rem;
            border-radius: 5px;
        }

        .nav-links a:hover {
            color: #00d4ff;
            background: rgba(0, 212, 255, 0.1);
            transform: translateY(-2px);
        }

        /* Hero Section */
        .hero {
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            position: relative;
        }

        .hero-content h1 {
            font-size: 4rem;
            font-weight: 900;
            margin-bottom: 1rem;
            background: linear-gradient(45deg, #0099ff, #00d4ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: glow 2s ease-in-out infinite alternate;
        }

        @keyframes glow {
            from { text-shadow: 0 0 20px #0099ff; }
            to { text-shadow: 0 0 30px #0099ff, 0 0 40px #00d4ff; }
        }

        .hero-content p {
            font-size: 1.2rem;
            margin-bottom: 2rem;
            opacity: 0.8;
        }

        .cta-button {
            display: inline-block;
            padding: 1rem 2rem;
            background: linear-gradient(45deg, #0099ff, #00d4ff);
            color: #000;
            text-decoration: none;
            border-radius: 50px;
            font-weight: 700;
            transition: all 0.3s ease;
            box-shadow: 0 10px 30px rgba(0, 153, 255, 0.3);
        }

        .cta-button:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0, 153, 255, 0.5);
        }

        /* Features Section */
        .features {
            padding: 5rem 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }

        .features h2 {
            text-align: center;
            font-size: 3rem;
            margin-bottom: 3rem;
            color: #00d4ff;
            animation: pulse 3s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% {
                text-shadow: 0 0 5px #00d4ff;
                transform: scale(1);
            }
            50% {
                text-shadow: 0 0 20px #00d4ff, 0 0 30px #0099ff;
                transform: scale(1.02);
            }
        }

        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
        }

        .feature-card {
            opacity: 0;
            transform: translateY(50px);
            transition: all 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        }

        .feature-card.animate {
            opacity: 1;
            transform: translateY(0);
        }

        .features h2 {
            opacity: 0;
            transform: translateY(30px);
            transition: all 0.6s ease-out;
        }

        .features h2.animate {
            opacity: 1;
            transform: translateY(0);
        }

        .feature-card {
            background: rgba(255, 255, 255, 0.05);
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid rgba(0, 212, 255, 0.3);
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            backdrop-filter: blur(10px);
            position: relative;
            overflow: hidden;
        }

        .feature-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.1), transparent);
            transition: left 0.5s ease;
        }

        .feature-card:hover::before {
            left: 100%;
        }

        .feature-card:hover {
            transform: translateY(-15px) scale(1.02);
            border-color: #00d4ff;
            box-shadow: 0 25px 50px rgba(0, 212, 255, 0.3);
            background: rgba(255, 255, 255, 0.08);
        }

        .feature-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
            color: #0099ff;
            transition: all 0.4s ease;
            transform: translateY(0);
        }

        .feature-card:hover .feature-icon {
            transform: translateY(-5px) rotate(10deg) scale(1.1);
            color: #00d4ff;
            text-shadow: 0 0 20px #00d4ff;
        }

        .feature-card h3 {
            font-size: 1.5rem;
            margin-bottom: 1rem;
            color: #00d4ff;
        }

        .feature-card p {
            opacity: 0.8;
            line-height: 1.6;
        }

        /* Stats Section */
        .stats {
            background: rgba(0, 0, 0, 0.5);
            padding: 3rem 2rem;
            text-align: center;
        }

        .stats-container {
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 2rem;
        }

        .stat-item {
            padding: 2rem;
            position: relative;
        }

        .stat-number {
            font-size: 3rem;
            font-weight: 900;
            color: #00d4ff;
            margin-bottom: 0.5rem;
        }

        .stat-label {
            font-size: 1.1rem;
            opacity: 0.8;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
        }

        /* Footer */
        footer {
            background: #000;
            padding: 2rem;
            text-align: center;
            border-top: 2px solid #00d4ff;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .hero-content h1 {
                font-size: 2.5rem;
            }

            .nav-links {
                display: none;
            }

            .features h2 {
                font-size: 2rem;
            }
        }

        /* Custom Cursor Animations */
        body {
            cursor: none; /* Hide default cursor */
        }

        /* Custom cursor dot */
        .custom-cursor {
            position: fixed;
            width: 20px;
            height: 20px;
            background: #00d4ff;
            border-radius: 50%;
            pointer-events: none;
            z-index: 9999;
            mix-blend-mode: difference;
            transition: transform 0.1s ease;
            box-shadow: 0 0 20px #00d4ff;
        }

        .custom-cursor.clicking {
            transform: scale(0.5);
            background: #ff6b6b;
            box-shadow: 0 0 30px #ff6b6b;
        }

        /* Hover effects for interactive elements */
        .custom-cursor.hovering {
            transform: scale(2);
            background: transparent;
            border: 2px solid #00d4ff;
            box-shadow: 0 0 40px #00d4ff;
        }

        /* Trail cursor */
        .cursor-trail {
            position: fixed;
            width: 6px;
            height: 6px;
            background: rgba(0, 212, 255, 0.5);
            border-radius: 50%;
            pointer-events: none;
            z-index: 9998;
            transition: all 0.3s ease;
        }

        /* Pulsing cursor */
        @keyframes cursorPulse {
            0% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.5); opacity: 0.7; }
            100% { transform: scale(1); opacity: 1; }
        }

        .custom-cursor.pulsing {
            animation: cursorPulse 1s infinite;
        }

        /* Rotating cursor */
        @keyframes cursorRotate {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .custom-cursor.rotating {
            animation: cursorRotate 2s linear infinite;
            border-radius: 0;
            width: 15px;
            height: 15px;
            background: linear-gradient(45deg, #00d4ff, #0099ff);
        }

        /* Magnetic cursor */
        .custom-cursor.magnetic {
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }

        /* Glitch cursor */
        @keyframes glitchCursor {
            0%, 100% { transform: translate(0); }
            10% { transform: translate(-2px, 2px); }
            20% { transform: translate(2px, -2px); }
            30% { transform: translate(-2px, -2px); }
            40% { transform: translate(2px, 2px); }
            50% { transform: translate(-2px, 2px); }
            60% { transform: translate(2px, -2px); }
            70% { transform: translate(-2px, -2px); }
            80% { transform: translate(2px, 2px); }
            90% { transform: translate(-2px, 2px); }
        }

        .custom-cursor.glitch {
            animation: glitchCursor 0.3s infinite;
        }

        /* Rainbow cursor */
        @keyframes rainbowCursor {
            0% { background: #ff0000; box-shadow: 0 0 20px #ff0000; }
            16.66% { background: #ff8000; box-shadow: 0 0 20px #ff8000; }
            33.33% { background: #ffff00; box-shadow: 0 0 20px #ffff00; }
            50% { background: #00ff00; box-shadow: 0 0 20px #00ff00; }
            66.66% { background: #0000ff; box-shadow: 0 0 20px #0000ff; }
            83.33% { background: #8000ff; box-shadow: 0 0 20px #8000ff; }
            100% { background: #ff0000; box-shadow: 0 0 20px #ff0000; }
        }

        .custom-cursor.rainbow {
            animation: rainbowCursor 2s linear infinite;
        }

        /* Particle effect */
        .particles {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 1;
        }

        .particle {
            position: absolute;
            width: 2px;
            height: 2px;
            background: #00d4ff;
            border-radius: 50%;
            animation: float 6s linear infinite;
            box-shadow: 0 0 6px #00d4ff;
        }

        .particle.large {
            width: 4px;
            height: 4px;
            background: #0099ff;
            animation: floatLarge 8s linear infinite;
            box-shadow: 0 0 10px #0099ff;
        }

        .particle.small {
            width: 1px;
            height: 1px;
            background: #ffffff;
            animation: floatSmall 4s linear infinite;
            box-shadow: 0 0 3px #ffffff;
        }

        @keyframes float {
            0% {
                opacity: 0;
                transform: translateY(100vh) translateX(0) rotate(0deg);
            }
            10% {
                opacity: 1;
            }
            90% {
                opacity: 1;
            }
            100% {
                opacity: 0;
                transform: translateY(-10px) translateX(100px) rotate(360deg);
            }
        }

        @keyframes floatLarge {
            0% {
                opacity: 0;
                transform: translateY(100vh) translateX(-50px) rotate(0deg) scale(0.5);
            }
            10% {
                opacity: 0.8;
                transform: translateY(90vh) translateX(-45px) rotate(45deg) scale(1);
            }
            90% {
                opacity: 0.8;
                transform: translateY(10vh) translateX(45px) rotate(315deg) scale(1);
            }
            100% {
                opacity: 0;
                transform: translateY(-10px) translateX(50px) rotate(360deg) scale(0.5);
            }
        }

        @keyframes floatSmall {
            0% {
                opacity: 0;
                transform: translateY(100vh) translateX(20px);
            }
            15% {
                opacity: 0.6;
            }
            85% {
                opacity: 0.6;
            }
            100% {
                opacity: 0;
                transform: translateY(-10px) translateX(-20px);
            }
        }
    </style>
</head>
<body>
    <div class="bg-animation"></div>

    <!-- Custom Cursor -->
    <div class="custom-cursor" id="customCursor"></div>

    <!-- Cursor Trail -->
    <div class="cursor-trail" id="cursorTrail1"></div>
    <div class="cursor-trail" id="cursorTrail2"></div>
    <div class="cursor-trail" id="cursorTrail3"></div>

    <!-- Particles -->
    <div class="particles" id="particles"></div>

    <!-- Navigation -->
    <nav>
        <div class="nav-container">
            <div class="logo">GAME SERVER</div>
            <ul class="nav-links">
                <li><a href="/">ホーム</a></li>
                {% if session.username %}
                <li><a href="/profile">プロフィール</a></li>
                <li><a href="/minigame">😀 ミニゲーム</a></li>
                <li><a href="/discord">Discord</a></li>
                {% if user_data and user_data.role == '管理者' %}
                <li><a href="/admin">管理</a></li>
                {% endif %}
                <li><a href="/logout">ログアウト</a></li>
                {% else %}
                <li><a href="/login">ログイン</a></li>
                <li><a href="/register">新規登録</a></li>
                <li><a href="/discord">Discord</a></li>
                {% endif %}
            </ul>
        </div>
    </nav>

    <!-- Hero Section -->
    <section class="hero" id="home">
        <div class="hero-content">
            <h1>GAME SERVER</h1>
            <p>あなたの手元にゲームを</p>
            {% if session.username %}
            <p>ようこそ、{{ session.username }}さん！</p>
            {% endif %}
            <a href="#features" class="cta-button">詳細</a>
        </div>
    </section>

    <!-- Features Section -->
    <section class="features" id="features">
        <h2>最高の機能</h2>
        <div class="features-grid">
            <div class="feature-card">
                <div class="feature-icon">🎮</div>
                <h3>無料のゲーム</h3>
                <p>期間限定の無料ゲームをお伝えします</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">⚡</div>
                <h3>アップデート</h3>
                <p>ゲームの最新情報をお伝えします。</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">✔</div>
                <h3>最新</h3>
                <p>たくさんのゲームをお伝えします!!</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🌐</div>
                <h3>オンライン</h3>
                <p>世界中のプレイヤーと繋がり、ゲームを楽しめる。</p>
            </div>
        </div>
    </section>

    <!-- Stats Section -->
    <section class="stats" id="stats">
        <div class="stats-container">
            <div class="stat-item">
                <div class="stat-number" id="active-users">0</div>
                <div class="stat-label">
                    現在のアクティブユーザー
                </div>
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer>
        <p>&copy; 2025 GAME SERVER INC</p>
    </footer>

    <script>
        // マウス位置の追跡
        let mouseX = 0;
        let mouseY = 0;
        let particles = [];
        let particleCreationInterval = null;
        let largeParticleCreationInterval = null;

        // カスタムカーソル要素
        const customCursor = document.getElementById('customCursor');
        const cursorTrails = [
            document.getElementById('cursorTrail1'),
            document.getElementById('cursorTrail2'),
            document.getElementById('cursorTrail3')
        ];

        let trailPositions = [
            { x: 0, y: 0 },
            { x: 0, y: 0 },
            { x: 0, y: 0 }
        ];

        // カーソル効果の設定
        let currentCursorMode = 'normal'; // normal, glitch, rainbow, pulsing, rotating
        let cursorModeInterval = null;

        document.addEventListener('mousemove', (e) => {
            mouseX = e.clientX;
            mouseY = e.clientY;

            // カスタムカーソルの位置更新
            if (customCursor) {
                customCursor.style.left = mouseX - 10 + 'px';
                customCursor.style.top = mouseY - 10 + 'px';
            }

            // トレイル効果の更新
            updateCursorTrail();
        });

        // カーソルトレイルの更新
        function updateCursorTrail() {
            // 位置を遅延させてトレイル効果を作成
            setTimeout(() => {
                trailPositions[0] = { x: mouseX, y: mouseY };
                if (cursorTrails[0]) {
                    cursorTrails[0].style.left = trailPositions[0].x - 3 + 'px';
                    cursorTrails[0].style.top = trailPositions[0].y - 3 + 'px';
                }
            }, 50);

            setTimeout(() => {
                trailPositions[1] = { x: mouseX, y: mouseY };
                if (cursorTrails[1]) {
                    cursorTrails[1].style.left = trailPositions[1].x - 3 + 'px';
                    cursorTrails[1].style.top = trailPositions[1].y - 3 + 'px';
                }
            }, 100);

            setTimeout(() => {
                trailPositions[2] = { x: mouseX, y: mouseY };
                if (cursorTrails[2]) {
                    cursorTrails[2].style.left = trailPositions[2].x - 3 + 'px';
                    cursorTrails[2].style.top = trailPositions[2].y - 3 + 'px';
                }
            }, 150);
        }

        // マウスクリック時の効果
        document.addEventListener('mousedown', () => {
            if (customCursor) {
                customCursor.classList.add('clicking');
            }
        });

        document.addEventListener('mouseup', () => {
            if (customCursor) {
                customCursor.classList.remove('clicking');
            }
        });

        // ホバー効果
        document.addEventListener('mouseover', (e) => {
            if (e.target.matches('a, button, .play-button, .cta-button, .nav-links a')) {
                if (customCursor) {
                    customCursor.classList.add('hovering');
                }
            }
        });

        document.addEventListener('mouseout', (e) => {
            if (e.target.matches('a, button, .play-button, .cta-button, .nav-links a')) {
                if (customCursor) {
                    customCursor.classList.remove('hovering');
                }
            }
        });

        // カーソルモードの切り替え
        function changeCursorMode() {
            const modes = ['normal', 'glitch', 'rainbow', 'pulsing', 'rotating'];
            const randomMode = modes[Math.floor(Math.random() * modes.length)];

            if (customCursor) {
                // 前のクラスを削除
                customCursor.classList.remove('glitch', 'rainbow', 'pulsing', 'rotating');

                // 新しいクラスを追加
                if (randomMode !== 'normal') {
                    customCursor.classList.add(randomMode);
                }
            }

            currentCursorMode = randomMode;
        }

        // 10秒ごとにカーソルモードを変更
        cursorModeInterval = setInterval(changeCursorMode, 10000);

        // マグネット効果（ボタンに近づくとカーソルが引き寄せられる）
        function updateMagneticCursor() {
            const buttons = document.querySelectorAll('button, .play-button, .cta-button');
            let closestButton = null;
            let minDistance = Infinity;

            buttons.forEach(button => {
                const rect = button.getBoundingClientRect();
                const buttonCenterX = rect.left + rect.width / 2;
                const buttonCenterY = rect.top + rect.height / 2;
                const distance = Math.sqrt(
                    Math.pow(mouseX - buttonCenterX, 2) +
                    Math.pow(mouseY - buttonCenterY, 2)
                );

                if (distance < 100 && distance < minDistance) {
                    minDistance = distance;
                    closestButton = { x: buttonCenterX, y: buttonCenterY, distance };
                }
            });

            if (closestButton && customCursor) {
                const pullStrength = Math.max(0, (100 - closestButton.distance) / 100);
                const pullX = (closestButton.x - mouseX) * pullStrength * 0.3;
                const pullY = (closestButton.y - mouseY) * pullStrength * 0.3;

                customCursor.style.transform = `translate(${pullX}px, ${pullY}px)`;
                customCursor.classList.add('magnetic');
            } else if (customCursor) {
                customCursor.style.transform = 'translate(0, 0)';
                customCursor.classList.remove('magnetic');
            }
        }

        // マグネット効果を定期的に更新
        setInterval(updateMagneticCursor, 16); // 60fps

        // パーティクルクラス
        class InteractiveParticle {
            constructor(type) {
                this.element = document.createElement('div');
                this.type = type;
                this.x = Math.random() * window.innerWidth;
                this.y = window.innerHeight + 50;
                this.originalVx = (Math.random() - 0.5) * 2;
                this.originalVy = -(Math.random() * 2 + 1);
                this.vx = this.originalVx;
                this.vy = this.originalVy;
                this.life = 0;
                this.maxLife = this.getMaxLife();
                this.avoidDistance = this.getAvoidDistance();

                this.element.className = type;
                this.setupElement();
                document.getElementById('particles').appendChild(this.element);
            }

            getMaxLife() {
                if (this.type.includes('large')) return 400;
                if (this.type.includes('small')) return 200;
                return 300;
            }

            getAvoidDistance() {
                if (this.type.includes('large')) return 120;
                if (this.type.includes('small')) return 80;
                return 100;
            }

            setupElement() {
                this.element.style.position = 'absolute';
                this.element.style.left = this.x + 'px';
                this.element.style.top = this.y + 'px';
                this.element.style.pointerEvents = 'none';
                this.element.style.zIndex = '1';

                // アニメーションを無効化してJS制御に切り替え
                this.element.style.animation = 'none';
            }

            update() {
                // マウスとの距離を計算
                const dx = mouseX - this.x;
                const dy = mouseY - this.y;
                const distance = Math.sqrt(dx * dx + dy * dy);

                // マウスが近い場合の回避処理
                if (distance < this.avoidDistance && distance > 0) {
                    const avoidForce = (this.avoidDistance - distance) / this.avoidDistance;

                    // より強力な逃避力を適用
                    const escapeMultiplier = this.type.includes('large') ? 6 : this.type.includes('small') ? 4 : 5;
                    const avoidX = -(dx / distance) * avoidForce * escapeMultiplier;
                    const avoidY = -(dy / distance) * avoidForce * escapeMultiplier;

                    // スムーズな加速度の適用
                    this.vx = this.originalVx + avoidX;
                    this.vy = this.originalVy + avoidY;

                    // より派手なビジュアル効果
                    const scaleEffect = 1 + avoidForce * 0.8;
                    const rotationEffect = avoidForce * 180;
                    const glowEffect = 15 + avoidForce * 25;

                    this.element.style.transform = `scale(${scaleEffect}) rotate(${rotationEffect}deg)`;
                    this.element.style.boxShadow = `0 0 ${glowEffect}px currentColor`;

                    // 色の変化も追加
                    if (this.type.includes('large')) {
                        this.element.style.background = `hsl(${200 + avoidForce * 60}, 100%, 60%)`;
                    } else if (this.type.includes('small')) {
                        this.element.style.background = `hsl(${0 + avoidForce * 60}, 100%, 80%)`;
                    } else {
                        this.element.style.background = `hsl(${180 + avoidForce * 80}, 100%, 70%)`;
                    }
                } else {
                    // 元の動きに戻る（スムーズに減速）
                    this.vx = this.vx * 0.95 + this.originalVx * 0.05;
                    this.vy = this.vy * 0.95 + this.originalVy * 0.05;

                    this.element.style.transform = 'scale(1) rotate(0deg)';
                    this.element.style.boxShadow = '0 0 6px currentColor';

                    // 元の色に戻す
                    if (this.type.includes('large')) {
                        this.element.style.background = '#0099ff';
                    } else if (this.type.includes('small')) {
                        this.element.style.background = '#ffffff';
                    } else {
                        this.element.style.background = '#00d4ff';
                    }
                }

                // 位置を更新
                this.x += this.vx;
                this.y += this.vy;
                this.life++;

                // 透明度の制御
                const opacity = this.life < 20 ? this.life / 20 :
                               this.life > this.maxLife - 20 ? (this.maxLife - this.life) / 20 : 1;

                this.element.style.opacity = Math.max(0, Math.min(1, opacity));
                this.element.style.left = this.x + 'px';
                this.element.style.top = this.y + 'px';

                // 画面外または寿命が尽きた場合は削除
                return this.life < this.maxLife && this.y > -50 && this.x > -50 && this.x < window.innerWidth + 50;
            }

            destroy() {
                if (this.element && this.element.parentNode) {
                    this.element.parentNode.removeChild(this.element);
                }
            }
        }

        // パーティクル生成と更新
        function createParticle() {
            const types = ['particle', 'particle large', 'particle small'];
            const type = types[Math.floor(Math.random() * types.length)];
            const particle = new InteractiveParticle(type);
            particles.push(particle);
        }

        function updateParticles() {
            particles = particles.filter(particle => {
                if (!particle.update()) {
                    particle.destroy();
                    return false;
                }
                return true;
            });
            requestAnimationFrame(updateParticles);
        }

        // Smooth scrolling
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth'
                    });
                }
            });
        });

        // Parallax effect
        window.addEventListener('scroll', () => {
            const scrolled = window.pageYOffset;
            const parallax = document.querySelector('.bg-animation');
            const speed = scrolled * 0.5;
            parallax.style.transform = `translateY(${speed}px)`;
        });

        // スリープ状態の管理
        let isAsleep = false;

        // パーティクルシステムの開始
        function startParticleSystem() {
            if (particleCreationInterval) clearInterval(particleCreationInterval);
            if (largeParticleCreationInterval) clearInterval(largeParticleCreationInterval);

            particleCreationInterval = setInterval(createParticle, 800);

            // 大きなパーティクルを時々生成
            largeParticleCreationInterval = setInterval(() => {
                const particle = new InteractiveParticle('particle large');
                particles.push(particle);
            }, 3000);
        }

        // パーティクルシステムを開始
        startParticleSystem();

        // アニメーションループの開始
        updateParticles();

        // Real-time active users tracking
        function updateActiveUsers() {
            fetch('/heartbeat')
                .then(response => response.json())
                .then(data => {
                    const activeCount = data.active_users;
                    document.getElementById('active-users').textContent = activeCount;

                    // アクティブユーザーが0の場合はスリープ状態
                    if (activeCount === 0 && !isAsleep) {
                        enterSleepMode();
                    } else if (activeCount > 0 && isAsleep) {
                        exitSleepMode();
                    }
                })
                .catch(error => console.log('Error updating active users:', error));
        }

        // スリープモードに入る
        function enterSleepMode() {
            isAsleep = true;

            // パーティクル生成を停止
            if (particleCreationInterval) {
                clearInterval(particleCreationInterval);
            }
            if (largeParticleCreationInterval) {
                clearInterval(largeParticleCreationInterval);
            }

            // 既存のパーティクルを徐々に削除
            particles.forEach(particle => {
                particle.maxLife = Math.min(particle.maxLife, particle.life + 100);
            });
        }

        // スリープモードから復帰
        function exitSleepMode() {
            isAsleep = false;

            // パーティクル生成を再開
            startParticleSystem();
        }

        // 初回実行
        updateActiveUsers();

        // 15秒ごとに更新
        setInterval(updateActiveUsers, 15000);

        // Scroll animations
        function animateOnScroll() {
            const elementsToAnimate = document.querySelectorAll('.feature-card, .features h2');

            elementsToAnimate.forEach(element => {
                const elementTop = element.getBoundingClientRect().top;
                const elementVisible = 150;

                if (elementTop < window.innerHeight - elementVisible) {
                    element.classList.add('animate');
                }
            });
        }

        // 初回チェック
        animateOnScroll();

        // スクロール時にアニメーションをチェック
        window.addEventListener('scroll', animateOnScroll);

        // 各カードに遅延を追加
        document.addEventListener('DOMContentLoaded', function() {
            const featureCards = document.querySelectorAll('.feature-card');
            featureCards.forEach((card, index) => {
                card.style.transitionDelay = `${index * 0.1}s`;
            });
        });
    </script>
</body>
</html>
"""

register_template = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>新規登録 - GAME SERVER</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Orbitron', monospace;
            background: #0a0a0a;
            color: #ffffff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .bg-animation {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(45deg, #0a0a0a, #1a2e42, #163e42);
            background-size: 400% 400%;
            animation: gradientShift 15s ease infinite;
            z-index: -1;
        }

        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        .container {
            background: rgba(255, 255, 255, 0.05);
            padding: 3rem;
            border-radius: 15px;
            border: 1px solid rgba(0, 212, 255, 0.3);
            backdrop-filter: blur(10px);
            text-align: center;
            max-width: 400px;
            width: 90%;
        }

        .register-icon {
            font-size: 4rem;
            color: #00d4ff;
            margin-bottom: 1rem;
        }

        h1 {
            font-size: 2.5rem;
            margin-bottom: 2rem;
            background: linear-gradient(45deg, #0099ff, #00d4ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .form-group {
            margin-bottom: 1.5rem;
            text-align: left;
        }

        label {
            display: block;
            margin-bottom: 0.5rem;
            color: #00d4ff;
            font-weight: 700;
        }

        input[type="text"], input[type="email"], input[type="password"] {
            width: 100%;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(0, 212, 255, 0.3);
            border-radius: 8px;
            color: #ffffff;
            font-family: 'Orbitron', monospace;
            font-size: 1rem;
            transition: border-color 0.3s ease;
        }

        input[type="text"]:focus, input[type="email"]:focus, input[type="password"]:focus {
            outline: none;
            border-color: #00d4ff;
            box-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
        }

        .register-button {
            width: 100%;
            padding: 1rem 2rem;
            background: linear-gradient(45deg, #0099ff, #00d4ff);
            color: #000;
            border: none;
            border-radius: 8px;
            font-weight: 700;
            font-family: 'Orbitron', monospace;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 10px 30px rgba(0, 153, 255, 0.3);
        }

        .register-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 15px 40px rgba(0, 153, 255, 0.5);
        }

        .back-button {
            display: inline-block;
            margin-top: 1rem;
            padding: 0.8rem 1.5rem;
            background: transparent;
            color: #00d4ff;
            text-decoration: none;
            border: 2px solid #00d4ff;
            border-radius: 25px;
            transition: all 0.3s ease;
        }

        .back-button:hover {
            background: #00d4ff;
            color: #000;
        }

        .error-message {
            background: rgba(255, 107, 107, 0.1);
            border: 1px solid #ff6b6b;
            color: #ff6b6b;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
    </style>
</head>
<body>
    <div class="bg-animation"></div>

    <div class="container">
        <div class="register-icon">📝</div>
        <h1>新規登録</h1>

        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="error-message">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <form method="POST">
            <div class="form-group">
                <label for="username">ユーザー名:</label>
                <input type="text" id="username" name="username" required value="{{ form_data.username if form_data else '' }}">
            </div>

            <div class="form-group">
                <label for="user_id">ユーザーID:</label>
                <input type="text" id="user_id" name="user_id" required value="{{ form_data.user_id if form_data else '' }}">
            </div>

            <div class="form-group">
                <label for="email">メールアドレス:</label>
                <input type="email" id="email" name="email" required value="{{ form_data.email if form_data else '' }}">
            </div>

            <div class="form-group">
                <label for="password">パスワード:</label>
                <input type="password" id="password" name="password" required>
            </div>

            <button type="submit" class="register-button">登録</button>
        </form>

        <a href="/login" class="back-button">ログインに戻る</a>
        <a href="/" class="back-button">ホームに戻る</a>
    </div>
</body>
</html>
"""

login_template = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ログイン - GAME SERVER</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Orbitron', monospace;
            background: #0a0a0a;
            color: #ffffff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .bg-animation {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(45deg, #0a0a0a, #1a2e42, #163e42);
            background-size: 400% 400%;
            animation: gradientShift 15s ease infinite;
            z-index: -1;
        }

        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        .container {
            background: rgba(255, 255, 255, 0.05);
            padding: 3rem;
            border-radius: 15px;
            border: 1px solid rgba(0, 212, 255, 0.3);
            backdrop-filter: blur(10px);
            text-align: center;
            max-width: 400px;
            width: 90%;
        }

        .login-icon {
            font-size: 4rem;
            color: #00d4ff;
            margin-bottom: 1rem;
        }

        h1 {
            font-size: 2.5rem;
            margin-bottom: 2rem;
            background: linear-gradient(45deg, #0099ff, #00d4ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .form-group {
            margin-bottom: 1.5rem;
            text-align: left;
        }

        label {
            display: block;
            margin-bottom: 0.5rem;
            color: #00d4ff;
            font-weight: 700;
        }

        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(0, 212, 255, 0.3);
            border-radius: 8px;
            color: #ffffff;
            font-family: 'Orbitron', monospace;
            font-size: 1rem;
            transition: border-color 0.3s ease;
        }

        input[type="text"]:focus, input[type="password"]:focus {
            outline: none;
            border-color: #00d4ff;
            box-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
        }

        .login-button {
            width: 100%;
            padding: 1rem 2rem;
            background: linear-gradient(45deg, #0099ff, #00d4ff);
            color: #000;
            border: none;
            border-radius: 8px;
            font-weight: 700;
            font-family: 'Orbitron', monospace;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 10px 30px rgba(0, 153, 255, 0.3);
        }

        .login-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 15px 40px rgba(0, 153, 255, 0.5);
        }

        .back-button {
            display: inline-block;
            margin-top: 1rem;
            padding: 0.8rem 1.5rem;
            background: transparent;
            color: #00d4ff;
            text-decoration: none;
            border: 2px solid #00d4ff;
            border-radius: 25px;
            transition: all 0.3s ease;
        }

        .back-button:hover {
            background: #00d4ff;
            color: #000;
        }

        .error-message {
            background: rgba(255, 107, 107, 0.1);
            border: 1px solid #ff6b6b;
            color: #ff6b6b;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }

        .demo-accounts {
            margin-top: 2rem;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 8px;
            border: 1px solid rgba(0, 212, 255, 0.2);
        }

        .demo-accounts h3 {
            color: #00d4ff;
            margin-bottom: 1rem;
            font-size: 1rem;
        }

        .demo-accounts p {
            font-size: 0.8rem;
            opacity: 0.8;
            margin-bottom: 0.5rem;
            text-align: left;
        }
    </style>
</head>
<body>
    <div class="bg-animation"></div>

    <div class="container">
        <div class="login-icon">🔐</div>
        <h1>ログイン</h1>

        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="error-message">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <form method="POST">
            <div class="form-group">
                <label for="username">ユーザー名:</label>
                <input type="text" id="username" name="username" required>
            </div>

            <div class="form-group">
                <label for="password">パスワード:</label>
                <input type="password" id="password" name="password" required>
            </div>

            <div class="form-group" style="flex-direction: row; justify-content: flex-start; align-items: center; gap: 0.5rem;">
                <input type="checkbox" id="remember_me" name="remember_me" style="width: auto; margin: 0;">
                <label for="remember_me" style="margin: 0; cursor: pointer;">ログインを保存する（30日間）</label>
            </div>

            <button type="submit" class="login-button">ログイン</button>
        </form>

        <a href="/" class="back-button">ホームに戻る</a>
        <a href="/register" class="back-button">新規登録</a>
    </div>
</body>
</html>
"""

discord_template = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Discord - GAME SERVER</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Orbitron', monospace;
            background: #0a0a0a;
            color: #ffffff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .bg-animation {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(45deg, #0a0a0a, #1a2e42, #163e42);
            background-size: 400% 400%;
            animation: gradientShift 15s ease infinite;
            z-index: -1;
        }

        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        .container {
            background: rgba(255, 255, 255, 0.05);
            padding: 3rem;
            border-radius: 15px;
            border: 1px solid rgba(0, 212, 255, 0.3);
            backdrop-filter: blur(10px);
            text-align: center;
            max-width: 500px;
            width: 90%;
        }

        .discord-icon {
            font-size: 4rem;
            color: #5865F2;
            margin-bottom: 1rem;
        }

        h1 {
            font-size: 2.5rem;
            margin-bottom: 1rem;
            background: linear-gradient(45deg, #0099ff, #00d4ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        p {
            margin-bottom: 2rem;
            opacity: 0.8;
            line-height: 1.6;
        }

        .discord-button {
            display: inline-block;
            padding: 1rem 2rem;
            background: #5865F2;
            color: white;
            text-decoration: none;
            border-radius: 50px;
            font-weight: 700;
            transition: all 0.3s ease;
            box-shadow: 0 10px 30px rgba(88, 101, 242, 0.3);
        }

        .discord-button:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(88, 101, 242, 0.5);
        }

        .back-button {
            display: inline-block;
            margin-top: 1rem;
            padding: 0.8rem 1.5rem;
            background: transparent;
            color: #00d4ff;
            text-decoration: none;
            border: 2px solid #00d4ff;
            border-radius: 25px;
            transition: all 0.3s ease;
        }

        .back-button:hover {
            background: #00d4ff;
            color: #000;
        }
    </style>
</head>
<body>
    <div class="bg-animation"></div>

    <div class="container">
        <div class="discord-icon">💬</div>
        <h1>Discord コミュニティ</h1>
        <p>GAME SERVERの公式Discordサーバーに参加して、他のプレイヤーと交流しましょう！</p>
        <p>最新のゲームを楽しみましょう!</p>

        <a href="https://discord.gg/2CWewd3WAd" class="discord-button" target="_blank">Discordに参加</a>
        <br>
        <a href="/" class="back-button">ホームに戻る</a>
    </div>
</body>
</html>
"""

minigame_template = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>😀 ミニゲーム - GAME SERVER</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Orbitron', monospace;
            background: #0a0a0a;
            color: #ffffff;
            min-height: 100vh;
            padding: 80px 20px 20px;
        }

        .bg-animation {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(45deg, #0a0a0a, #1a2e42, #163e42);
            background-size: 400% 400%;
            animation: gradientShift 15s ease infinite;
            z-index: -1;
        }

        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        nav {
            position: fixed;
            top: 0;
            width: 100%;
            padding: 1rem 2rem;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(10px);
            z-index: 1000;
            border-bottom: 2px solid #00d4ff;
        }

        .nav-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            max-width: 1200px;
            margin: 0 auto;
        }

        .logo {
            font-size: 1.8rem;
            font-weight: 900;
            color: #00d4ff;
            text-shadow: 0 0 20px #00d4ff;
        }

        .nav-links {
            display: flex;
            gap: 2rem;
            list-style: none;
        }

        .nav-links a {
            color: #ffffff;
            text-decoration: none;
            transition: all 0.3s ease;
            padding: 0.5rem 1rem;
            border-radius: 5px;
        }

        .nav-links a:hover {
            color: #00d4ff;
            background: rgba(0, 212, 255, 0.1);
            transform: translateY(-2px);
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            text-align: center;
        }

        h1 {
            font-size: 3rem;
            margin-bottom: 2rem;
            background: linear-gradient(45deg, #0099ff, #00d4ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .game-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin: 3rem 0;
        }

        .game-card {
            background: rgba(255, 255, 255, 0.05);
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid rgba(0, 212, 255, 0.3);
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }

        .game-card:hover {
            transform: translateY(-10px);
            border-color: #00d4ff;
            box-shadow: 0 20px 40px rgba(0, 212, 255, 0.3);
        }

        .game-icon {
            font-size: 4rem;
            margin-bottom: 1rem;
        }

        .game-title {
            font-size: 1.5rem;
            color: #00d4ff;
            margin-bottom: 1rem;
        }

        .game-description {
            opacity: 0.8;
            margin-bottom: 2rem;
            line-height: 1.5;
        }

        .play-button {
            padding: 1rem 2rem;
            background: linear-gradient(45deg, #0099ff, #00d4ff);
            color: #000;
            border: none;
            border-radius: 50px;
            font-weight: 700;
            font-family: 'Orbitron', monospace;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 10px 30px rgba(0, 153, 255, 0.3);
        }

        .play-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 15px 40px rgba(0, 153, 255, 0.5);
        }

        .back-button {
            display: inline-block;
            margin-top: 2rem;
            padding: 0.8rem 1.5rem;
            background: transparent;
            color: #00d4ff;
            text-decoration: none;
            border: 2px solid #00d4ff;
            border-radius: 25px;
            transition: all 0.3s ease;
        }

        .back-button:hover {
            background: #00d4ff;
            color: #000;
        }

        /* ゲームエリア */
        .game-area {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 2rem;
            margin: 2rem 0;
            border: 1px solid rgba(0, 212, 255, 0.3);
            display: none;
        }

        .game-area.active {
            display: block;
        }

        .memory-game {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            max-width: 400px;
            margin: 0 auto;
        }

        .memory-card {
            width: 80px;
            height: 80px;
            background: rgba(0, 212, 255, 0.2);
            border: 2px solid #00d4ff;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .memory-card:hover {
            background: rgba(0, 212, 255, 0.4);
        }

        .memory-card.flipped {
            background: #00d4ff;
            color: #000;
        }

        .memory-card.matched {
            background: #00ff88;
            color: #000;
            cursor: default;
        }

        .game-stats {
            margin: 1rem 0;
            font-size: 1.2rem;
        }

        .score {
            color: #00d4ff;
        }
    </style>
</head>
<body>
    <div class="bg-animation"></div>

    <nav>
        <div class="nav-container">
            <div class="logo">GAME SERVER</div>
            <ul class="nav-links">
                <li><a href="/">ホーム</a></li>
                <li><a href="/profile">プロフィール</a></li>
                <li><a href="/minigame" style="color: #00d4ff;">😀 ミニゲーム</a></li>
                <li><a href="/discord">Discord</a></li>
            </ul>
        </div>
    </nav>

    <div class="container">
        <h1>😀 ミニゲーム</h1>
        <p>楽しいミニゲームで遊んでみよう！</p>

        <div class="game-grid">
            <div class="game-card">
                <div class="game-icon">🧠</div>
                <div class="game-title">記憶ゲーム</div>
                <div class="game-description">カードをめくって同じ絵柄のペアを見つけよう！</div>
                <button class="play-button" onclick="startMemoryGame()">プレイ</button>
            </div>

            <div class="game-card">
                <div class="game-icon">🎲</div>
                <div class="game-title">数字当てゲーム</div>
                <div class="game-description">1〜100の数字を当ててみよう！</div>
                <button class="play-button" onclick="startNumberGame()">プレイ</button>
            </div>

            <div class="game-card">
                <div class="game-icon">✂️</div>
                <div class="game-title">じゃんけんゲーム</div>
                <div class="game-description">コンピューターとじゃんけん勝負！</div>
                <button class="play-button" onclick="startRockPaperScissors()">プレイ</button>
            </div>

            <div class="game-card">
                <div class="game-icon">❓</div>
                <div class="game-title">クイズゲーム</div>
                <div class="game-description">様々な問題に挑戦しよう！</div>
                <button class="play-button" onclick="startQuizGame()">プレイ</button>
            </div>

            <div class="game-card">
                <div class="game-icon">🎨</div>
                <div class="game-title">カラーマッチング</div>
                <div class="game-description">色の名前と実際の色を素早く合わせよう！</div>
                <button class="play-button" onclick="startColorGame()">プレイ</button>
            </div>

            <div class="game-card">
                <div class="game-icon">⚡</div>
                <div class="game-title">リアクションゲーム</div>
                <div class="game-description">緑色になったらすぐにクリック！</div>
                <button class="play-button" onclick="startReactionGame()">プレイ</button>
            </div>
        </div>

        <!-- 記憶ゲームエリア -->
        <div id="memory-game-area" class="game-area">
            <h2>🧠 記憶ゲーム</h2>
            <div class="game-stats">
                <span>スコア: <span class="score" id="memory-score">0</span></span>
                <span style="margin-left: 2rem;">試行回数: <span class="score" id="memory-attempts">0</span></span>
            </div>
            <div id="memory-game" class="memory-game"></div>
            <button class="play-button" onclick="resetMemoryGame()" style="margin-top: 1rem;">リセット</button>
            <button class="play-button" onclick="hideGame()" style="margin-top: 1rem; background: #ff6b6b;">戻る</button>
        </div>

        <!-- 数字当てゲームエリア -->
        <div id="number-game-area" class="game-area">
            <h2>🎲 数字当てゲーム</h2>
            <p>1〜100の数字を考えました。当ててみてください！</p>
            <div style="margin: 2rem 0;">
                <input type="number" id="number-input" min="1" max="100" placeholder="数字を入力"
                       style="padding: 1rem; font-size: 1rem; border-radius: 8px; border: 1px solid #00d4ff; background: rgba(255,255,255,0.1); color: white;">
                <button class="play-button" onclick="guessNumber()" style="margin-left: 1rem;">予想</button>
            </div>
            <div id="number-result" style="margin: 1rem 0; font-size: 1.2rem;"></div>
            <div class="game-stats">
                <span>試行回数: <span class="score" id="number-attempts">0</span></span>
            </div>
            <button class="play-button" onclick="resetNumberGame()" style="margin-top: 1rem;">リセット</button>
            <button class="play-button" onclick="hideGame()" style="margin-top: 1rem; background: #ff6b6b;">戻る</button>
        </div>

        <!-- じゃんけんゲームエリア -->
        <div id="rps-game-area" class="game-area">
            <h2>✂️ じゃんけんゲーム</h2>
            <div class="game-stats">
                <span>勝ち: <span class="score" id="rps-wins">0</span></span>
                <span style="margin: 0 1rem;">負け: <span class="score" id="rps-losses">0</span></span>
                <span>引き分け: <span class="score" id="rps-draws">0</span></span>
            </div>
            <div style="margin: 2rem 0;">
                <button class="play-button" onclick="playRPS('rock')" style="margin: 0.5rem;">✊ グー</button>
                <button class="play-button" onclick="playRPS('paper')" style="margin: 0.5rem;">✋ パー</button>
                <button class="play-button" onclick="playRPS('scissors')" style="margin: 0.5rem;">✌️ チョキ</button>
            </div>
            <div id="rps-result" style="margin: 1rem 0; font-size: 1.5rem;"></div>
            <button class="play-button" onclick="resetRPSGame()" style="margin-top: 1rem;">リセット</button>
            <button class="play-button" onclick="hideGame()" style="margin-top: 1rem; background: #ff6b6b;">戻る</button>
        </div>

        <!-- クイズゲームエリア -->
        <div id="quiz-game-area" class="game-area">
            <h2>❓ クイズゲーム</h2>
            <div class="game-stats">
                <span>スコア: <span class="score" id="quiz-score">0</span></span>
                <span style="margin-left: 2rem;">問題: <span class="score" id="quiz-current">1</span> / <span id="quiz-total">10</span></span>
            </div>
            <div id="quiz-question" style="font-size: 1.3rem; margin: 2rem 0; min-height: 100px; display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,0.05); border-radius: 10px; padding: 1rem;"></div>
            <div id="quiz-options" style="margin: 2rem 0;"></div>
            <div id="quiz-result" style="margin: 1rem 0; font-size: 1.2rem; min-height: 30px;"></div>
            <button class="play-button" onclick="resetQuizGame()" style="margin-top: 1rem;">リセット</button>
            <button class="play-button" onclick="hideGame()" style="margin-top: 1rem; background: #ff6b6b;">戻る</button>
        </div>

        <!-- カラーマッチングゲームエリア -->
        <div id="color-game-area" class="game-area">
            <h2>🎨 カラーマッチング</h2>
            <div class="game-stats">
                <span>スコア: <span class="score" id="color-score">0</span></span>
                <span style="margin: 0 1rem;">時間: <span class="score" id="color-time">30</span>秒</span>
                <span>コンボ: <span class="score" id="color-combo">0</span></span>
            </div>
            <div id="color-display" style="font-size: 3rem; margin: 2rem 0; min-height: 120px; display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,0.05); border-radius: 15px; padding: 2rem;"></div>
            <div id="color-options" style="margin: 2rem 0;"></div>
            <div id="color-result" style="margin: 1rem 0; font-size: 1.2rem; min-height: 30px;"></div>
            <button class="play-button" onclick="startColorGameRound()" style="margin-top: 1rem;">スタート</button>
            <button class="play-button" onclick="hideGame()" style="margin-top: 1rem; background: #ff6b6b;">戻る</button>
        </div>

        <!-- リアクションゲームエリア -->
        <div id="reaction-game-area" class="game-area">
            <h2>⚡ リアクションゲーム</h2>
            <div class="game-stats">
                <span>最高記録: <span class="score" id="reaction-best">-</span>ms</span>
                <span style="margin-left: 2rem;">試行回数: <span class="score" id="reaction-attempts">0</span></span>
            </div>
            <div id="reaction-display" style="width: 300px; height: 300px; margin: 2rem auto; border-radius: 15px; display: flex; align-items: center; justify-content: center; font-size: 2rem; font-weight: bold; cursor: pointer; transition: all 0.3s ease; background: #333; border: 3px solid #555;"></div>
            <div id="reaction-result" style="margin: 1rem 0; font-size: 1.2rem; min-height: 30px;"></div>
            <button class="play-button" onclick="startReactionRound()" style="margin-top: 1rem;">スタート</button>
            <button class="play-button" onclick="resetReactionGame()" style="margin-top: 1rem;">リセット</button>
            <button class="play-button" onclick="hideGame()" style="margin-top: 1rem; background: #ff6b6b;">戻る</button>
        </div>

        <a href="/" class="back-button">ホームに戻る</a>
    </div>

    <script>
        // 記憶ゲーム
        let memoryCards = [];
        let flippedCards = [];
        let matchedPairs = 0;
        let memoryScore = 0;
        let memoryAttempts = 0;
        const memorySymbols = ['🌟', '🎈', '🎮', '🎯', '🎨', '🎪', '🎭', '🎸'];

        function startMemoryGame() {
            document.getElementById('memory-game-area').classList.add('active');
            initMemoryGame();
        }

        function initMemoryGame() {
            const gameBoard = document.getElementById('memory-game');
            gameBoard.innerHTML = '';
            memoryCards = [...memorySymbols, ...memorySymbols];
            memoryCards.sort(() => Math.random() - 0.5);
            flippedCards = [];
            matchedPairs = 0;
            memoryScore = 0;
            memoryAttempts = 0;
            updateMemoryStats();

            memoryCards.forEach((symbol, index) => {
                const card = document.createElement('div');
                card.className = 'memory-card';
                card.dataset.symbol = symbol;
                card.dataset.index = index;
                card.addEventListener('click', flipCard);
                gameBoard.appendChild(card);
            });
        }

        function flipCard(e) {
            const card = e.target;
            if (card.classList.contains('flipped') || card.classList.contains('matched') || flippedCards.length >= 2) {
                return;
            }

            card.classList.add('flipped');
            card.textContent = card.dataset.symbol;
            flippedCards.push(card);

            if (flippedCards.length === 2) {
                memoryAttempts++;
                updateMemoryStats();
                setTimeout(checkMatch, 1000);
            }
        }

        function checkMatch() {
            const [card1, card2] = flippedCards;
            if (card1.dataset.symbol === card2.dataset.symbol) {
                card1.classList.add('matched');
                card2.classList.add('matched');
                matchedPairs++;
                memoryScore += 10;
                if (matchedPairs === memorySymbols.length) {
                    setTimeout(() => alert('おめでとう！ゲームクリア！'), 500);
                }
            } else {
                card1.classList.remove('flipped');
                card2.classList.remove('flipped');
                card1.textContent = '';
                card2.textContent = '';
            }
            flippedCards = [];
            updateMemoryStats();
        }

        function updateMemoryStats() {
            document.getElementById('memory-score').textContent = memoryScore;
            document.getElementById('memory-attempts').textContent = memoryAttempts;
        }

        function resetMemoryGame() {
            initMemoryGame();
        }

        // 数字当てゲーム
        let targetNumber = 0;
        let numberAttempts = 0;

        function startNumberGame() {
            document.getElementById('number-game-area').classList.add('active');
            resetNumberGame();
        }

        function resetNumberGame() {
            targetNumber = Math.floor(Math.random() * 100) + 1;
            numberAttempts = 0;
            document.getElementById('number-input').value = '';
            document.getElementById('number-result').textContent = '';
            document.getElementById('number-attempts').textContent = '0';
        }

        function guessNumber() {
            const input = document.getElementById('number-input');
            const guess = parseInt(input.value);
            const result = document.getElementById('number-result');

            if (isNaN(guess) || guess < 1 || guess > 100) {
                result.textContent = '1〜100の数字を入力してください';
                result.style.color = '#ff6b6b';
                return;
            }

            numberAttempts++;
            document.getElementById('number-attempts').textContent = numberAttempts;

            if (guess === targetNumber) {
                result.textContent = `🎉 正解！${numberAttempts}回で当てました！`;
                result.style.color = '#00ff88';
            } else if (guess < targetNumber) {
                result.textContent = '📈 もっと大きい数字です';
                result.style.color = '#00d4ff';
            } else {
                result.textContent = '📉 もっと小さい数字です';
                result.style.color = '#00d4ff';
            }
        }

        // じゃんけんゲーム
        let rpsWins = 0;
        let rpsLosses = 0;
        let rpsDraws = 0;

        function startRockPaperScissors() {
            document.getElementById('rps-game-area').classList.add('active');
        }

        function playRPS(playerChoice) {
            const choices = ['rock', 'paper', 'scissors'];
            const emojis = { rock: '✊', paper: '✋', scissors: '✌️' };
            const computerChoice = choices[Math.floor(Math.random() * 3)];
            const result = document.getElementById('rps-result');

            let outcome = '';
            if (playerChoice === computerChoice) {
                outcome = '引き分け';
                rpsDraws++;
            } else if (
                (playerChoice === 'rock' && computerChoice === 'scissors') ||
                (playerChoice === 'paper' && computerChoice === 'rock') ||
                (playerChoice === 'scissors' && computerChoice === 'paper')
            ) {
                outcome = 'あなたの勝ち！';
                rpsWins++;
            } else {
                outcome = 'あなたの負け...';
                rpsLosses++;
            }

            result.innerHTML = `
                あなた: ${emojis[playerChoice]} vs コンピューター: ${emojis[computerChoice]}<br>
                <span style="color: ${outcome.includes('勝ち') ? '#00ff88' : outcome.includes('負け') ? '#ff6b6b' : '#00d4ff'}">${outcome}</span>
            `;

            updateRPSStats();
        }

        function updateRPSStats() {
            document.getElementById('rps-wins').textContent = rpsWins;
            document.getElementById('rps-losses').textContent = rpsLosses;
            document.getElementById('rps-draws').textContent = rpsDraws;
        }

        function resetRPSGame() {
            rpsWins = 0;
            rpsLosses = 0;
            rpsDraws = 0;
            updateRPSStats();
            document.getElementById('rps-result').textContent = '';
        }

        function hideGame() {
            document.querySelectorAll('.game-area').forEach(area => {
                area.classList.remove('active');
            });
        }

        // クイズゲーム
        let quizQuestions = [
            { question: "日本の首都は？", options: ["東京", "大阪", "京都", "名古屋"], correct: 0 },
            { question: "1 + 1 = ?", options: ["1", "2", "3", "4"], correct: 1 },
            { question: "地球で一番大きい海は？", options: ["大西洋", "太平洋", "インド洋", "北極海"], correct: 1 },
            { question: "人間の骨の数は約何本？", options: ["150本", "200本", "250本", "300本"], correct: 1 },
            { question: "富士山の高さは？", options: ["3776m", "3500m", "4000m", "3200m"], correct: 0 },
            { question: "日本で一番長い川は？", options: ["利根川", "信濃川", "石狩川", "北上川"], correct: 1 },
            { question: "光の速度は？", options: ["約30万km/s", "約20万km/s", "約40万km/s", "約10万km/s"], correct: 0 },
            { question: "虹は何色？", options: ["5色", "6色", "7色", "8色"], correct: 2 },
            { question: "一年は何日？", options: ["364日", "365日", "366日", "367日"], correct: 1 },
            { question: "日本の県の数は？", options: ["45", "46", "47", "48"], correct: 2 }
        ];
        let currentQuiz = 0;
        let quizScore = 0;
        let shuffledQuiz = [];

        function startQuizGame() {
            document.getElementById('quiz-game-area').classList.add('active');
            resetQuizGame();
        }

        function resetQuizGame() {
            shuffledQuiz = [...quizQuestions].sort(() => Math.random() - 0.5);
            currentQuiz = 0;
            quizScore = 0;
            updateQuizStats();
            showQuizQuestion();
        }

        function updateQuizStats() {
            document.getElementById('quiz-score').textContent = quizScore;
            document.getElementById('quiz-current').textContent = currentQuiz + 1;
            document.getElementById('quiz-total').textContent = shuffledQuiz.length;
        }

        function showQuizQuestion() {
            if (currentQuiz >= shuffledQuiz.length) {
                document.getElementById('quiz-question').innerHTML = `ゲーム終了！<br>最終スコア: ${quizScore}/${shuffledQuiz.length}`;
                document.getElementById('quiz-options').innerHTML = '';
                document.getElementById('quiz-result').textContent = '';
                return;
            }

            const question = shuffledQuiz[currentQuiz];
            document.getElementById('quiz-question').textContent = question.question;
            document.getElementById('quiz-result').textContent = '';

            const optionsHtml = question.options.map((option, index) =>
                `<button class="play-button" onclick="answerQuiz(${index})" style="margin: 0.5rem; display: block; width: 80%; margin-left: auto; margin-right: auto;">${option}</button>`
            ).join('');
            document.getElementById('quiz-options').innerHTML = optionsHtml;
        }

        function answerQuiz(selectedIndex) {
            const question = shuffledQuiz[currentQuiz];
            const result = document.getElementById('quiz-result');

            if (selectedIndex === question.correct) {
                result.innerHTML = '🎉 正解！';
                result.style.color = '#00ff88';
                quizScore++;
            } else {
                result.innerHTML = `❌ 不正解。正解は「${question.options[question.correct]}」です。`;
                result.style.color = '#ff6b6b';
            }

            currentQuiz++;
            updateQuizStats();

            setTimeout(() => {
                showQuizQuestion();
            }, 2000);
        }

        // カラーマッチングゲーム
        let colorScore = 0;
        let colorTime = 30;
        let colorCombo = 0;
        let colorGameInterval = null;
        let currentColor = null;
        let colorGameActive = false;

        const colors = [
            { name: '赤', color: '#ff0000', bg: '#ff0000' },
            { name: '青', color: '#0000ff', bg: '#0000ff' },
            { name: '緑', color: '#00ff00', bg: '#00ff00' },
            { name: '黄', color: '#ffff00', bg: '#ffff00' },
            { name: '紫', color: '#ff00ff', bg: '#ff00ff' },
            { name: '橙', color: '#ff8000', bg: '#ff8000' },
            { name: '桃', color: '#ff69b4', bg: '#ff69b4' },
            { name: '茶', color: '#8b4513', bg: '#8b4513' }
        ];

        function startColorGame() {
            document.getElementById('color-game-area').classList.add('active');
        }

        function startColorGameRound() {
            colorScore = 0;
            colorTime = 30;
            colorCombo = 0;
            colorGameActive = true;
            updateColorStats();

            colorGameInterval = setInterval(() => {
                colorTime--;
                updateColorStats();
                if (colorTime <= 0) {
                    endColorGame();
                }
            }, 1000);

            showNextColor();
        }

        function showNextColor() {
            if (!colorGameActive) return;

            // ランダムな色を選択
            const randomColor = colors[Math.floor(Math.random() * colors.length)];
            // 表示する色名をランダムに選択（正解または不正解）
            const displayColor = Math.random() < 0.7 ? randomColor : colors[Math.floor(Math.random() * colors.length)];

            currentColor = {
                correct: randomColor,
                display: displayColor,
                isMatch: randomColor === displayColor
            };

            document.getElementById('color-display').innerHTML = `<span style="color: ${randomColor.bg}">${displayColor.name}</span>`;

            const optionsHtml = `
                <button class="play-button" onclick="answerColor(true)" style="margin: 0.5rem; background: #00ff88;">一致</button>
                <button class="play-button" onclick="answerColor(false)" style="margin: 0.5rem; background: #ff6b6b;">不一致</button>
            `;
            document.getElementById('color-options').innerHTML = optionsHtml;
        }

        function answerColor(userAnswer) {
            if (!colorGameActive) return;

            const result = document.getElementById('color-result');
            if (userAnswer === currentColor.isMatch) {
                colorScore += (1 + colorCombo);
                colorCombo++;
                result.innerHTML = `✅ 正解！ +${1 + colorCombo - 1}点`;
                result.style.color = '#00ff88';
            } else {
                colorCombo = 0;
                result.innerHTML = '❌ 不正解！';
                result.style.color = '#ff6b6b';
            }

            updateColorStats();
            setTimeout(showNextColor, 800);
        }

        function updateColorStats() {
            document.getElementById('color-score').textContent = colorScore;
            document.getElementById('color-time').textContent = colorTime;
            document.getElementById('color-combo').textContent = colorCombo;
        }

        function endColorGame() {
            colorGameActive = false;
            clearInterval(colorGameInterval);
            document.getElementById('color-display').innerHTML = `ゲーム終了！<br>スコア: ${colorScore}点`;
            document.getElementById('color-options').innerHTML = '';
            document.getElementById('color-result').innerHTML = '';
        }

        // リアクションゲーム
        let reactionStartTime = 0;
        let reactionTimeout = null;
        let reactionWaiting = false;
        let reactionBestTime = null;
        let reactionAttempts = 0;

        function startReactionGame() {
            document.getElementById('reaction-game-area').classList.add('active');
        }

        function startReactionRound() {
            const display = document.getElementById('reaction-display');
            display.style.background = '#ff6b6b';
            display.style.borderColor = '#ff6b6b';
            display.textContent = '待機...';
            display.onclick = null;
            reactionWaiting = false;

            document.getElementById('reaction-result').textContent = '';

            // 1-5秒後にランダムで緑色に変更
            const delay = Math.random() * 4000 + 1000;
            reactionTimeout = setTimeout(() => {
                display.style.background = '#00ff88';
                display.style.borderColor = '#00ff88';
                display.textContent = 'クリック！';
                reactionStartTime = Date.now();
                reactionWaiting = true;

                display.onclick = function() {
                    if (reactionWaiting) {
                        const reactionTime = Date.now() - reactionStartTime;
                        reactionAttempts++;

                        if (!reactionBestTime || reactionTime < reactionBestTime) {
                            reactionBestTime = reactionTime;
                        }

                        display.style.background = '#00d4ff';
                        display.style.borderColor = '#00d4ff';
                        display.textContent = `${reactionTime}ms`;
                        display.onclick = null;
                        reactionWaiting = false;

                        updateReactionStats();

                        const result = document.getElementById('reaction-result');
                        if (reactionTime < 200) {
                            result.innerHTML = '🚀 超高速！';
                            result.style.color = '#00ff88';
                        } else if (reactionTime < 300) {
                            result.innerHTML = '⚡ 高速！';
                            result.style.color = '#00d4ff';
                        } else if (reactionTime < 500) {
                            result.innerHTML = '👍 良い！';
                            result.style.color = '#ffff00';
                        } else {
                            result.innerHTML = '🐌 もう少し速く！';
                            result.style.color = '#ff8000';
                        }
                    }
                };
            }, delay);

            // フライング対策
            display.onclick = function() {
                if (!reactionWaiting) {
                    clearTimeout(reactionTimeout);
                    display.style.background = '#ff6b6b';
                    display.style.borderColor = '#ff6b6b';
                    display.textContent = 'フライング！';
                    display.onclick = null;
                    document.getElementById('reaction-result').innerHTML = '❌ 早すぎます！';
                    document.getElementById('reaction-result').style.color = '#ff6b6b';
                }
            };
        }

        function updateReactionStats() {
            document.getElementById('reaction-best').textContent = reactionBestTime ? `${reactionBestTime}` : '-';
            document.getElementById('reaction-attempts').textContent = reactionAttempts;
        }

        function resetReactionGame() {
            reactionBestTime = null;
            reactionAttempts = 0;
            updateReactionStats();
            const display = document.getElementById('reaction-display');
            display.style.background = '#333';
            display.style.borderColor = '#555';
            display.textContent = 'スタートを押してください';
            display.onclick = null;
            document.getElementById('reaction-result').textContent = '';
            if (reactionTimeout) {
                clearTimeout(reactionTimeout);
            }
        }

        // エンターキーで数字当てゲームの予想を実行
        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById('number-input').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    guessNumber();
                }
            });
        });
    </script>
</body>
</html>
"""

profile_template = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>プロフィール - GAME SERVER</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Orbitron', monospace;
            background: #0a0a0a;
            color: #ffffff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .bg-animation {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(45deg, #0a0a0a, #1a2e42, #163e42);
            background-size: 400% 400%;
            animation: gradientShift 15s ease infinite;
            z-index: -1;
        }

        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        .container {
            background: rgba(255, 255, 255, 0.05);
            padding: 3rem;
            border-radius: 15px;
            border: 1px solid rgba(0, 212, 255, 0.3);
            backdrop-filter: blur(10px);
            text-align: center;
            max-width: 600px;
            width: 90%;
        }

        .profile-icon {
            font-size: 4rem;
            color: #00d4ff;
            margin-bottom: 1rem;
        }

        h1 {
            font-size: 2.5rem;
            margin-bottom: 1rem;
            background: linear-gradient(45deg, #0099ff, #00d4ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .profile-info {
            background: rgba(255, 255, 255, 0.03);
            padding: 2rem;
            border-radius: 10px;
            margin: 2rem 0;
            border: 1px solid rgba(0, 212, 255, 0.2);
        }

        .info-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 0;
            border-bottom: 1px solid rgba(0, 212, 255, 0.1);
        }

        .info-item:last-child {
            border-bottom: none;
        }

        .info-label {
            font-weight: 700;
            color: #00d4ff;
        }

        .info-value {
            opacity: 0.8;
            word-break: break-all;
        }

        .login-prompt {
            text-align: center;
            padding: 2rem;
        }

        .login-prompt p {
            margin-bottom: 2rem;
            opacity: 0.8;
            line-height: 1.6;
        }

        .back-button, .logout-button, .login-button {
            display: inline-block;
            margin: 0.5rem;
            padding: 0.8rem 1.5rem;
            background: transparent;
            color: #00d4ff;
            text-decoration: none;
            border: 2px solid #00d4ff;
            border-radius: 25px;
            transition: all 0.3s ease;
        }

        .back-button:hover, .logout-button:hover, .login-button:hover {
            background: #00d4ff;
            color: #000;
        }

        .logout-button {
            color: #ff6b6b;
            border-color: #ff6b6b;
        }

        .logout-button:hover {
            background: #ff6b6b;
            color: #000;
        }

        @media (max-width: 768px) {
            .info-item {
                flex-direction: column;
                align-items: flex-start;
                gap: 0.5rem;
            }
        }
    </style>
</head>
<body>
    <div class="bg-animation"></div>

    <div class="container">
        {% if session.username %}
        <div class="profile-icon">👤</div>
        <h1>プロフィール</h1>

        <div class="profile-info">
            <div class="info-item">
                <span class="info-label">ユーザー名:</span>
                <span class="info-value">{{ session.username }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">ユーザーID:</span>
                <span class="info-value">{{ user_data.user_id }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">ロール:</span>
                <span class="info-value">{{ user_data.role }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">アカウントタイプ:</span>
                <span class="info-value">カスタム認証</span>
            </div>
        </div>

        <a href="/edit_profile" class="back-button">プロフィール編集</a>
        <a href="/" class="back-button">ホームに戻る</a>
        <a href="/logout" class="logout-button">ログアウト</a>

        {% else %}
        <div class="profile-icon">🔐</div>
        <h1>ログインが必要です</h1>

        <div class="login-prompt">
            <p>プロフィールを表示するにはログインしてください。</p>
        </div>

        <a href="/login" class="login-button">ログイン</a>
        <a href="/" class="back-button">ホームに戻る</a>
        {% endif %}
    </div>
</body>
</html>
"""

edit_profile_template = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>プロフィール編集 - GAME SERVER</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Orbitron', monospace;
            background: #0a0a0a;
            color: #ffffff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .bg-animation {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(45deg, #0a0a0a, #1a2e42, #163e42);
            background-size: 400% 400%; animation: gradientShift 15s ease infinite; z-index: -1;
        }
        @keyframes gradientShift {
            0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; }
        }
        .container {
            background: rgba(255, 255, 255, 0.05); padding: 3rem; border-radius: 15px;
            border: 1px solid rgba(0, 212, 255, 0.3); backdrop-filter: blur(10px);
            text-align: center; max-width: 400px; width: 90%;
        }
        h1 {
            font-size: 2.5rem; margin-bottom: 2rem;
            background: linear-gradient(45deg, #0099ff, #00d4ff);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        label { display: block; margin-bottom: 0.5rem; color: #00d4ff; font-weight: 700; }
        input[type="text"] {
            width: 100%; padding: 1rem; background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(0, 212, 255, 0.3); border-radius: 8px; color: #ffffff;
            font-family: 'Orbitron', monospace; font-size: 1rem;
        }
        .save-button {
            width: 100%; padding: 1rem 2rem; background: linear-gradient(45deg, #0099ff, #00d4ff);
            color: #000; border: none; border-radius: 8px; font-weight: 700;
            font-family: 'Orbitron', monospace; cursor: pointer; margin-top: 1rem;
        }
        .back-button {
            display: inline-block; margin-top: 1rem; padding: 0.8rem 1.5rem;
            background: transparent; color: #00d4ff; text-decoration: none;
            border: 2px solid #00d4ff; border-radius: 25px;
        }
    </style>
</head>
<body>
    <div class="bg-animation"></div>
    <div class="container">
        <h1>プロフィール編集</h1>
        <form method="POST">
            <label for="new_username">新しいユーザー名:</label>
            <input type="text" id="new_username" name="new_username" value="{{ user_data.get('username', '') }}" required>
            <button type="submit" class="save-button">保存</button>
        </form>
        <a href="/profile" class="back-button">戻る</a>
    </div>
</body>
</html>
"""

server_settings_template = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>サーバー設定 - GAME SERVER</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Orbitron', monospace; background: #0a0a0a; color: #ffffff;
            min-height: 100vh; padding: 80px 20px 20px;
        }
        .bg-animation {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(45deg, #0a0a0a, #1a2e42, #163e42);
            background-size: 400% 400%; animation: gradientShift 15s ease infinite; z-index: -1;
        }
        @keyframes gradientShift {
            0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; }
        }
        nav {
            position: fixed; top: 0; width: 100%; padding: 1rem 2rem;
            background: rgba(0, 0, 0, 0.8); backdrop-filter: blur(10px);
            z-index: 1000; border-bottom: 2px solid #00d4ff;
        }
        .nav-container {
            display: flex; justify-content: space-between; align-items: center;
            max-width: 1200px; margin: 0 auto;
        }
        .logo { font-size: 1.8rem; font-weight: 900; color: #00d4ff; text-shadow: 0 0 20px #00d4ff; }
        .nav-links { display: flex; gap: 2rem; list-style: none; }
        .nav-links a { color: #ffffff; text-decoration: none; transition: all 0.3s ease; padding: 0.5rem 1rem; border-radius: 5px; }
        .nav-links a:hover { color: #00d4ff; background: rgba(0, 212, 255, 0.1); transform: translateY(-2px); }
        .container { max-width: 800px; margin: 0 auto; }
        h1 {
            font-size: 3rem; margin-bottom: 2rem; text-align: center;
            background: linear-gradient(45deg, #0099ff, #00d4ff);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .settings-form {
            background: rgba(255, 255, 255, 0.05); padding: 2rem; border-radius: 15px;
            border: 1px solid rgba(0, 212, 255, 0.3); backdrop-filter: blur(10px);
        }
        .form-group {
            margin-bottom: 1.5rem; display: flex; justify-content: space-between;
            align-items: center; padding: 1rem 0; border-bottom: 1px solid rgba(0, 212, 255, 0.1);
        }
        .form-group:last-child { border-bottom: none; }
        .form-label { font-weight: 700; color: #00d4ff; flex: 1; }
        .form-description { font-size: 0.9rem; opacity: 0.7; flex: 1; margin: 0 1rem; }
        .form-input { flex: 0 0 150px; }
        input[type="text"], input[type="number"] {
            width: 100%; padding: 0.5rem; background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(0, 212, 255, 0.3); border-radius: 5px; color: #ffffff;
            font-family: 'Orbitron', monospace;
        }
        input[type="checkbox"] {
            width: 20px; height: 20px; accent-color: #00d4ff;
        }
        .save-button {
            width: 100%; padding: 1rem 2rem; background: linear-gradient(45deg, #0099ff, #00d4ff);
            color: #000; border: none; border-radius: 8px; font-weight: 700;
            font-family: 'Orbitron', monospace; cursor: pointer; margin-top: 2rem; font-size: 1.1rem;
        }
        .save-button:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(0, 212, 255, 0.3); }
        .back-button {
            display: inline-block; margin-top: 2rem; padding: 0.8rem 1.5rem;
            background: transparent; color: #00d4ff; text-decoration: none;
            border: 2px solid #00d4ff; border-radius: 25px; transition: all 0.3s ease;
        }
        .back-button:hover { background: #00d4ff; color: #000; }
        .success-message {
            background: rgba(0, 255, 136, 0.1); border: 1px solid #00ff88; color: #00ff88;
            padding: 1rem; border-radius: 8px; margin-bottom: 1rem;
        }
        .error-message {
            background: rgba(255, 107, 107, 0.1); border: 1px solid #ff6b6b; color: #ff6b6b;
            padding: 1rem; border-radius: 8px; margin-bottom: 1rem;
        }
        @media (max-width: 768px) {
            .form-group { flex-direction: column; align-items: flex-start; gap: 0.5rem; }
            .form-input { flex: none; width: 100%; }
        }
    </style>
</head>
<body>
    <div class="bg-animation"></div>
    <nav>
        <div class="nav-container">
            <div class="logo">GAME SERVER</div>
            <ul class="nav-links">
                <li><a href="/">ホーム</a></li>
                <li><a href="/users">👥 ユーザー</a></li>
                <li><a href="/server_settings" style="color: #00d4ff;">⚙️ 設定</a></li>
                <li><a href="/logout">ログアウト</a></li>
            </ul>
        </div>
    </nav>
    <div class="container">
        <h1>⚙️ サーバー設定</h1>

        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    {% if 'success' in message or '成功' in message or '更新' in message %}
                        <div class="success-message">{{ message }}</div>
                    {% else %}
                        <div class="error-message">{{ message }}</div>
                    {% endif %}
                {% endfor %}
            {% endif %}
        {% endwith %}

        <form method="POST" class="settings-form">
            <div class="form-group">
                <div class="form-label">サーバー名</div>
                <div class="form-description">表示されるサーバー名</div>
                <div class="form-input">
                    <input type="text" name="server_name" value="{{ settings.server_name }}" required>
                </div>
            </div>

            <div class="form-group">
                <div class="form-label">ユーザータイムアウト</div>
                <div class="form-description">アクティブユーザーが非アクティブと判定される時間（秒）</div>
                <div class="form-input">
                    <input type="number" name="user_timeout" value="{{ settings.user_timeout }}" min="10" max="300" required>
                </div>
            </div>

            <div class="form-group">
                <div class="form-label">最大ユーザー数</div>
                <div class="form-description">同時接続可能な最大ユーザー数</div>
                <div class="form-input">
                    <input type="number" name="max_users" value="{{ settings.max_users }}" min="1" max="1000" required>
                </div>
            </div>

            <div class="form-group">
                <div class="form-label">ハートビート間隔</div>
                <div class="form-description">アクティブユーザー更新の間隔（秒）</div>
                <div class="form-input">
                    <input type="number" name="heartbeat_interval" value="{{ settings.heartbeat_interval }}" min="5" max="60" required>
                </div>
            </div>

            <div class="form-group">
                <div class="form-label">デバッグモード</div>
                <div class="form-description">開発用のデバッグ情報を表示</div>
                <div class="form-input">
                    <input type="checkbox" name="debug_mode" {% if settings.debug_mode %}checked{% endif %}>
                </div>
            </div>

            <div class="form-group">
                <div class="form-label">新規登録</div>
                <div class="form-description">新規ユーザー登録を許可</div>
                <div class="form-input">
                    <input type="checkbox" name="registration_enabled" {% if settings.registration_enabled %}checked{% endif %}>
                </div>
            </div>

            <div class="form-group">
                <div class="form-label">メンテナンスモード</div>
                <div class="form-description">メンテナンス中は管理者のみアクセス可能</div>
                <div class="form-input">
                    <input type="checkbox" name="maintenance_mode" {% if settings.maintenance_mode %}checked{% endif %}>
                </div>
            </div>

            <button type="submit" class="save-button">設定を保存</button>
        </form>

        <a href="/admin" class="back-button">管理画面に戻る</a>
    </div>
</body>
</html>
"""

users_template = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ユーザー管理 - GAME SERVER</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Orbitron', monospace; background: #0a0a0a; color: #ffffff;
            min-height: 100vh; padding: 80px 20px 20px;
        }
        .bg-animation {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(45deg, #0a0a0a, #1a2e42, #163e42);
            background-size: 400% 400%; animation: gradientShift 15s ease infinite; z-index: -1;
        }
        @keyframes gradientShift {
            0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; }
        }
        nav {
            position: fixed; top: 0; width: 100%; padding: 1rem 2rem;
            background: rgba(0, 0, 0, 0.8); backdrop-filter: blur(10px);
            z-index: 1000; border-bottom: 2px solid #00d4ff;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 {
            font-size: 3rem; margin-bottom: 2rem; text-align: center;
            background: linear-gradient(45deg, #0099ff, #00d4ff);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .user-card {
            background: rgba(255, 255, 255, 0.05); padding: 2rem; margin: 1rem 0;
            border-radius: 15px; border: 1px solid rgba(0, 212, 255, 0.3);
        }
        .back-button {
            display: inline-block; margin-top: 2rem; padding: 0.8rem 1.5rem;
            background: transparent; color: #00d4ff; text-decoration: none;
            border: 2px solid #00d4ff; border-radius: 25px;
        }
    </style>
</head>
<body>
    <div class="bg-animation"></div>
    <nav><div style="text-align: center; color: #00d4ff; font-size: 1.8rem; font-weight: 900;">GAME SERVER</div></nav>
    <div class="container">
        <h1>ユーザー管理</h1>
        {% for username, data in users_db.items() %}
        <div class="user-card">
            <strong>{{ username }}</strong> ({{ data.user_id }}) - {{ data.role }}
            {% if 'email' in data %}<br>Email: {{ data.email }}{% endif %}
        </div>
        {% endfor %}
        <a href="/admin" class="back-button">管理画面に戻る</a>
    </div>
</body>
</html>
"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember_me = request.form.get('remember_me') == 'on'

        if verify_password(username, password):
            session['username'] = username
            
            # Remember me機能の処理
            if remember_me:
                # 永続的なログイントークンを生成
                token = secrets.token_urlsafe(32)
                expires = datetime.now() + timedelta(days=30)
                persistent_tokens[token] = {
                    'username': username,
                    'expires': expires
                }
                
                # Cookieにトークンを設定（30日間有効）
                response = make_response(redirect(url_for('home')))
                response.set_cookie('remember_token', token, 
                                  max_age=30*24*60*60,  # 30日
                                  httponly=True, 
                                  secure=False)  # HTTPSの場合はTrueに設定
                flash('ログインに成功しました！（30日間保存されます）', 'success')
                return response
            else:
                flash('ログインに成功しました！', 'success')
                return redirect(url_for('home'))
        else:
            flash('ユーザー名またはパスワードが間違っています。', 'error')

    return render_template_string(login_template)

@app.route('/register', methods=['GET', 'POST'])
def register():
    # 新規登録が無効化されている場合はエラー
    if not server_settings.get('registration_enabled', True):
        flash('現在、新規登録は無効化されています。', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form['username']
        user_id = request.form['user_id']
        email = request.form['email']
        password = request.form['password']

        # ユーザー名、ユーザーID、メールアドレスが既に存在しないかチェック
        if username in users_db or user_id in [u['user_id'] for u in users_db.values()] or email in [u['email'] for u in users_db.values() if 'email' in u]:
            flash('ユーザー名、ユーザーID、またはメールアドレスが既に存在します。', 'error')
            return render_template_string(register_template, form_data=request.form)

        # 新しいユーザーをデータベースに追加
        users_db[username] = {
            "password_hash": hashlib.sha256(password.encode()).hexdigest(),
            "role": "一般ユーザー", # デフォルトロール
            "user_id": user_id,
            "email": email
        }
        flash('新規登録が完了しました！ログインしてください。', 'success')
        return redirect(url_for('login'))

    return render_template_string(register_template)

@app.route('/discord')
def discord():
    return render_template_string(discord_template)

@app.route('/minigame')
def minigame():
    return render_template_string(minigame_template)

@app.route('/profile')
def profile():
    if 'username' in session:
        user_data = get_user_info(session['username'])
        return render_template_string(profile_template, user_data=user_data)
    else:
        return render_template_string(profile_template)

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'username' not in session:
        flash('ログインが必要です。', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_username = request.form['new_username']
        current_username = session['username']

        # 新しいユーザー名が既に存在しないかチェック
        if new_username != current_username and new_username in users_db:
            flash('そのユーザー名は既に使用されています。', 'error')
            return render_template_string(edit_profile_template, user_data=get_user_info(current_username))

        # ユーザー名を更新
        if new_username != current_username:
            user_data = users_db[current_username]
            users_db[new_username] = user_data
            del users_db[current_username]
            session['username'] = new_username
            flash('ユーザー名を更新しました！', 'success')
        else:
            flash('変更はありませんでした。', 'info')

        return redirect(url_for('profile'))

    user_data = get_user_info(session['username'])
    return render_template_string(edit_profile_template, user_data=user_data)

@app.route('/users')
def users():
    if 'username' not in session:
        flash('ログインが必要です。', 'error')
        return redirect(url_for('login'))

    user_data = get_user_info(session['username'])
    if user_data['role'] != '管理者':
        flash('管理者権限が必要です。', 'error')
        return redirect(url_for('home'))

    return render_template_string(users_template, users_db=users_db)

@app.route('/logout')
def logout():
    # セッションからユーザー名を削除
    session.pop('username', None)
    
    # 永続的なログイントークンがある場合は削除
    remember_token = request.cookies.get('remember_token')
    if remember_token and remember_token in persistent_tokens:
        del persistent_tokens[remember_token]
    
    # Cookieからトークンを削除
    response = make_response(render_template_string("""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ログアウト - GAME SERVER</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Orbitron', monospace;
                background: #0a0a0a;
                color: #ffffff;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .bg-animation {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: linear-gradient(45deg, #0a0a0a, #1a2e42, #163e42);
                background-size: 400% 400%;
                animation: gradientShift 15s ease infinite;
                z-index: -1;
            }
            @keyframes gradientShift {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }
            .container {
                background: rgba(255, 255, 255, 0.05);
                padding: 3rem;
                border-radius: 15px;
                border: 1px solid rgba(0, 212, 255, 0.3);
                backdrop-filter: blur(10px);
                text-align: center;
                max-width: 500px;
                width: 90%;
            }
            h1 {
                font-size: 2.5rem;
                margin-bottom: 1rem;
                background: linear-gradient(45deg, #0099ff, #00d4ff);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            p { margin-bottom: 2rem; opacity: 0.8; line-height: 1.6; }
            .back-button {
                display: inline-block;
                padding: 0.8rem 1.5rem;
                background: transparent;
                color: #00d4ff;
                text-decoration: none;
                border: 2px solid #00d4ff;
                border-radius: 25px;
                transition: all 0.3s ease;
            }
            .back-button:hover { background: #00d4ff; color: #000; }
        </style>
    </head>
    <body>
        <div class="bg-animation"></div>
        <div class="container">
            <h1>ログアウト完了</h1>
            <p>ログアウトしました。ご利用ありがとうございました。</p>
            <a href="/" class="back-button">ホームに戻る</a>
        </div>
    </body>
    </html>
    """))
    
    # Remember tokenのCookieを削除
    response.set_cookie('remember_token', '', expires=0)
    flash('ログアウトしました。', 'info')
    return response

# Server settings route
@app.route('/server_settings', methods=['GET', 'POST'])
def server_settings_page():
    if 'username' not in session:
        flash('管理者としてログインしてください。', 'error')
        return redirect(url_for('login'))

    user_data = get_user_info(session['username'])
    if user_data['role'] != '管理者':
        flash('管理者権限が必要です。', 'error')
        return redirect(url_for('home'))

    if request.method == 'POST':
        try:
            # 設定を更新
            server_settings['user_timeout'] = int(request.form.get('user_timeout', 30))
            server_settings['debug_mode'] = request.form.get('debug_mode') == 'on'
            server_settings['max_users'] = int(request.form.get('max_users', 100))
            server_settings['heartbeat_interval'] = int(request.form.get('heartbeat_interval', 15))
            server_settings['maintenance_mode'] = request.form.get('maintenance_mode') == 'on'
            server_settings['server_name'] = request.form.get('server_name', 'GAME SERVER')
            server_settings['registration_enabled'] = request.form.get('registration_enabled') == 'on'

            flash('サーバー設定を更新しました！', 'success')
        except ValueError:
            flash('無効な値が入力されました。', 'error')

    return render_template_string(server_settings_template, settings=server_settings)

# Admin dashboard route
@app.route('/admin')
def admin_dashboard():
    if 'username' not in session:
        flash('管理者としてログインしてください。', 'error')
        return redirect(url_for('login'))

    user_data = get_user_info(session['username'])
    if user_data['role'] != '管理者':
        flash('管理者権限が必要です。', 'error')
        return redirect(url_for('home'))

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>管理ダッシュボード - GAME SERVER</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Orbitron', monospace;
                background: #0a0a0a;
                color: #ffffff;
                min-height: 100vh;
                padding: 80px 20px 20px;
            }
            .bg-animation {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: linear-gradient(45deg, #0a0a0a, #1a2e42, #163e42);
                background-size: 400% 400%;
                animation: gradientShift 15s ease infinite;
                z-index: -1;
            }
            @keyframes gradientShift {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }
            nav {
                position: fixed;
                top: 0;
                width: 100%;
                padding: 1rem 2rem;
                background: rgba(0, 0, 0, 0.8);
                backdrop-filter: blur(10px);
                z-index: 1000;
                border-bottom: 2px solid #00d4ff;
            }
            .nav-container {
                display: flex;
                justify-content: space-between;
                align-items: center;
                max-width: 1200px;
                margin: 0 auto;
            }
            .logo {
                font-size: 1.8rem;
                font-weight: 900;
                color: #00d4ff;
                text-shadow: 0 0 20px #00d4ff;
            }
            .nav-links {
                display: flex;
                gap: 2rem;
                list-style: none;
            }
            .nav-links a {
                color: #ffffff;
                text-decoration: none;
                transition: all 0.3s ease;
                padding: 0.5rem 1rem;
                border-radius: 5px;
            }
            .nav-links a:hover {
                color: #00d4ff;
                background: rgba(0, 212, 255, 0.1);
                transform: translateY(-2px);
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                text-align: center;
            }
            h1 {
                font-size: 3rem;
                margin-bottom: 2rem;
                background: linear-gradient(45deg, #0099ff, #00d4ff);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 2rem;
                margin-top: 3rem;
            }
            .card {
                background: rgba(255, 255, 255, 0.05);
                padding: 2rem;
                border-radius: 15px;
                border: 1px solid rgba(0, 212, 255, 0.3);
                transition: all 0.3s ease;
                backdrop-filter: blur(10px);
                text-align: center;
            }
            .card:hover {
                transform: translateY(-10px);
                border-color: #00d4ff;
                box-shadow: 0 20px 40px rgba(0, 212, 255, 0.3);
            }
            .card-icon {
                font-size: 3rem;
                color: #00d4ff;
                margin-bottom: 1rem;
            }
            .card-title {
                font-size: 1.5rem;
                color: #00d4ff;
                margin-bottom: 0.5rem;
            }
            .card-description {
                opacity: 0.8;
            }
            .back-button {
                display: inline-block;
                margin-top: 2rem;
                padding: 0.8rem 1.5rem;
                background: transparent;
                color: #00d4ff;
                text-decoration: none;
                border: 2px solid #00d4ff;
                border-radius: 25px;
                transition: all 0.3s ease;
            }
            .back-button:hover {
                background: #00d4ff;
                color: #000;
            }
            @media (max-width: 768px) {
                h1 { font-size: 2rem; }
            }
        </style>
    </head>
    <body>
        <div class="bg-animation"></div>
        <nav>
            <div class="nav-container">
                <div class="logo">GAME SERVER</div>
                <ul class="nav-links">
                    <li><a href="/">ホーム</a></li>
                    <li><a href="/users">👥 ユーザー</a></li>
                    <li><a href="/server_settings">⚙️ 設定</a></li>
                    <li><a href="/logout">ログアウト</a></li>
                </ul>
            </div>
        </nav>
        <div class="container">
            <h1>管理ダッシュボード</h1>
            <div class="dashboard-grid">
                <a href="/users" class="card">
                    <div class="card-icon">👥</div>
                    <div class="card-title">ユーザー管理</div>
                    <div class="card-description">ユーザーリストの表示と管理</div>
                </a>
                <a href="/server_settings" class="card">
                    <div class="card-icon">⚙️</div>
                    <div class="card-title">サーバー設定</div>
                    <div class="card-description">サーバー設定の変更と管理</div>
                </a>
                <a href="/statistics" class="card">
                    <div class="card-icon">📊</div>
                    <div class="card-title">統計情報</div>
                    <div class="card-description">サーバーの統計情報</div>
                </a>
            </div>
            <a href="/" class="back-button">ホームに戻る</a>
        </div>
    </body>
    </html>
    """)


@app.route('/')
def home():
    global user_counter
    user_data = None

    if 'username' in session:
        # ユーザーがログインしている場合、アクティブユーザーに追加
        user_id = f"{session['username']}_{user_counter}"
        user_counter += 1
        active_users[user_id] = time.time()
        user_data = get_user_info(session['username'])

    return render_template_string(template, user_data=user_data)

@app.route('/heartbeat')
def heartbeat():
    """アクティブユーザー数を返すエンドポイント"""
    # セッションにユーザーがいる場合、現在時刻で更新
    if 'username' in session:
        # より簡単なユーザーIDを使用
        user_id = session['username']
        active_users[user_id] = time.time()

    return jsonify({
        'active_users': len(active_users),
        'timestamp': time.time()
    })

# Statistics route
@app.route('/statistics')
def statistics():
    if 'username' not in session:
        flash('ログインが必要です。', 'error')
        return redirect(url_for('login'))

    user_data = get_user_info(session['username'])
    if user_data['role'] != '管理者':
        flash('管理者権限が必要です。', 'error')
        return redirect(url_for('home'))

    return render_template_string(statistics_template)

statistics_template = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>統計情報 - GAME SERVER</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Orbitron', monospace; background: #0a0a0a; color: #ffffff;
            min-height: 100vh; padding: 80px 20px 20px;
        }
        .bg-animation {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(45deg, #0a0a0a, #1a2e42, #163e42);
            background-size: 400% 400%; animation: gradientShift 15s ease infinite; z-index: -1;
        }
        @keyframes gradientShift {
            0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; }
        }
        nav {
            position: fixed; top: 0; width: 100%; padding: 1rem 2rem;
            background: rgba(0, 0, 0, 0.8); backdrop-filter: blur(10px);
            z-index: 1000; border-bottom: 2px solid #00d4ff;
        }
        .nav-container {
            display: flex; justify-content: space-between; align-items: center;
            max-width: 1200px; margin: 0 auto;
        }
        .logo { font-size: 1.8rem; font-weight: 900; color: #00d4ff; text-shadow: 0 0 20px #00d4ff; }
        .nav-links { display: flex; gap: 2rem; list-style: none; }
        .nav-links a { color: #ffffff; text-decoration: none; transition: all 0.3s ease; padding: 0.5rem 1rem; border-radius: 5px; }
        .nav-links a:hover { color: #00d4ff; background: rgba(0, 212, 255, 0.1); transform: translateY(-2px); }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 {
            font-size: 3rem; margin-bottom: 2rem; text-align: center;
            background: linear-gradient(45deg, #0099ff, #00d4ff);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .stats-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 2rem; margin: 2rem 0;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.05); padding: 2rem; border-radius: 15px;
            border: 1px solid rgba(0, 212, 255, 0.3); backdrop-filter: blur(10px); text-align: center;
        }
        .stat-card:hover {
            transform: translateY(-5px); border-color: #00d4ff;
            box-shadow: 0 15px 30px rgba(0, 212, 255, 0.3);
        }
        .stat-icon { font-size: 2.5rem; color: #00d4ff; margin-bottom: 1rem; }
        .stat-value { font-size: 2rem; font-weight: 900; color: #00d4ff; margin-bottom: 0.5rem; }
        .stat-label { opacity: 0.8; font-size: 1rem; }
        .chart-container {
            background: rgba(255, 255, 255, 0.05); padding: 2rem; border-radius: 15px;
            border: 1px solid rgba(0, 212, 255, 0.3); margin: 2rem 0; text-align: center;
        }
        .page-views { display: flex; flex-wrap: wrap; gap: 1rem; justify-content: center; margin-top: 1rem; }
        .page-view-item {
            background: rgba(0, 212, 255, 0.1); padding: 0.5rem 1rem; border-radius: 8px;
            border: 1px solid rgba(0, 212, 255, 0.3);
        }
        .refresh-button, .reset-button {
            padding: 1rem 2rem; background: linear-gradient(45deg, #0099ff, #00d4ff);
            color: #000; border: none; border-radius: 8px; font-weight: 700;
            font-family: 'Orbitron', monospace; cursor: pointer; margin: 0.5rem; font-size: 1rem;
        }
        .reset-button { background: linear-gradient(45deg, #ff6b6b, #ff8e8e); }
        .back-button {
            display: inline-block; margin-top: 2rem; padding: 0.8rem 1.5rem;
            background: transparent; color: #00d4ff; text-decoration: none;
            border: 2px solid #00d4ff; border-radius: 25px; transition: all 0.3s ease;
        }
        .back-button:hover { background: #00d4ff; color: #000; }
        .success-rate { display: flex; align-items: center; justify-content: center; gap: 1rem; }
        .rate-bar {
            width: 100px; height: 10px; background: rgba(255,255,255,0.1);
            border-radius: 5px; overflow: hidden;
        }
        .rate-fill { height: 100%; background: linear-gradient(90deg, #ff6b6b, #ffff00, #00ff88); border-radius: 5px; }
        @media (max-width: 768px) {
            .stats-grid { grid-template-columns: 1fr; }
            h1 { font-size: 2rem; }
        }
    </style>
</head>
<body>
    <div class="bg-animation"></div>
    <nav>
        <div class="nav-container">
            <div class="logo">GAME SERVER</div>
            <ul class="nav-links">
                <li><a href="/">ホーム</a></li>
                <li><a href="/users">👥 ユーザー</a></li>
                <li><a href="/server_settings">⚙️ 設定</a></li>
                <li><a href="/statistics" style="color: #00d4ff;">📊 統計</a></li>
                <li><a href="/logout">ログアウト</a></li>
            </ul>
        </div>
    </nav>
    <div class="container">
        <h1>📊 サーバー統計情報</h1>

        <div class="stats-grid" id="stats-container">
            <!-- 統計カードはJavaScriptで動的に読み込まれます -->
        </div>

        <div class="chart-container">
            <h2 style="color: #00d4ff; margin-bottom: 1rem;">📈 ページビュー</h2>
            <div class="page-views" id="page-views">
                <!-- ページビューはJavaScriptで動的に読み込まれます -->
            </div>
        </div>

        <div style="text-align: center; margin: 2rem 0;">
            <button class="refresh-button" onclick="loadStats()">🔄 更新</button>
            <form method="POST" action="/reset_stats" style="display: inline;"
                  onsubmit="return confirm('統計情報をリセットしますか？この操作は元に戻せません。')">
                <button type="submit" class="reset-button">🗑️ リセット</button>
            </form>
        </div>

        <a href="/admin" class="back-button">管理画面に戻る</a>
    </div>

    <script>
        function loadStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    updateStatsDisplay(data);
                })
                .catch(error => {
                    console.error('統計情報の読み込みに失敗しました:', error);
                });
        }

        function updateStatsDisplay(stats) {
            const container = document.getElementById('stats-container');

            container.innerHTML = `
                <div class="stat-card">
                    <div class="stat-icon">⏱️</div>
                    <div class="stat-value">${stats.uptime_formatted}</div>
                    <div class="stat-label">サーバー稼働時間</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">👥</div>
                    <div class="stat-value">${stats.current_active_users}</div>
                    <div class="stat-label">現在のアクティブユーザー</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">📈</div>
                    <div class="stat-value">${stats.peak_active_users}</div>
                    <div class="stat-label">ピークアクティブユーザー</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">📊</div>
                    <div class="stat-value">${stats.avg_active_users.toFixed(1)}</div>
                    <div class="stat-label">平均アクティブユーザー</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">🌐</div>
                    <div class="stat-value">${stats.total_requests.toLocaleString()}</div>
                    <div class="stat-label">総リクエスト数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">🔐</div>
                    <div class="stat-value">${stats.login_attempts}</div>
                    <div class="stat-label">ログイン試行回数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">✅</div>
                    <div class="stat-value">${stats.successful_logins}</div>
                    <div class="stat-label">成功したログイン</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">❌</div>
                    <div class="stat-value">${stats.failed_logins}</div>
                    <div class="stat-label">失敗したログイン</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">📝</div>
                    <div class="stat-value">${stats.registrations}</div>
                    <div class="stat-label">新規登録数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">👤</div>
                    <div class="stat-value">${stats.total_users}</div>
                    <div class="stat-label">総ユーザー数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">📊</div>
                    <div class="stat-value success-rate">
                        <span>${stats.success_rate.toFixed(1)}%</span>
                        <div class="rate-bar">
                            <div class="rate-fill" style="width: ${Math.min(stats.success_rate, 100)}%"></div>
                        </div>
                    </div>
                    <div class="stat-label">ログイン成功率</div>
                </div>
            `;

            // ページビューの更新
            const pageViewsContainer = document.getElementById('page-views');
            const pageViewsHtml = Object.entries(stats.page_views)
                .map(([page, views]) => `
                    <div class="page-view-item">
                        <strong>${page}</strong>: ${views.toLocaleString()} views
                    </div>
                `).join('');

            pageViewsContainer.innerHTML = pageViewsHtml || '<div class="page-view-item">データなし</div>';
        }

        // 初回読み込み
        loadStats();

        // 30秒ごとに自動更新
        setInterval(loadStats, 30000);
    </script>
</body>
</html>
"""

@app.route('/reset_stats', methods=['POST'])
def reset_stats():
    if 'username' not in session:
        flash('ログインが必要です。', 'error')
        return redirect(url_for('login'))

    user_data = get_user_info(session['username'])
    if user_data['role'] != '管理者':
        flash('管理者権限が必要です。', 'error')
        return redirect(url_for('home'))

    # 統計情報をリセット（ここではダミーデータを使用）
    # 実際には、ログファイルやデータベースから集計したデータをクリアする必要があります。
    global active_users, user_counter
    active_users.clear()
    user_counter = 0

    # ページビューなどの統計情報もリセットするロジックを追加

    flash('統計情報をリセットしました。', 'success')
    return redirect(url_for('statistics'))

# Mock API endpoint for statistics (replace with actual data aggregation)
@app.route('/api/stats')
def api_stats():
    # Dummy data for statistics
    # In a real application, this data would be fetched from logs or a database
    uptime = time.time() - 1678886400 # Example: Server started on March 15, 2023
    uptime_seconds = int(uptime)
    days = uptime_seconds // (24 * 3600)
    hours = (uptime_seconds % (24 * 3600)) // 3600
    minutes = (uptime_seconds % 3600) // 60
    uptime_formatted = f"{days}d {hours}h {minutes}m"

    current_active_users = len(active_users)
    # Simulate peak and average users (replace with actual tracking)
    peak_active_users = max(current_active_users, 50) # Example peak
    avg_active_users = (current_active_users + 30) / 2 # Example average

    total_requests = 15000 # Example total requests
    login_attempts = 500 # Example login attempts
    successful_logins = 450 # Example successful logins
    failed_logins = login_attempts - successful_logins
    registrations = 100 # Example registrations
    total_users = len(users_db) # Number of users in our mock DB

    success_rate = (successful_logins / login_attempts * 100) if login_attempts > 0 else 0

    # Mock page view data
    page_views = {
        '/': 12000,
        '/login': 3000,
        '/register': 1500,
        '/profile': 2500,
        '/minigame': 5000,
        '/discord': 4000,
        '/admin': 500,
        '/server_settings': 100,
        '/users': 200,
        '/statistics': 50
    }

    return jsonify({
        'uptime_formatted': uptime_formatted,
        'current_active_users': current_active_users,
        'peak_active_users': peak_active_users,
        'avg_active_users': avg_active_users,
        'total_requests': total_requests,
        'login_attempts': login_attempts,
        'successful_logins': successful_logins,
        'failed_logins': failed_logins,
        'registrations': registrations,
        'total_users': total_users,
        'success_rate': success_rate,
        'page_views': page_views
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)