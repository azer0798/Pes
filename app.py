from flask import Flask, render_template_string, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default-secret-key-please-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# إعدادات رفع الصور
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# إنشاء مجلد static/uploads إذا لم يكن موجوداً
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

# ======================
# نموذج قاعدة البيانات (مع إضافة الصورة والنوع)
# ======================
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(255), nullable=True)  # مسار الصورة
    category = db.Column(db.String(50), nullable=False, default='general')  # نوع التدوينة
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Post {self.id}: {self.content[:20]}...>'

with app.app_context():
    db.create_all()

# ======================
# دوال مساعدة للصور
# ======================
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_category_label(category):
    categories = {
        'cities': '🏙️ مدن زرتها',
        'experience': '⭐ تجربة خاصة',
        'moments': '📸 لحظات خاصة',
        'memories': '📖 ذكريات',
        'dates': '📅 تواريخ',
        'general': '📝 عام'
    }
    return categories.get(category, category)

def get_category_icon(category):
    icons = {
        'cities': 'bi-geo-alt-fill',
        'experience': 'bi-star-fill',
        'moments': 'bi-camera-fill',
        'memories': 'bi-bookmark-fill',
        'dates': 'bi-calendar-event-fill',
        'general': 'bi-pencil-fill'
    }
    return icons.get(category, 'bi-pencil-fill')

def get_category_color(category):
    colors = {
        'cities': '#4ecdc4',
        'experience': '#ff6b6b',
        'moments': '#feca57',
        'memories': '#a29bfe',
        'dates': '#fd79a8',
        'general': '#6c63ff'
    }
    return colors.get(category, '#6c63ff')

