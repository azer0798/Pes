from flask import Flask, render_template_string, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
# استخدم مفتاحاً سرياً ثابتاً في الإنتاج، أو متغير بيئة
app.secret_key = os.environ.get('SECRET_KEY', 'default-secret-key-please-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ======================
# نموذج قاعدة البيانات
# ======================
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Post {self.id}: {self.content[:20]}...>'

# ======================
# إنشاء قاعدة البيانات
# ======================
with app.app_context():
    db.create_all()

# ======================
# قالب تسجيل الدخول المحسن
# ======================
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    <title>تسجيل الدخول - مدونتي</title>
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
            padding: 20px;
        }
        .login-card {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 400px;
            width: 100%;
            animation: fadeIn 0.5s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .login-icon {
            font-size: 4rem;
            color: #667eea;
            background: #f0f0ff;
            padding: 20px;
            border-radius: 50%;
            display: inline-block;
            margin-bottom: 10px;
        }
        .btn-login {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            padding: 12px;
            font-weight: bold;
            transition: all 0.3s;
        }
        .btn-login:hover {
            transform: scale(1.02);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        .error-message {
            color: #dc3545;
            font-size: 0.9rem;
            margin-top: 10px;
            padding: 10px;
            background: #f8d7da;
            border-radius: 8px;
            border: 1px solid #f5c6cb;
        }
        .input-group-text {
            background: #f8f9fa;
        }
        .back-link {
            transition: all 0.3s;
        }
        .back-link:hover {
            color: #667eea !important;
        }
    </style>
</head>
<body>
    <div class="login-card text-center">
        <div class="login-icon">
            <i class="bi bi-shield-lock"></i>
        </div>
        <h3 class="mt-3 fw-bold">مرحباً بعودتك</h3>
        <p class="text-muted">أدخل كلمة السر للوصول إلى لوحة التحكم</p>
        
        <form method="POST" class="mt-4">
            <div class="input-group mb-3">
                <span class="input-group-text"><i class="bi bi-key-fill"></i></span>
                <input type="password" name="password" class="form-control form-control-lg" 
                       placeholder="كلمة السر" required autofocus>
            </div>
            <button type="submit" class="btn btn-primary w-100 btn-login">
                <i class="bi bi-box-arrow-in-right"></i> دخول
            </button>
        </form>
        
        {% if error %}
            <div class="error-message">
                <i class="bi bi-exclamation-circle-fill"></i> {{ error }}
            </div>
        {% endif %}
        
        <div class="mt-4">
            <a href="/" class="text-decoration-none text-muted back-link">
                <i class="bi bi-arrow-right"></i> العودة للمدونة
            </a>
        </div>
        
        <div class="mt-3 small text-muted">
            <i class="bi bi-info-circle"></i> كلمة السر الافتراضية: 1234
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

# ======================
# الصفحة الرئيسية
# ======================
@app.route('/')
def index():
    posts = Post.query.order_by(Post.date.desc()).all()
    # قراءة ملف index.html من نفس المجلد (بدون مجلد templates)
    with open('index.html', encoding='utf-8') as f:
        template = f.read()
    return render_template_string(template, posts=posts)

# ======================
# تسجيل الدخول
# ======================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == '1234':  # يمكنك تغيير كلمة السر هنا
            session['admin'] = True
            session['login_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return redirect(url_for('index'))
        else:
            return render_template_string(LOGIN_TEMPLATE, error='❌ كلمة السر غير صحيحة، حاول مرة أخرى')
    return render_template_string(LOGIN_TEMPLATE, error=None)

# ======================
# إضافة تدوينة جديدة
# ======================
@app.route('/add', methods=['POST'])
def add():
    if not session.get('admin'):
        return "غير مصرح لك - يرجى تسجيل الدخول أولاً", 403
    
    content = request.form.get('content', '').strip()
    if not content:
        return "المحتوى مطلوب", 400
    
    post = Post(content=content)
    db.session.add(post)
    db.session.commit()
    return redirect(url_for('index'))

# ======================
# حذف تدوينة
# ======================
@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    if not session.get('admin'):
        return "غير مصرح لك - يرجى تسجيل الدخول أولاً", 403
    
    post = Post.query.get(id)
    if post:
        db.session.delete(post)
        db.session.commit()
    else:
        return "التدوينة غير موجودة", 404
    return redirect(url_for('index'))

# ======================
# تسجيل الخروج
# ======================
@app.route('/logout')
def logout():
    session.pop('admin', None)
    session.pop('login_time', None)
    return redirect(url_for('index'))

# ======================
# (اختياري) عرض تفاصيل التدوينة
# ======================
@app.route('/post/<int:id>')
def view_post(id):
    post = Post.query.get_or_404(id)
    return render_template_string('''
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <title>التدوينة</title>
        </head>
        <body class="p-4">
            <div class="container" style="max-width: 600px;">
                <div class="card shadow">
                    <div class="card-body">
                        <h5 class="card-title">📝 تفاصيل التدوينة</h5>
                        <p class="card-text">{{ post.content }}</p>
                        <small class="text-muted">{{ post.date.strftime('%Y-%m-%d %H:%M') }}</small>
                        <br><br>
                        <a href="/" class="btn btn-secondary btn-sm">← العودة للرئيسية</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
    ''', post=post)

# ======================
# تشغيل التطبيق
# ======================
if __name__ == '__main__':
    # التعديل الهام للعمل على Render ومنصات السحابة
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(host='0.0.0.0', port=port, debug=debug)
