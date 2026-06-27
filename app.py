from flask import Flask, render_template_string, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
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

with app.app_context():
    db.create_all()

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
    return render_template_string(template, posts=posts)

# ======================
# لوحة التحكم (خاصة بالأدمن)
# ======================
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('admin'):
        posts = Post.query.order_by(Post.date.desc()).all()
        with open('admin.html', encoding='utf-8') as f:
            template = f.read()
        return render_template_string(template, posts=posts)
    
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
# إضافة تدوينة (خاص بالأدمن)
# ======================
@app.route('/add', methods=['POST'])
def add():
    if not session.get('admin'):
        return "غير مصرح لك", 403
    
    content = request.form.get('content', '').strip()
    if not content:
        return "المحتوى مطلوب", 400
    
    post = Post(content=content)
    db.session.add(post)
    db.session.commit()
    return redirect(url_for('admin'))

# ======================
# حذف تدوينة (خاص بالأدمن)
# ======================
@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    if not session.get('admin'):
        return "غير مصرح لك", 403
    
    post = Post.query.get(id)
    if post:
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
# الصفحات الخاصة (للقائمة المنسدلة)
# ======================

@app.route('/cities')
def cities():
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
            <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap" rel="stylesheet">
            <title>مدن زرتها - مدونتي</title>
            <style>
                * { font-family: 'Cairo', sans-serif; }
                body { background: #f8f9fa; padding: 40px 20px; }
                .container { max-width: 750px; margin: 0 auto; }
                .page-header { text-align: center; padding-bottom: 30px; border-bottom: 1px solid #e9ecef; margin-bottom: 30px; }
                .page-header h1 { font-size: 2.2rem; font-weight: 700; color: #2d3436; }
                .page-header h1 i { color: #4ecdc4; }
                .page-header p { color: #868e96; }
                .back-btn { display: inline-block; margin-top: 15px; padding: 8px 25px; background: #6c63ff; color: white; border-radius: 30px; text-decoration: none; transition: all 0.3s; }
                .back-btn:hover { background: #5a52d5; color: white; transform: translateY(-2px); }
                .content-card { background: white; border-radius: 16px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.03); border: 1px solid #e9ecef; }
                .content-card h3 { color: #2d3436; }
                .content-card p { color: #636e72; line-height: 1.8; }
                .footer { text-align: center; margin-top: 40px; color: #b2bec3; font-size: 0.8rem; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="page-header">
                    <h1><i class="bi bi-geo-alt-fill"></i> مدن زرتها</h1>
                    <p>🗺️ استكشف المدن التي زرتها وذكرياتك فيها</p>
                    <a href="/" class="back-btn"><i class="bi bi-arrow-right"></i> العودة للرئيسية</a>
                </div>
                <div class="content-card">
                    <h3>🌍 قائمة المدن</h3>
                    <p>هنا ستظهر قائمة المدن التي زرتها مع تفاصيل كل رحلة...</p>
                    <p style="color: #b2bec3; font-size: 0.9rem;">✍️ قم بإضافة محتوى مدنك هنا</p>
                </div>
                <div class="footer">© 2026 مدونتي</div>
            </div>
        </body>
        </html>
    ''')

@app.route('/experience')
def experience():
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
            <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap" rel="stylesheet">
            <title>تجربة خاصة - مدونتي</title>
            <style>
                * { font-family: 'Cairo', sans-serif; }
                body { background: #f8f9fa; padding: 40px 20px; }
                .container { max-width: 750px; margin: 0 auto; }
                .page-header { text-align: center; padding-bottom: 30px; border-bottom: 1px solid #e9ecef; margin-bottom: 30px; }
                .page-header h1 { font-size: 2.2rem; font-weight: 700; color: #2d3436; }
                .page-header h1 i { color: #ff6b6b; }
                .page-header p { color: #868e96; }
                .back-btn { display: inline-block; margin-top: 15px; padding: 8px 25px; background: #6c63ff; color: white; border-radius: 30px; text-decoration: none; transition: all 0.3s; }
                .back-btn:hover { background: #5a52d5; color: white; transform: translateY(-2px); }
                .content-card { background: white; border-radius: 16px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.03); border: 1px solid #e9ecef; }
                .content-card h3 { color: #2d3436; }
                .content-card p { color: #636e72; line-height: 1.8; }
                .footer { text-align: center; margin-top: 40px; color: #b2bec3; font-size: 0.8rem; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="page-header">
                    <h1><i class="bi bi-star-fill"></i> تجربة خاصة</h1>
                    <p>✨ لحظات وتجارب غيرت حياتك</p>
                    <a href="/" class="back-btn"><i class="bi bi-arrow-right"></i> العودة للرئيسية</a>
                </div>
                <div class="content-card">
                    <h3>🌟 تجاربي المميزة</h3>
                    <p>هنا ستشارك تجاربك الفريدة والخاصة...</p>
                    <p style="color: #b2bec3; font-size: 0.9rem;">✍️ قم بإضافة محتوى تجاربك هنا</p>
                </div>
                <div class="footer">© 2026 مدونتي</div>
            </div>
        </body>
        </html>
    ''')

@app.route('/moments')
def moments():
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
            <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap" rel="stylesheet">
            <title>لحظات خاصة - مدونتي</title>
            <style>
                * { font-family: 'Cairo', sans-serif; }
                body { background: #f8f9fa; padding: 40px 20px; }
                .container { max-width: 750px; margin: 0 auto; }
                .page-header { text-align: center; padding-bottom: 30px; border-bottom: 1px solid #e9ecef; margin-bottom: 30px; }
                .page-header h1 { font-size: 2.2rem; font-weight: 700; color: #2d3436; }
                .page-header h1 i { color: #feca57; }
                .page-header p { color: #868e96; }
                .back-btn { display: inline-block; margin-top: 15px; padding: 8px 25px; background: #6c63ff; color: white; border-radius: 30px; text-decoration: none; transition: all 0.3s; }
                .back-btn:hover { background: #5a52d5; color: white; transform: translateY(-2px); }
                .content-card { background: white; border-radius: 16px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.03); border: 1px solid #e9ecef; }
                .content-card h3 { color: #2d3436; }
                .content-card p { color: #636e72; line-height: 1.8; }
                .footer { text-align: center; margin-top: 40px; color: #b2bec3; font-size: 0.8rem; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="page-header">
                    <h1><i class="bi bi-camera-fill"></i> لحظات خاصة</h1>
                    <p>📸 أجمل اللحظات التي لا تنسى</p>
                    <a href="/" class="back-btn"><i class="bi bi-arrow-right"></i> العودة للرئيسية</a>
                </div>
                <div class="content-card">
                    <h3>📷 لحظاتي المميزة</h3>
                    <p>هنا ستشارك أجمل اللحظات في حياتك...</p>
                    <p style="color: #b2bec3; font-size: 0.9rem;">✍️ قم بإضافة محتوى لحظاتك هنا</p>
                </div>
                <div class="footer">© 2026 مدونتي</div>
            </div>
        </body>
        </html>
    ''')

@app.route('/memories')
def memories():
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
            <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap" rel="stylesheet">
            <title>ذكريات - مدونتي</title>
            <style>
                * { font-family: 'Cairo', sans-serif; }
                body { background: #f8f9fa; padding: 40px 20px; }
                .container { max-width: 750px; margin: 0 auto; }
                .page-header { text-align: center; padding-bottom: 30px; border-bottom: 1px solid #e9ecef; margin-bottom: 30px; }
                .page-header h1 { font-size: 2.2rem; font-weight: 700; color: #2d3436; }
                .page-header h1 i { color: #a29bfe; }
                .page-header p { color: #868e96; }
                .back-btn { display: inline-block; margin-top: 15px; padding: 8px 25px; background: #6c63ff; color: white; border-radius: 30px; text-decoration: none; transition: all 0.3s; }
                .back-btn:hover { background: #5a52d5; color: white; transform: translateY(-2px); }
                .content-card { background: white; border-radius: 16px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.03); border: 1px solid #e9ecef; }
                .content-card h3 { color: #2d3436; }
                .content-card p { color: #636e72; line-height: 1.8; }
                .footer { text-align: center; margin-top: 40px; color: #b2bec3; font-size: 0.8rem; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="page-header">
                    <h1><i class="bi bi-bookmark-fill"></i> ذكريات</h1>
                    <p>📖 ذكريات تبقى في القلب</p>
                    <a href="/" class="back-btn"><i class="bi bi-arrow-right"></i> العودة للرئيسية</a>
                </div>
                <div class="content-card">
                    <h3>📚 ذكرياتي الجميلة</h3>
                    <p>هنا ستشارك ذكرياتك التي تريد الاحتفاظ بها...</p>
                    <p style="color: #b2bec3; font-size: 0.9rem;">✍️ قم بإضافة محتوى ذكرياتك هنا</p>
                </div>
                <div class="footer">© 2026 مدونتي</div>
            </div>
        </body>
        </html>
    ''')

@app.route('/dates')
def dates():
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
            <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap" rel="stylesheet">
            <title>تواريخ - مدونتي</title>
            <style>
                * { font-family: 'Cairo', sans-serif; }
                body { background: #f8f9fa; padding: 40px 20px; }
                .container { max-width: 750px; margin: 0 auto; }
                .page-header { text-align: center; padding-bottom: 30px; border-bottom: 1px solid #e9ecef; margin-bottom: 30px; }
                .page-header h1 { font-size: 2.2rem; font-weight: 700; color: #2d3436; }
                .page-header h1 i { color: #fd79a8; }
                .page-header p { color: #868e96; }
                .back-btn { display: inline-block; margin-top: 15px; padding: 8px 25px; background: #6c63ff; color: white; border-radius: 30px; text-decoration: none; transition: all 0.3s; }
                .back-btn:hover { background: #5a52d5; color: white; transform: translateY(-2px); }
                .content-card { background: white; border-radius: 16px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.03); border: 1px solid #e9ecef; }
                .content-card h3 { color: #2d3436; }
                .content-card p { color: #636e72; line-height: 1.8; }
                .footer { text-align: center; margin-top: 40px; color: #b2bec3; font-size: 0.8rem; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="page-header">
                    <h1><i class="bi bi-calendar-event-fill"></i> تواريخ</h1>
                    <p>📅 تواريخ مهمة في حياتك</p>
                    <a href="/" class="back-btn"><i class="bi bi-arrow-right"></i> العودة للرئيسية</a>
                </div>
                <div class="content-card">
                    <h3>🗓️ تواريخي المهمة</h3>
                    <p>هنا ستشارك التواريخ التي تعني لك الكثير...</p>
                    <p style="color: #b2bec3; font-size: 0.9rem;">✍️ قم بإضافة محتوى تواريخك هنا</p>
                </div>
                <div class="footer">© 2026 مدونتي</div>
            </div>
        </body>
        </html>
    ''')

# ======================
# تشغيل التطبيق
# ======================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(host='0.0.0.0', port=port, debug=debug)