# ======================
# قالب تسجيل الدخول (خاص بالأدمن)
# ======================
ADMIN_LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    <title>دخول الأدمن - مدونتي</title>
    <style>
        body {
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
            padding: 20px;
        }
        .login-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 40px;
            border-radius: 20px;
            max-width: 400px;
            width: 100%;
            animation: fadeIn 0.5s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .login-icon {
            font-size: 3rem;
            color: #f093fb;
            text-align: center;
            display: block;
            margin-bottom: 15px;
        }
        .login-title {
            color: white;
            text-align: center;
            font-weight: 700;
            margin-bottom: 5px;
        }
        .login-sub {
            color: rgba(255,255,255,0.4);
            text-align: center;
            font-size: 0.9rem;
            margin-bottom: 25px;
        }
        .form-control-custom {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: white;
            border-radius: 12px;
            padding: 12px 15px;
        }
        .form-control-custom:focus {
            background: rgba(255, 255, 255, 0.08);
            border-color: #f093fb;
            box-shadow: 0 0 20px rgba(240, 147, 251, 0.1);
            color: white;
        }
        .form-control-custom::placeholder {
            color: rgba(255,255,255,0.3);
        }
        .btn-login {
            background: linear-gradient(135deg, #f093fb, #f5576c);
            border: none;
            padding: 12px;
            border-radius: 12px;
            font-weight: 700;
            color: white;
            width: 100%;
            transition: all 0.3s;
        }
        .btn-login:hover {
            transform: scale(1.02);
            box-shadow: 0 10px 30px rgba(245, 87, 108, 0.3);
        }
        .error-message {
            color: #fca5a5;
            font-size: 0.9rem;
            margin-top: 10px;
            padding: 10px;
            background: rgba(239, 68, 68, 0.1);
            border-radius: 8px;
            border: 1px solid rgba(239, 68, 68, 0.2);
            text-align: center;
        }
        .back-link {
            color: rgba(255,255,255,0.3);
            text-decoration: none;
            display: block;
            text-align: center;
            margin-top: 15px;
            transition: all 0.3s;
        }
        .back-link:hover {
            color: rgba(255,255,255,0.6);
        }
    </style>
</head>
<body>
    <div class="login-card">
        <i class="bi bi-shield-lock login-icon"></i>
        <h3 class="login-title">لوحة التحكم</h3>
        <p class="login-sub">أدخل كلمة السر للوصول</p>
        
        <form method="POST">
            <input type="password" name="password" class="form-control form-control-custom mb-3" 
                   placeholder="كلمة السر" required autofocus>
            <button type="submit" class="btn btn-login">
                <i class="bi bi-box-arrow-in-right"></i> دخول
            </button>
        </form>
        
        {% if error %}
            <div class="error-message">
                <i class="bi bi-exclamation-circle-fill"></i> {{ error }}
            </div>
        {% endif %}
        
        <a href="/" class="back-link">
            <i class="bi bi-arrow-right"></i> العودة للمدونة
        </a>
    </div>
</body>
</html>
'''

# ======================
# الصفحة الرئيسية (للزوار)
# ======================
@app.route('/')
def index():
    posts = Post.query.order_by(Post.date.desc()).all()
    with open('index.html', encoding='utf-8') as f:
        template = f.read()
    return render_template_string(template, posts=posts, get_category_label=get_category_label, get_category_icon=get_category_icon, get_category_color=get_category_color)

# ======================
# لوحة التحكم (خاصة بالأدمن)
# ======================
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('admin'):
        posts = Post.query.order_by(Post.date.desc()).all()
        with open('admin.html', encoding='utf-8') as f:
            template = f.read()
        return render_template_string(template, posts=posts, get_category_label=get_category_label, get_category_color=get_category_color)
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == '1234':
            session['admin'] = True
            session['login_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return redirect(url_for('admin'))
        else:
            return render_template_string(ADMIN_LOGIN_TEMPLATE, error='❌ كلمة السر غير صحيحة')
    
    return render_template_string(ADMIN_LOGIN_TEMPLATE, error=None)

# ======================
# إضافة تدوينة (خاص بالأدمن) - مع صورة ونوع
# ======================
@app.route('/add', methods=['POST'])
def add():
    if not session.get('admin'):
        return "غير مصرح لك", 403
    
    content = request.form.get('content', '').strip()
    category = request.form.get('category', 'general')
    
    if not content:
        return "المحتوى مطلوب", 400
    
    # معالجة الصورة
    image_filename = None
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename and allowed_file(file.filename):
            # إنشاء اسم ملف فريد
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            image_filename = f"uploads/{filename}"
    
    post = Post(content=content, image=image_filename, category=category)
    db.session.add(post)
    db.session.commit()
    return redirect(url_for('admin'))

# ======================
# حذف تدوينة (خاص بالأدمن) - مع حذف الصورة
# ======================
@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    if not session.get('admin'):
        return "غير مصرح لك", 403
    
    post = Post.query.get(id)
    if post:
        # حذف الصورة من المجلد إن وجدت
        if post.image:
            image_path = os.path.join('static', post.image)
            if os.path.exists(image_path):
                os.remove(image_path)
        db.session.delete(post)
        db.session.commit()
    return redirect(url_for('admin'))

# ======================
# تسجيل الخروج
# ======================
@app.route('/logout')
def logout():
    session.pop('admin', None)
    session.pop('login_time', None)
    return redirect(url_for('index'))

# ======================
# الصفحات الخاصة (تصفية حسب النوع)
# ======================
@app.route('/cities')
def cities():
    posts = Post.query.filter_by(category='cities').order_by(Post.date.desc()).all()
    return render_category_page('مدن زرتها', '🗺️ استكشف المدن التي زرتها وذكرياتك فيها', 'bi-geo-alt-fill', '#4ecdc4', posts)

@app.route('/experience')
def experience():
    posts = Post.query.filter_by(category='experience').order_by(Post.date.desc()).all()
    return render_category_page('تجربة خاصة', '✨ لحظات وتجارب غيرت حياتك', 'bi-star-fill', '#ff6b6b', posts)

@app.route('/moments')
def moments():
    posts = Post.query.filter_by(category='moments').order_by(Post.date.desc()).all()
    return render_category_page('لحظات خاصة', '📸 أجمل اللحظات التي لا تنسى', 'bi-camera-fill', '#feca57', posts)

@app.route('/memories')
def memories():
    posts = Post.query.filter_by(category='memories').order_by(Post.date.desc()).all()
    return render_category_page('ذكريات', '📖 ذكريات تبقى في القلب', 'bi-bookmark-fill', '#a29bfe', posts)

@app.route('/dates')
def dates():
    posts = Post.query.filter_by(category='dates').order_by(Post.date.desc()).all()
    return render_category_page('تواريخ', '📅 تواريخ مهمة في حياتك', 'bi-calendar-event-fill', '#fd79a8', posts)

# ======================
# دالة مساعدة لعرض صفحات التصنيفات
# ======================
def render_category_page(title, subtitle, icon, color, posts):
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
            <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap" rel="stylesheet">
            <title>{{ title }} - مدونتي</title>
            <style>
                * { font-family: 'Cairo', sans-serif; }
                body { background: #f8f9fa; padding: 40px 20px; }
                .container { max-width: 750px; margin: 0 auto; }
                .page-header { text-align: center; padding-bottom: 30px; border-bottom: 1px solid #e9ecef; margin-bottom: 30px; }
                .page-header h1 { font-size: 2.2rem; font-weight: 700; color: #2d3436; }
                .page-header h1 i { color: {{ color }}; }
                .page-header p { color: #868e96; }
                .back-btn { display: inline-block; margin-top: 15px; padding: 8px 25px; background: #6c63ff; color: white; border-radius: 30px; text-decoration: none; transition: all 0.3s; }
                .back-btn:hover { background: #5a52d5; color: white; transform: translateY(-2px); }
                .post-card { background: white; border-radius: 16px; padding: 25px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.03); border: 1px solid #e9ecef; border-right: 4px solid {{ color }}; }
                .post-card img { max-width: 100%; border-radius: 12px; margin-top: 15px; }
                .post-content { font-size: 1.1rem; line-height: 1.9; color: #2d3748; }
                .post-meta { display: flex; justify-content: flex-end; margin-top: 15px; padding-top: 15px; border-top: 1px solid #f1f3f5; }
                .post-date { color: #868e96; font-size: 0.85rem; }
                .empty-state { text-align: center; padding: 60px 20px; background: white; border-radius: 16px; border: 2px dashed #dee2e6; }
                .empty-state i { font-size: 3.5rem; color: #dee2e6; }
                .footer { text-align: center; margin-top: 40px; color: #b2bec3; font-size: 0.8rem; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="page-header">
                    <h1><i class="bi {{ icon }}"></i> {{ title }}</h1>
                    <p>{{ subtitle }}</p>
                    <a href="/" class="back-btn"><i class="bi bi-arrow-right"></i> العودة للرئيسية</a>
                </div>
                
                {% if posts %}
                    {% for post in posts %}
                        <div class="post-card">
                            <div class="post-content">{{ post.content }}</div>
                            {% if post.image %}
                                <img src="/static/{{ post.image }}" alt="صورة التدوينة">
                            {% endif %}
                            <div class="post-meta">
                                <span class="post-date"><i class="bi bi-clock"></i> {{ post.date.strftime('%Y-%m-%d %H:%M') }}</span>
                            </div>
                        </div>
                    {% endfor %}
                {% else %}
                    <div class="empty-state">
                        <i class="bi bi-journal-text"></i>
                        <h5 class="mt-3">لا توجد تدوينات في هذا القسم</h5>
                        <p style="color: #868e96;">قم بإضافة تدوينة جديدة من لوحة التحكم! ✨</p>
                    </div>
                {% endif %}
                
                <div class="footer">© 2026 مدونتي</div>
            </div>
        </body>
        </html>
    ''', title=title, subtitle=subtitle, icon=icon, color=color, posts=posts)

# ======================
# تشغيل التطبيق
# ======================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(host='0.0.0.0', port=port, debug=debug)
