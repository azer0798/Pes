from flask import Flask, render_template_string, request, redirect, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import uuid
from werkzeug.utils import secure_filename
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import func

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default-secret-key-please-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# إعدادات رفع الصور
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# إنشاء مجلد static/uploads
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

# ======================
# نماذج قاعدة البيانات
# ======================

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(50), nullable=False, default='general')
    date = db.Column(db.DateTime, default=datetime.utcnow)
    views = db.Column(db.Integer, default=0)  # عدد المشاهدات
    likes = db.Column(db.Integer, default=0)  # عدد الإعجابات
    
    def __repr__(self):
        return f'<Post {self.id}: {self.content[:20]}...>'

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False, default='زائر')
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    post = db.relationship('Post', backref=db.backref('comments', lazy=True, cascade='all, delete-orphan'))

class Visitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True)
    first_visit = db.Column(db.DateTime, default=datetime.utcnow)
    last_visit = db.Column(db.DateTime, default=datetime.utcnow)
    visits_count = db.Column(db.Integer, default=1)

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    session_id = db.Column(db.String(100), nullable=False)
    
    __table_args__ = (db.UniqueConstraint('post_id', 'session_id', name='unique_like'),)

class Subscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# ======================
# دوال مساعدة
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

def get_visitor_session():
    """الحصول على معرف الزائر الفريد"""
    if 'visitor_id' not in session:
        session['visitor_id'] = str(uuid.uuid4())
    return session['visitor_id']

def track_visitor():
    """تتبع الزوار"""
    visitor_id = get_visitor_session()
    visitor = Visitor.query.filter_by(session_id=visitor_id).first()
    if visitor:
        visitor.last_visit = datetime.utcnow()
        visitor.visits_count += 1
    else:
        visitor = Visitor(session_id=visitor_id)
        db.session.add(visitor)
    db.session.commit()
    return visitor

def get_total_visitors():
    """الحصول على عدد الزوار الكلي"""
    return Visitor.query.count()

def get_online_visitors():
    """الحصول على عدد الزوار النشطين (آخر 5 دقائق)"""
    from datetime import timedelta
    threshold = datetime.utcnow() - timedelta(minutes=5)
    return Visitor.query.filter(Visitor.last_visit >= threshold).count()

