from flask import Flask, render_template_string, request, redirect, session, url_for, jsonify
from datetime import datetime
import os
import uuid
import cloudinary
import cloudinary.uploader
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)

# ======================
# إعدادات التطبيق من متغيرات البيئة (Render)
# ======================
app.secret_key = os.environ.get('SECRET_KEY', 'default-secret-key-change-this')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASS', '1234')
DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

# ======================
# إعدادات MongoDB
# ======================
MONGO_URI = os.environ.get('MONGO_URI')
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI غير موجود في متغيرات البيئة")

client = MongoClient(MONGO_URI)
db = client.get_database('blog')

# ======================
# إعدادات Cloudinary (للصور)
# ======================
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_NAME', 'dyaiiu0if'),
    api_key=os.environ.get('CLOUDINARY_KEY'),
    api_secret=os.environ.get('CLOUDINARY_SECRET'),
    secure=True
)

# ======================
# دوال مساعدة للصور (Cloudinary)
# ======================

def upload_image_to_cloudinary(file):
    """رفع الصورة إلى Cloudinary مع تحسينات"""
    try:
        if not file or not file.filename:
            print("❌ لا يوجد ملف للرفع")
            return {'success': False, 'error': 'لا يوجد ملف'}

        print(f"📤 جاري رفع الصورة: {file.filename}")

        # التحقق من نوع الملف
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        file_ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        
        if file_ext not in allowed_extensions:
            print(f"⚠️ نوع الملف غير مدعوم: {file_ext}")
            return {'success': False, 'error': f'نوع الملف غير مدعوم: {file_ext}'}

        # رفع الصورة
        upload_result = cloudinary.uploader.upload(
            file,
            folder='blog_images',
            allowed_formats=['jpg', 'jpeg', 'png', 'gif', 'webp'],
            transformation=[
                {'width': 1200, 'height': 800, 'crop': 'limit'},
                {'quality': 'auto:best'},
                {'fetch_format': 'auto'}
            ],
            use_filename=True,
            unique_filename=True,
            resource_type='image'
        )

        print(f"✅ تم رفع الصورة بنجاح: {upload_result.get('public_id')}")
        print(f"✅ رابط الصورة: {upload_result.get('secure_url')}")

        return {
            'public_id': upload_result.get('public_id'),
            'url': upload_result.get('secure_url'),
            'success': True
        }
    except Exception as e:
        print(f"❌ خطأ في رفع الصورة: {str(e)}")
        return {'success': False, 'error': str(e)}

def delete_image_from_cloudinary(public_id):
    """حذف الصورة من Cloudinary"""
    try:
        if public_id:
            result = cloudinary.uploader.destroy(public_id)
            print(f"🗑️ تم حذف الصورة: {public_id}")
            return True
    except Exception as e:
        print(f"❌ خطأ في حذف الصورة: {e}")
        return False

# ======================
# دوال مساعدة أخرى
# ======================

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
    if 'visitor_id' not in session:
        session['visitor_id'] = str(uuid.uuid4())
    return session['visitor_id']

def track_visitor():
    visitor_id = get_visitor_session()
    visitors_collection = db.visitors
    visitor = visitors_collection.find_one({'session_id': visitor_id})
    
    if visitor:
        visitors_collection.update_one(
            {'session_id': visitor_id},
            {'$set': {'last_visit': datetime.utcnow()}, '$inc': {'visits_count': 1}}
        )
    else:
        visitors_collection.insert_one({
            'session_id': visitor_id,
            'first_visit': datetime.utcnow(),
            'last_visit': datetime.utcnow(),
            'visits_count': 1
        })

def get_total_visitors():
    return db.visitors.count_documents({})

def get_online_visitors():
    from datetime import timedelta
    threshold = datetime.utcnow() - timedelta(minutes=5)
    return db.visitors.count_documents({'last_visit': {'$gte': threshold}})