# ======================
# قالب تسجيل الدخول
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
        .login-icon { font-size: 3rem; color: #f093fb; text-align: center; display: block; margin-bottom: 15px; }
        .login-title { color: white; text-align: center; font-weight: 700; margin-bottom: 5px; }
        .login-sub { color: rgba(255,255,255,0.4); text-align: center; font-size: 0.9rem; margin-bottom: 25px; }
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
        .form-control-custom::placeholder { color: rgba(255,255,255,0.3); }
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
        .back-link:hover { color: rgba(255,255,255,0.6); }
    </style>
</head>
<body>
    <div class="login-card">
        <i class="bi bi-shield-lock login-icon"></i>
        <h3 class="login-title">لوحة التحكم</h3>
        <p class="login-sub">أدخل كلمة السر للوصول</p>
        <form method="POST">
            <input type="password" name="password" class="form-control form-control-custom mb-3" placeholder="كلمة السر" required autofocus>
            <button type="submit" class="btn btn-login"><i class="bi bi-box-arrow-in-right"></i> دخول</button>
        </form>
        {% if error %}
            <div class="error-message"><i class="bi bi-exclamation-circle-fill"></i> {{ error }}</div>
        {% endif %}
        <a href="/" class="back-link"><i class="bi bi-arrow-right"></i> العودة للمدونة</a>
    </div>
</body>
</html>
'''

# ======================
# الصفحة الرئيسية (مع ترقيم الصفحات)
# ======================
@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 5
    
    # تتبع الزائر
    track_visitor()
    
    # جلب التدوينات مع ترقيم الصفحات
    pagination = Post.query.order_by(Post.date.desc()).paginate(page=page, per_page=per_page)
    posts = pagination.items
    total_pages = pagination.pages
    current_page = page
    
    with open('index.html', encoding='utf-8') as f:
        template = f.read()
    return render_template_string(template, 
                                  posts=posts, 
                                  total_pages=total_pages, 
                                  current_page=current_page,
                                  get_category_label=get_category_label,
                                  get_category_icon=get_category_icon,
                                  get_category_color=get_category_color)

# ======================
# عرض تدوينة مفردة (لزيادة المشاهدات)
# ======================
@app.route('/post/<int:id>')
def view_post(id):
    post = Post.query.get_or_404(id)
    # زيادة عدد المشاهدات
    post.views += 1
    db.session.commit()
    
    # جلب التعليقات
    comments = Comment.query.filter_by(post_id=id).order_by(Comment.date.desc()).all()
    
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
            <title>التدوينة - مدونتي</title>
            <style>
                * { font-family: 'Cairo', sans-serif; }
                body { background: #f8f9fa; padding: 30px 20px; }
                .container { max-width: 750px; margin: 0 auto; }
                .post-card { background: white; border-radius: 16px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
                .post-card img { max-width: 100%; border-radius: 12px; margin: 15px 0; }
                .post-meta { display: flex; gap: 20px; flex-wrap: wrap; color: #868e96; font-size: 0.9rem; margin: 15px 0; }
                .back-btn { display: inline-block; margin-top: 20px; padding: 8px 25px; background: #6c63ff; color: white; border-radius: 30px; text-decoration: none; }
                .back-btn:hover { background: #5a52d5; color: white; }
                .comments-section { margin-top: 30px; }
                .comment-card { background: #f8f9fa; border-radius: 12px; padding: 15px; margin-bottom: 10px; }
                .comment-name { font-weight: 600; color: #2d3436; }
                .comment-date { color: #868e96; font-size: 0.8rem; }
                .comment-form textarea { border-radius: 12px; border: 1px solid #e9ecef; padding: 12px; width: 100%; }
                .comment-form button { background: #6c63ff; color: white; border: none; padding: 10px 25px; border-radius: 30px; }
                .btn-like { background: none; border: none; color: #e74c3c; font-size: 1.2rem; transition: all 0.3s; }
                .btn-like:hover { transform: scale(1.2); }
                .btn-like.liked { color: #e74c3c; }
                .share-btn { background: none; border: none; color: #6c63ff; font-size: 1.2rem; transition: all 0.3s; }
                .share-btn:hover { transform: scale(1.1); }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="post-card">
                    <h3 class="mb-3">{{ post.content[:50] }}...</h3>
                    <div class="post-meta">
                        <span><i class="bi bi-eye"></i> {{ post.views }} مشاهدة</span>
                        <span><i class="bi bi-heart"></i> <span id="like-count">{{ post.likes }}</span> إعجاب</span>
                        <span><i class="bi bi-chat"></i> {{ comments|length }} تعليق</span>
                        <span><i class="bi bi-clock"></i> {{ post.date.strftime('%Y-%m-%d %H:%M') }}</span>
                    </div>
                    
                    <div style="margin: 15px 0;">
                        <button class="btn-like" onclick="toggleLike({{ post.id }})" id="like-btn">
                            <i class="bi bi-heart-fill"></i> أعجبني
                        </button>
                        <button class="share-btn" onclick="sharePost()">
                            <i class="bi bi-share-fill"></i> مشاركة
                        </button>
                    </div>
                    
                    {% if post.image %}
                        <img src="/static/{{ post.image }}" alt="صورة التدوينة">
                    {% endif %}
                    
                    <div class="post-content" style="font-size: 1.1rem; line-height: 1.9; color: #2d3748;">
                        {{ post.content }}
                    </div>
                    
                    <a href="/" class="back-btn"><i class="bi bi-arrow-right"></i> العودة للرئيسية</a>
                </div>
                
                <!-- التعليقات -->
                <div class="comments-section">
                    <h5><i class="bi bi-chat-dots"></i> التعليقات ({{ comments|length }})</h5>
                    
                    {% for comment in comments %}
                        <div class="comment-card">
                            <div class="comment-name">{{ comment.name }}</div>
                            <div>{{ comment.content }}</div>
                            <div class="comment-date">{{ comment.date.strftime('%Y-%m-%d %H:%M') }}</div>
                        </div>
                    {% endfor %}
                    
                    <div class="comment-form mt-3">
                        <h6>💬 أضف تعليقاً</h6>
                        <form action="/comment/{{ post.id }}" method="POST">
                            <input type="text" name="name" class="form-control mb-2" placeholder="اسمك (اختياري)" style="border-radius: 12px;">
                            <textarea name="content" class="form-control mb-2" placeholder="اكتب تعليقك..." rows="3" required style="border-radius: 12px;"></textarea>
                            <button type="submit"><i class="bi bi-send"></i> نشر التعليق</button>
                        </form>
                    </div>
                </div>
            </div>
            
            <script>
                function toggleLike(postId) {
                    fetch('/like/' + postId, { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('like-count').textContent = data.likes;
                            const btn = document.getElementById('like-btn');
                            btn.classList.toggle('liked');
                        });
                }
                
                function sharePost() {
                    if (navigator.share) {
                        navigator.share({
                            title: '{{ post.content[:30] }}',
                            url: window.location.href
                        });
                    } else {
                        navigator.clipboard.writeText(window.location.href);
                        alert('✅ تم نسخ الرابط!');
                    }
                }
            </script>
        </body>
        </html>
    ''', post=post, comments=comments)