def serialize_post(post):
    post['_id'] = str(post['_id'])
    return post

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
    <title>دخول الأدمن</title>
    <style>
        body { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
        .login-card { background: rgba(255,255,255,0.05); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.1); padding: 40px; border-radius: 20px; max-width: 400px; width: 100%; }
        .login-icon { font-size: 3rem; color: #f093fb; text-align: center; display: block; margin-bottom: 15px; }
        .login-title { color: white; text-align: center; font-weight: 700; }
        .login-sub { color: rgba(255,255,255,0.4); text-align: center; font-size: 0.9rem; margin-bottom: 25px; }
        .form-control-custom { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: white; border-radius: 12px; padding: 12px 15px; }
        .form-control-custom:focus { background: rgba(255,255,255,0.08); border-color: #f093fb; box-shadow: 0 0 20px rgba(240,147,251,0.1); color: white; }
        .form-control-custom::placeholder { color: rgba(255,255,255,0.3); }
        .btn-login { background: linear-gradient(135deg, #f093fb, #f5576c); border: none; padding: 12px; border-radius: 12px; font-weight: 700; color: white; width: 100%; transition: all 0.3s; }
        .btn-login:hover { transform: scale(1.02); box-shadow: 0 10px 30px rgba(245,87,108,0.3); }
        .error-message { color: #fca5a5; font-size: 0.9rem; margin-top: 10px; padding: 10px; background: rgba(239,68,68,0.1); border-radius: 8px; border: 1px solid rgba(239,68,68,0.2); text-align: center; }
        .back-link { color: rgba(255,255,255,0.3); text-decoration: none; display: block; text-align: center; margin-top: 15px; }
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
            <button type="submit" class="btn-login"><i class="bi bi-box-arrow-in-right"></i> دخول</button>
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
# المسارات (Routes)
# ======================

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 5
    
    track_visitor()
    
    posts_cursor = db.posts.find().sort('date', -1).skip((page - 1) * per_page).limit(per_page)
    posts = [serialize_post(p) for p in posts_cursor]
    
    total_posts = db.posts.count_documents({})
    total_pages = (total_posts + per_page - 1) // per_page if total_posts > 0 else 1
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

@app.route('/post/<post_id>')
def view_post(post_id):
    post = db.posts.find_one({'_id': ObjectId(post_id)})
    if not post:
        return "التدوينة غير موجودة", 404
    
    db.posts.update_one({'_id': ObjectId(post_id)}, {'$inc': {'views': 1}})
    post = db.posts.find_one({'_id': ObjectId(post_id)})
    post = serialize_post(post)
    
    comments = list(db.comments.find({'post_id': post_id}).sort('date', -1))
    for c in comments:
        c['_id'] = str(c['_id'])
    
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
                        <button class="btn-like" onclick="toggleLike('{{ post._id }}')" id="like-btn">
                            <i class="bi bi-heart-fill"></i> أعجبني
                        </button>
                        <button class="share-btn" onclick="sharePost()">
                            <i class="bi bi-share-fill"></i> مشاركة
                        </button>
                    </div>
                    
                    {% if post.image_url %}
                        <img src="{{ post.image_url }}" alt="صورة التدوينة">
                    {% endif %}
                    
                    <div class="post-content" style="font-size: 1.1rem; line-height: 1.9; color: #2d3748;">
                        {{ post.content }}
                    </div>
                    
                    <a href="/" class="back-btn"><i class="bi bi-arrow-right"></i> العودة للرئيسية</a>
                </div>
                
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
                        <form action="/comment/{{ post._id }}" method="POST">
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
                        });
                }
                
                function sharePost() {
                    if (navigator.share) {
                        navigator.share({ title: '{{ post.content[:30] }}', url: window.location.href });
                    } else {
                        navigator.clipboard.writeText(window.location.href);
                        alert('✅ تم نسخ الرابط!');
                    }
                }
            </script>
        </body>
        </html>
    ''', post=post, comments=comments)

@app.route('/comment/<post_id>', methods=['POST'])
def add_comment(post_id):
    name = request.form.get('name', '').strip() or 'زائر'
    content = request.form.get('content', '').strip()
    
    if not content:
        return "التعليق مطلوب", 400
    
    post = db.posts.find_one({'_id': ObjectId(post_id)})
    if not post:
        return "التدوينة غير موجودة", 404
    
    comment = {
        'post_id': post_id,
        'name': name,
        'content': content,
        'date': datetime.utcnow()
    }
    db.comments.insert_one(comment)
    
    return redirect(url_for('view_post', post_id=post_id))

@app.route('/like/<post_id>', methods=['POST'])
def like_post(post_id):
    visitor_id = get_visitor_session()
    
    post = db.posts.find_one({'_id': ObjectId(post_id)})
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    existing_like = db.likes.find_one({'post_id': post_id, 'session_id': visitor_id})
    
    if existing_like:
        db.likes.delete_one({'_id': existing_like['_id']})
        db.posts.update_one({'_id': ObjectId(post_id)}, {'$inc': {'likes': -1}})
    else:
        like = {
            'post_id': post_id,
            'session_id': visitor_id
        }
        db.likes.insert_one(like)
        db.posts.update_one({'_id': ObjectId(post_id)}, {'$inc': {'likes': 1}})
    
    updated_post = db.posts.find_one({'_id': ObjectId(post_id)})
    return jsonify({'likes': updated_post.get('likes', 0)})

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('admin'):
        posts = list(db.posts.find().sort('date', -1))
        for p in posts:
            p['_id'] = str(p['_id'])
        
        total_posts = db.posts.count_documents({})
        total_comments = db.comments.count_documents({})
        total_visitors = get_total_visitors()
        online_visitors = get_online_visitors()
        
        total_likes = 0
        for p in db.posts.find():
            total_likes += p.get('likes', 0)
        
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
        if password == ADMIN_PASSWORD:
            session['admin'] = True
            session['login_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return redirect(url_for('admin'))
        else:
            return render_template_string(ADMIN_LOGIN_TEMPLATE, error='❌ كلمة السر غير صحيحة')
    
    return render_template_string(ADMIN_LOGIN_TEMPLATE, error=None)

# ======================
# إضافة تدوينة (مع رفع الصورة)
# ======================
@app.route('/add', methods=['POST'])
def add():
    if not session.get('admin'):
        return "غير مصرح لك", 403
    
    content = request.form.get('content', '').strip()
    category = request.form.get('category', 'general')
    
    if not content:
        return "المحتوى مطلوب", 400
    
    image_public_id = None
    image_url = None
    
    # معالجة الصورة
    if 'image' in request.files:
        file = request.files['image']
        print(f"📸 الملف المستلم: {file.filename if file else 'لا يوجد ملف'}")
        
        if file and file.filename:
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
            file_ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
            
            if file_ext in allowed_extensions:
                print(f"📤 جاري رفع الصورة: {file.filename}")
                upload_result = upload_image_to_cloudinary(file)
                
                if upload_result['success']:
                    image_public_id = upload_result['public_id']
                    image_url = upload_result['url']
                    print(f"✅ تم رفع الصورة بنجاح: {image_url}")
                else:
                    print(f"❌ فشل رفع الصورة: {upload_result.get('error')}")
            else:
                print(f"⚠️ نوع الملف غير مدعوم: {file_ext}")
    
    # إنشاء التدوينة
    post = {
        'content': content,
        'image_public_id': image_public_id,
        'image_url': image_url,
        'category': category,
        'date': datetime.utcnow(),
        'views': 0,
        'likes': 0
    }
    
    print(f"📝 بيانات التدوينة: {post}")
    db.posts.insert_one(post)
    print(f"✅ تم نشر التدوينة مع الصورة: {image_url if image_url else 'بدون صورة'}")
    
    return redirect(url_for('admin'))

@app.route('/delete/<post_id>', methods=['POST'])
def delete(post_id):
    if not session.get('admin'):
        return "غير مصرح لك", 403
    
    post = db.posts.find_one({'_id': ObjectId(post_id)})
    if post:
        if post.get('image_public_id'):
            delete_image_from_cloudinary(post['image_public_id'])
        
        db.posts.delete_one({'_id': ObjectId(post_id)})
        db.comments.delete_many({'post_id': post_id})
        db.likes.delete_many({'post_id': post_id})
    
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.pop('admin', None)
    session.pop('login_time', None)
    return redirect(url_for('index'))

# ======================
# اختبار عرض الصورة
# ======================
@app.route('/test-image/<post_id>')
def test_image(post_id):
    post = db.posts.find_one({'_id': ObjectId(post_id)})
    if not post:
        return "التدوينة غير موجودة", 404
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🧪 اختبار عرض الصورة</title>
        <style>
            body {{ font-family: 'Cairo', Arial, sans-serif; padding: 40px; background: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 16px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            img {{ max-width: 100%; border-radius: 12px; }}
            .info {{ background: #f8f9fa; padding: 15px; border-radius: 12px; margin: 15px 0; }}
            .success {{ color: green; }}
            .error {{ color: red; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🧪 اختبار عرض الصورة</h2>
            <div class="info">
                <p><strong>معرف التدوينة:</strong> {post_id}</p>
                <p><strong>المحتوى:</strong> {post.get('content', '')[:50]}...</p>
                <p><strong>رابط الصورة:</strong> {post.get('image_url', 'لا توجد صورة')}</p>
            </div>
            <hr>
            {"<img src='" + post['image_url'] + "' alt='الصورة'>" if post.get('image_url') else '<p class="error">❌ لا توجد صورة لهذه التدوينة</p>'}
            <br>
            <a href="/admin" style="color: #6c63ff;">↩️ العودة للوحة التحكم</a>
        </div>
    </body>
    </html>
    """

# ======================
# الصفحات الخاصة (تصفية حسب النوع)
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
    
    posts_cursor = db.posts.find({'category': category}).sort('date', -1).skip((page - 1) * per_page).limit(per_page)
    posts = [serialize_post(p) for p in posts_cursor]
    
    total_posts = db.posts.count_documents({'category': category})
    total_pages = (total_posts + per_page - 1) // per_page if total_posts > 0 else 1
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
                            {% if post.image_url %}
                                <img src="{{ post.image_url }}" alt="صورة التدوينة">
                            {% endif %}
                            <div class="post-meta">
                                <div class="post-stats">
                                    <span><i class="bi bi-eye"></i> {{ post.views }}</span>
                                    <span><i class="bi bi-heart"></i> {{ post.likes }}</span>
                                    <span><i class="bi bi-chat"></i> {{ post.comments|length }}</span>
                                </div>
                                <span class="post-date"><i class="bi bi-clock"></i> {{ post.date.strftime('%Y-%m-%d %H:%M') }}</span>
                            </div>
                            <a href="/post/{{ post._id }}" class="read-more">اقرأ المزيد →</a>
                        </div>
                    {% endfor %}
                    
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
        </body>
        </html>
    ''', posts=posts, total_pages=total_pages, current_page=current_page, 
    title=title, subtitle=subtitle, icon=icon, color=color,
    get_category_label=get_category_label)

# ======================
# تشغيل التطبيق
# ======================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=DEBUG)