# ======================
# إضافة تعليق
# ======================
@app.route('/comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    name = request.form.get('name', '').strip() or 'زائر'
    content = request.form.get('content', '').strip()
    
    if not content:
        return "التعليق مطلوب", 400
    
    comment = Comment(post_id=post_id, name=name, content=content)
    db.session.add(comment)
    db.session.commit()
    
    return redirect(url_for('view_post', id=post_id))

# ======================
# إعجاب بتدوينة (API)
# ======================
@app.route('/like/<int:post_id>', methods=['POST'])
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    visitor_id = get_visitor_session()
    
    # التحقق إذا كان المستخدم أعجب سابقاً
    existing_like = Like.query.filter_by(post_id=post_id, session_id=visitor_id).first()
    
    if existing_like:
        # إزالة الإعجاب
        db.session.delete(existing_like)
        post.likes -= 1
        liked = False
    else:
        # إضافة إعجاب
        like = Like(post_id=post_id, session_id=visitor_id)
        db.session.add(like)
        post.likes += 1
        liked = True
    
    db.session.commit()
    
    return jsonify({'likes': post.likes, 'liked': liked})

# ======================
# لوحة التحكم (مع الإحصائيات)
# ======================
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('admin'):
        posts = Post.query.order_by(Post.date.desc()).all()
        total_posts = Post.query.count()
        total_comments = Comment.query.count()
        total_visitors = get_total_visitors()
        online_visitors = get_online_visitors()
        total_likes = db.session.query(func.sum(Post.likes)).scalar() or 0
        
        stats = {
            'total_posts': total_posts,
            'total_comments': total_comments,
            'total_visitors': total_visitors,
            'online_visitors': online_visitors,
            'total_likes': total_likes
        }
        
        with open('admin.html', encoding='utf-8') as f:
            template = f.read()
        return render_template_string(template, posts=posts, stats=stats, 
                                      get_category_label=get_category_label,
                                      get_category_color=get_category_color)
    
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
# إضافة تدوينة
# ======================
@app.route('/add', methods=['POST'])
def add():
    if not session.get('admin'):
        return "غير مصرح لك", 403
    
    content = request.form.get('content', '').strip()
    category = request.form.get('category', 'general')
    
    if not content:
        return "المحتوى مطلوب", 400
    
    image_filename = None
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename and allowed_file(file.filename):
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
# حذف تدوينة
# ======================
@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    if not session.get('admin'):
        return "غير مصرح لك", 403
    
    post = Post.query.get(id)
    if post:
        if post.image:
            image_path = os.path.join('static', post.image)
            if os.path.exists(image_path):
                os.remove(image_path)
        # حذف التعليقات المرتبطة (cascade)
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
# الصفحات الخاصة (تصفية حسب النوع مع ترقيم)
# ======================
@app.route('/cities')
def cities():
    return render_category_page('cities', 'مدن زرتها', '🗺️ استكشف المدن التي زرتها وذكرياتك فيها', 'bi-geo-alt-fill', '#4ecdc4')

@app.route('/experience')
def experience():
    return render_category_page('experience', 'تجربة خاصة', '✨ لحظات وتجارب غيرت حياتك', 'bi-star-fill', '#ff6b6b')

@app.route('/moments')
def moments():
    return render_category_page('moments', 'لحظات خاصة', '📸 أجمل اللحظات التي لا تنسى', 'bi-camera-fill', '#feca57')

@app.route('/memories')
def memories():
    return render_category_page('memories', 'ذكريات', '📖 ذكريات تبقى في القلب', 'bi-bookmark-fill', '#a29bfe')

@app.route('/dates')
def dates():
    return render_category_page('dates', 'تواريخ', '📅 تواريخ مهمة في حياتك', 'bi-calendar-event-fill', '#fd79a8')

def render_category_page(category, title, subtitle, icon, color):
    page = request.args.get('page', 1, type=int)
    per_page = 5
    
    pagination = Post.query.filter_by(category=category).order_by(Post.date.desc()).paginate(page=page, per_page=per_page)
    posts = pagination.items
    total_pages = pagination.pages
    current_page = page
    
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
                .post-card { background: white; border-radius: 16px; padding: 25px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.03); border: 1px solid #e9ecef; border-right: 4px solid {{ color }}; transition: all 0.3s; }
                .post-card:hover { box-shadow: 0 8px 30px rgba(0,0,0,0.06); transform: translateY(-2px); }
                .post-card img { max-width: 100%; border-radius: 12px; margin-top: 15px; max-height: 300px; object-fit: cover; }
                .post-content { font-size: 1.1rem; line-height: 1.9; color: #2d3748; }
                .post-meta { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-top: 15px; padding-top: 15px; border-top: 1px solid #f1f3f5; gap: 10px; }
                .post-stats { display: flex; gap: 15px; color: #868e96; font-size: 0.85rem; }
                .post-date { color: #868e96; font-size: 0.85rem; }
                .post-category-badge { display: inline-block; padding: 2px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; margin-bottom: 10px; background: {{ color }}20; color: {{ color }}; border: 1px solid {{ color }}40; }
                .empty-state { text-align: center; padding: 60px 20px; background: white; border-radius: 16px; border: 2px dashed #dee2e6; }
                .empty-state i { font-size: 3.5rem; color: #dee2e6; }
                .pagination { display: flex; justify-content: center; gap: 8px; margin-top: 30px; }
                .pagination a { padding: 8px 16px; border: 1px solid #e9ecef; border-radius: 8px; text-decoration: none; color: #6c63ff; transition: all 0.3s; }
                .pagination a:hover { background: #6c63ff; color: white; }
                .pagination .active { background: #6c63ff; color: white; }
                .pagination .disabled { color: #ccc; pointer-events: none; }
                .footer { text-align: center; margin-top: 40px; color: #b2bec3; font-size: 0.8rem; }
                .read-more { color: #6c63ff; text-decoration: none; font-weight: 600; }
                .read-more:hover { text-decoration: underline; }
                @media (max-width: 576px) { .post-card { padding: 20px; } .post-meta { flex-direction: column; align-items: flex-start; } }
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
                            <span class="post-category-badge">{{ get_category_label(post.category) }}</span>
                            <div class="post-content">{{ post.content }}</div>
                            {% if post.image %}
                                <img src="/static/{{ post.image }}" alt="صورة التدوينة">
                            {% endif %}
                            <div class="post-meta">
                                <div class="post-stats">
                                    <span><i class="bi bi-eye"></i> {{ post.views }}</span>
                                    <span><i class="bi bi-heart"></i> {{ post.likes }}</span>
                                    <span><i class="bi bi-chat"></i> {{ post.comments|length }}</span>
                                </div>
                                <span class="post-date"><i class="bi bi-clock"></i> {{ post.date.strftime('%Y-%m-%d %H:%M') }}</span>
                            </div>
                            <a href="/post/{{ post.id }}" class="read-more">اقرأ المزيد →</a>
                        </div>
                    {% endfor %}
                    
                    <!-- ترقيم الصفحات -->
                    {% if total_pages > 1 %}
                        <div class="pagination">
                            {% if current_page > 1 %}
                                <a href="?page={{ current_page - 1 }}">‹ السابق</a>
                            {% else %}
                                <span class="disabled">‹ السابق</span>
                            {% endif %}
                            
                            {% for p in range(1, total_pages + 1) %}
                                {% if p == current_page %}
                                    <span class="active">{{ p }}</span>
                                {% else %}
                                    <a href="?page={{ p }}">{{ p }}</a>
                                {% endif %}
                            {% endfor %}
                            
                            {% if current_page < total_pages %}
                                <a href="?page={{ current_page + 1 }}">التالي ›</a>
                            {% else %}
                                <span class="disabled">التالي ›</span>
                            {% endif %}
                        </div>
                    {% endif %}
                    
                {% else %}
                    <div class="empty-state">
                        <i class="bi bi-journal-text"></i>
                        <h5 class="mt-3">لا توجد تدوينات في هذا القسم</h5>
                        <p style="color: #868e96;">قم بإضافة تدوينة جديدة من لوحة التحكم! ✨</p>
                    </div>
                {% endif %}
                
                <div class="footer">© 2026 مدونتي</div>
            </div>
            <script>
                document.querySelectorAll('.post-card .post-content').forEach(el => {
                    if (el.textContent.length > 200) {
                        el.textContent = el.textContent.substring(0, 200) + '...';
                    }
                });
            </script>
        </body>
        </html>
    ''', posts=posts, total_pages=total_pages, current_page=current_page, 
    title=title, subtitle=subtitle, icon=icon, color=color,
    get_category_label=get_category_label)

# ======================
# تشغيل التطبيق
# ======================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(host='0.0.0.0', port=port, debug=debug)
