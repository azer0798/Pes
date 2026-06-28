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
# دوال مساعدة للصور
# ======================

def upload_image_to_cloudinary(file):
    try:
        if not file or not file.filename:
            return {'success': False, 'error': 'لا يوجد ملف'}

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

        return {
            'public_id': upload_result.get('public_id'),
            'url': upload_result.get('secure_url'),
            'success': True
        }
    except Exception as e:
        print(f"❌ خطأ في رفع الصورة: {str(e)}")
        return {'success': False, 'error': str(e)}

def delete_image_from_cloudinary(public_id):
    try:
        if public_id:
            cloudinary.uploader.destroy(public_id)
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

def get_post_with_comments(post):
    """جلب التدوينة مع تعليقاتها"""
    post = serialize_post(post)
    comments = list(db.comments.find({'post_id': post['_id']}).sort('date', -1))
    for c in comments:
        c['_id'] = str(c['_id'])
    post['comments'] = comments
    return post

def get_comments_tree(post_id, parent_id=None):
    """جلب التعليقات بشكل متداخل (مثل فيسبوك)"""
    query = {'post_id': post_id}
    if parent_id:
        query['parent_id'] = parent_id
    else:
        query['parent_id'] = None
    
    comments = list(db.comments.find(query).sort('date', 1))
    for comment in comments:
        comment['_id'] = str(comment['_id'])
        comment['replies'] = get_comments_tree(post_id, str(comment['_id']))
        comment['likes_count'] = db.comment_likes.count_documents({'comment_id': str(comment['_id'])})
        comment['user_liked'] = db.comment_likes.find_one({
            'comment_id': str(comment['_id']),
            'session_id': get_visitor_session()
        }) is not None
    return comments

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
    posts = []
    for p in posts_cursor:
        posts.append(get_post_with_comments(p))
    
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
    
    # جلب التعليقات المتداخلة
    comments = get_comments_tree(post_id)
    
    # التحقق من إعجاب المستخدم بالتدوينة
    user_liked = db.likes.find_one({
        'post_id': post_id,
        'session_id': get_visitor_session()
    }) is not None
    
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
            <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap" rel="stylesheet">
            <title>التدوينة - مدونتي</title>
            <style>
                * { font-family: 'Cairo', sans-serif; }
                body { background: #f0f2f5; padding: 30px 20px; }
                .container { max-width: 750px; margin: 0 auto; }
                
                .post-card { background: white; border-radius: 12px; padding: 25px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
                .post-card img { max-width: 100%; border-radius: 12px; margin: 15px 0; }
                
                .post-actions { display: flex; gap: 20px; padding: 10px 0; border-top: 1px solid #e4e6eb; margin-top: 15px; }
                .post-actions button { background: none; border: none; padding: 8px 15px; border-radius: 8px; font-weight: 600; color: #65676b; transition: all 0.2s; display: flex; align-items: center; gap: 8px; }
                .post-actions button:hover { background: #f0f2f5; }
                .post-actions .liked { color: #1877f2; }
                .post-actions .liked i { color: #1877f2; }
                
                .reaction-bar { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid #e4e6eb; margin-bottom: 10px; }
                .reaction-bar .likes-count { font-weight: 600; color: #65676b; font-size: 0.9rem; }
                
                .comments-section { margin-top: 25px; }
                .comments-section h5 { color: #1a1a1a; font-weight: 700; margin-bottom: 15px; }
                
                .comment-input { display: flex; gap: 10px; margin-bottom: 20px; }
                .comment-input textarea { flex: 1; border-radius: 20px; border: 1px solid #e4e6eb; padding: 12px 15px; resize: none; font-size: 0.95rem; background: #f0f2f5; transition: all 0.3s; }
                .comment-input textarea:focus { background: white; border-color: #1877f2; outline: none; box-shadow: 0 0 0 2px rgba(24,119,242,0.2); }
                .comment-input button { background: #1877f2; color: white; border: none; border-radius: 20px; padding: 0 20px; font-weight: 600; transition: all 0.3s; }
                .comment-input button:hover { background: #166fe5; transform: scale(1.02); }
                
                .comment { display: flex; gap: 12px; margin-bottom: 15px; padding: 12px; border-radius: 12px; transition: all 0.2s; }
                .comment:hover { background: #f8f9fa; }
                .comment-avatar { width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #667eea, #764ba2); display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; flex-shrink: 0; }
                .comment-body { flex: 1; }
                .comment-name { font-weight: 600; color: #1a1a1a; font-size: 0.95rem; }
                .comment-name span { font-weight: 400; color: #65676b; font-size: 0.8rem; margin-right: 8px; }
                .comment-text { color: #1a1a1a; margin: 5px 0; }
                .comment-actions { display: flex; gap: 15px; margin-top: 5px; }
                .comment-actions button { background: none; border: none; color: #65676b; font-size: 0.8rem; font-weight: 600; padding: 2px 8px; border-radius: 4px; transition: all 0.2s; }
                .comment-actions button:hover { background: #e4e6eb; }
                .comment-actions .liked { color: #1877f2; }
                
                .comment-replies { margin-right: 52px; padding-right: 15px; border-right: 2px solid #e4e6eb; }
                .comment-reply-input { display: flex; gap: 10px; margin: 10px 0; }
                .comment-reply-input textarea { flex: 1; border-radius: 20px; border: 1px solid #e4e6eb; padding: 8px 15px; resize: none; font-size: 0.9rem; background: #f0f2f5; }
                .comment-reply-input textarea:focus { background: white; border-color: #1877f2; outline: none; }
                .comment-reply-input button { background: #1877f2; color: white; border: none; border-radius: 20px; padding: 0 15px; font-weight: 600; font-size: 0.85rem; }
                
                .back-btn { display: inline-block; margin-top: 15px; padding: 8px 20px; background: #1877f2; color: white; border-radius: 8px; text-decoration: none; font-weight: 600; transition: all 0.3s; }
                .back-btn:hover { background: #166fe5; color: white; }
                
                .share-dropdown { position: relative; display: inline-block; }
                .share-menu { display: none; position: absolute; background: white; box-shadow: 0 8px 25px rgba(0,0,0,0.15); border-radius: 12px; padding: 8px; min-width: 200px; z-index: 1000; top: 100%; left: 0; }
                .share-menu.show { display: block; }
                .share-menu a { display: flex; align-items: center; gap: 10px; padding: 8px 15px; border-radius: 8px; color: #1a1a1a; text-decoration: none; transition: all 0.2s; }
                .share-menu a:hover { background: #f0f2f5; }
                
                @media (max-width: 576px) {
                    .post-card { padding: 20px; }
                    .comment-replies { margin-right: 20px; padding-right: 10px; }
                    .post-actions { flex-wrap: wrap; }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="post-card">
                    <h4 class="mb-2">{{ post.content[:50] }}...</h4>
                    <div style="color: #65676b; font-size: 0.9rem; margin-bottom: 10px;">
                        <span><i class="bi bi-clock"></i> {{ post.date.strftime('%Y-%m-%d %H:%M') }}</span>
                    </div>
                    
                    {% if post.image_url %}
                        <img src="{{ post.image_url }}" alt="صورة التدوينة">
                    {% endif %}
                    
                    <div class="post-content" style="font-size: 1.05rem; line-height: 1.8; color: #1a1a1a;">
                        {{ post.content }}
                    </div>
                    
                    <div class="reaction-bar">
                        <span class="likes-count" id="like-count-display"><i class="bi bi-hand-thumbs-up-fill" style="color: #1877f2;"></i> {{ post.likes }}</span>
                        <span style="color: #65676b; font-size: 0.9rem;"><i class="bi bi-chat"></i> {{ comments|length }}</span>
                    </div>
                    
                    <div class="post-actions">
                        <button class="{% if user_liked %}liked{% endif %}" onclick="toggleLike('{{ post._id }}')" id="like-btn">
                            <i class="bi {% if user_liked %}bi-hand-thumbs-up-fill{% else %}bi-hand-thumbs-up{% endif %}"></i>
                            <span id="like-text">{% if user_liked %}أعجبني{% else %}أعجبني{% endif %}</span>
                        </button>
                        
                        <button onclick="document.getElementById('comment-input').focus()">
                            <i class="bi bi-chat"></i> تعليق
                        </button>
                        
                        <div class="share-dropdown">
                            <button onclick="toggleShareMenu()">
                                <i class="bi bi-share"></i> مشاركة
                            </button>
                            <div class="share-menu" id="share-menu">
                                <a href="#" onclick="sharePost('facebook')"><i class="bi bi-facebook" style="color: #1877f2;"></i> فيسبوك</a>
                                <a href="#" onclick="sharePost('twitter')"><i class="bi bi-twitter-x" style="color: #000;"></i> تويتر</a>
                                <a href="#" onclick="sharePost('whatsapp')"><i class="bi bi-whatsapp" style="color: #25D366;"></i> واتساب</a>
                                <a href="#" onclick="sharePost('copy')"><i class="bi bi-link-45deg" style="color: #65676b;"></i> نسخ الرابط</a>
                            </div>
                        </div>
                    </div>
                    
                    <a href="/" class="back-btn"><i class="bi bi-arrow-right"></i> العودة للرئيسية</a>
                </div>
                
                <div class="comments-section">
                    <h5><i class="bi bi-chat-dots"></i> التعليقات ({{ comments|length }})</h5>
                    
                    <div class="comment-input">
                        <textarea id="comment-input" placeholder="اكتب تعليقاً..." rows="1"></textarea>
                        <button onclick="addComment('{{ post._id }}')">نشر</button>
                    </div>
                    
                    <div id="comments-container">
                        {% for comment in comments %}
                            {{ render_comment(comment, post._id)|safe }}
                        {% endfor %}
                    </div>
                </div>
            </div>
            
            <script>
                function toggleLike(postId) {
                    fetch('/like/' + postId, { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            const btn = document.getElementById('like-btn');
                            const countDisplay = document.getElementById('like-count-display');
                            const text = document.getElementById('like-text');
                            
                            if (data.liked) {
                                btn.classList.add('liked');
                                btn.querySelector('i').className = 'bi bi-hand-thumbs-up-fill';
                                text.textContent = 'أعجبني';
                            } else {
                                btn.classList.remove('liked');
                                btn.querySelector('i').className = 'bi bi-hand-thumbs-up';
                                text.textContent = 'أعجبني';
                            }
                            
                            countDisplay.innerHTML = '<i class="bi bi-hand-thumbs-up-fill" style="color: #1877f2;"></i> ' + data.likes;
                        });
                }
                
                function addComment(postId, parentId = null) {
                    const input = parentId ? 
                        document.getElementById('reply-input-' + parentId) : 
                        document.getElementById('comment-input');
                    
                    const content = input.value.trim();
                    if (!content) return;
                    
                    fetch('/comment/' + postId, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ content: content, parent_id: parentId })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            input.value = '';
                            loadComments(postId);
                        }
                    });
                }
                
                function loadComments(postId) {
                    fetch('/get-comments/' + postId)
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('comments-container').innerHTML = data.html;
                        });
                }
                
                function toggleReply(commentId) {
                    const replyForm = document.getElementById('reply-form-' + commentId);
                    if (replyForm.style.display === 'none') {
                        replyForm.style.display = 'block';
                    } else {
                        replyForm.style.display = 'none';
                    }
                }
                
                function likeComment(commentId) {
                    fetch('/like-comment/' + commentId, { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            const btn = document.getElementById('comment-like-' + commentId);
                            const count = document.getElementById('comment-like-count-' + commentId);
                            if (data.liked) {
                                btn.classList.add('liked');
                            } else {
                                btn.classList.remove('liked');
                            }
                            count.textContent = data.likes;
                        });
                }
                
                function toggleShareMenu() {
                    document.getElementById('share-menu').classList.toggle('show');
                }
                
                function sharePost(platform) {
                    const url = window.location.href;
                    const title = '{{ post.content[:50] }}';
                    let shareUrl = '';
                    
                    switch(platform) {
                        case 'facebook':
                            shareUrl = 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(url);
                            break;
                        case 'twitter':
                            shareUrl = 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(title) + '&url=' + encodeURIComponent(url);
                            break;
                        case 'whatsapp':
                            shareUrl = 'https://api.whatsapp.com/send?text=' + encodeURIComponent(title + ' ' + url);
                            break;
                        case 'copy':
                            navigator.clipboard.writeText(url);
                            alert('✅ تم نسخ الرابط!');
                            return;
                    }
                    
                    if (shareUrl) {
                        window.open(shareUrl, '_blank');
                    }
                    
                    document.getElementById('share-menu').classList.remove('show');
                }
                
                document.addEventListener('click', function(e) {
                    if (!e.target.closest('.share-dropdown')) {
                        document.getElementById('share-menu').classList.remove('show');
                    }
                });
                
                document.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        const target = e.target;
                        if (target.id === 'comment-input' || target.id.startsWith('reply-input-')) {
                            e.preventDefault();
                            const postId = '{{ post._id }}';
                            const parentId = target.id.startsWith('reply-input-') ? target.id.replace('reply-input-', '') : null;
                            addComment(postId, parentId);
                        }
                    }
                });
            </script>
        </body>
        </html>
    ''', post=post, comments=comments, user_liked=user_liked, render_comment=render_comment)

# ======================
# دالة عرض التعليقات المتداخلة
# ======================

def render_comment(comment, post_id, depth=0):
    """عرض تعليق مع ردوده (مثل فيسبوك)"""
    indent = depth * 20
    max_depth = 5
    
    html = f'''
    <div class="comment" style="margin-right: {indent}px;" id="comment-{comment['_id']}">
        <div class="comment-avatar">{comment['name'][0]}</div>
        <div class="comment-body">
            <div class="comment-name">{comment['name']} <span>{comment['date'].strftime('%Y-%m-%d %H:%M')}</span></div>
            <div class="comment-text">{comment['content']}</div>
            <div class="comment-actions">
                <button onclick="likeComment('{comment['_id']}')" id="comment-like-{comment['_id']}" class="{'liked' if comment.get('user_liked') else ''}">
                    <i class="bi bi-hand-thumbs-up"></i> <span id="comment-like-count-{comment['_id']}">{comment.get('likes_count', 0)}</span>
                </button>
                <button onclick="toggleReply('{comment['_id']}')">رد</button>
            </div>
            
            <div class="comment-reply-input" id="reply-form-{comment['_id']}" style="display: none;">
                <textarea id="reply-input-{comment['_id']}" placeholder="اكتب رداً..." rows="1"></textarea>
                <button onclick="addComment('{post_id}', '{comment['_id']}')">نشر</button>
            </div>
        </div>
    </div>
    '''
    
    if comment.get('replies') and depth < max_depth:
        html += '<div class="comment-replies">'
        for reply in comment['replies']:
            html += render_comment(reply, post_id, depth + 1)
        html += '</div>'
    
    return html

# ======================
# API التعليقات (للـ AJAX)
# ======================

@app.route('/comment/<post_id>', methods=['POST'])
def add_comment_api(post_id):
    data = request.get_json()
    content = data.get('content', '').strip()
    parent_id = data.get('parent_id')
    
    if not content:
        return jsonify({'success': False, 'error': 'التعليق مطلوب'}), 400
    
    post = db.posts.find_one({'_id': ObjectId(post_id)})
    if not post:
        return jsonify({'success': False, 'error': 'التدوينة غير موجودة'}), 404
    
    name = request.headers.get('X-Forwarded-For', 'زائر').split(',')[0].strip()
    if name == 'زائر':
        name = 'زائر_' + str(uuid.uuid4())[:6]
    
    comment = {
        'post_id': post_id,
        'parent_id': parent_id,
        'name': name,
        'content': content,
        'date': datetime.utcnow()
    }
    result = db.comments.insert_one(comment)
    
    return jsonify({
        'success': True,
        'comment_id': str(result.inserted_id)
    })

@app.route('/get-comments/<post_id>')
def get_comments_api(post_id):
    comments = get_comments_tree(post_id)
    html = ''
    for comment in comments:
        html += render_comment(comment, post_id)
    return jsonify({'html': html})

@app.route('/like-comment/<comment_id>', methods=['POST'])
def like_comment(comment_id):
    session_id = get_visitor_session()
    
    existing_like = db.comment_likes.find_one({
        'comment_id': comment_id,
        'session_id': session_id
    })
    
    if existing_like:
        db.comment_likes.delete_one({'_id': existing_like['_id']})
        liked = False
    else:
        db.comment_likes.insert_one({
            'comment_id': comment_id,
            'session_id': session_id
        })
        liked = True
    
    likes_count = db.comment_likes.count_documents({'comment_id': comment_id})
    
    return jsonify({
        'likes': likes_count,
        'liked': liked
    })

# ======================
# الإعجاب بالتدوينة (API)
# ======================

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
        liked = False
    else:
        like = {'post_id': post_id, 'session_id': visitor_id}
        db.likes.insert_one(like)
        db.posts.update_one({'_id': ObjectId(post_id)}, {'$inc': {'likes': 1}})
        liked = True
    
    updated_post = db.posts.find_one({'_id': ObjectId(post_id)})
    return jsonify({
        'likes': updated_post.get('likes', 0),
        'liked': liked
    })

# ======================
# لوحة التحكم
# ======================

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
    
    image_public_id = None
    image_url = None
    
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename:
            upload_result = upload_image_to_cloudinary(file)
            if upload_result['success']:
                image_public_id = upload_result['public_id']
                image_url = upload_result['url']
    
    post = {
        'content': content,
        'image_public_id': image_public_id,
        'image_url': image_url,
        'category': category,
        'date': datetime.utcnow(),
        'views': 0,
        'likes': 0
    }
    db.posts.insert_one(post)
    
    return redirect(url_for('admin'))

# ======================
# حذف تدوينة
# ======================

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
    posts = []
    for p in posts_cursor:
        posts.append(get_post_with_comments(p))
    
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
                body { background: #f0f2f5; padding: 40px 20px; }
                .container { max-width: 750px; margin: 0 auto; }
                .page-header { text-align: center; padding-bottom: 30px; border-bottom: 1px solid #e9ecef; margin-bottom: 30px; background: white; border-radius: 12px; padding: 25px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
                .page-header h1 { font-size: 2.2rem; font-weight: 700; color: #2d3436; }
                .page-header h1 i { color: {{ color }}; }
                .page-header p { color: #868e96; }
                .back-btn { display: inline-block; margin-top: 15px; padding: 8px 25px; background: #6c63ff; color: white; border-radius: 30px; text-decoration: none; transition: all 0.3s; }
                .back-btn:hover { background: #5a52d5; color: white; transform: translateY(-2px); }
                .post-card { background: white; border-radius: 12px; padding: 25px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border-right: 4px solid {{ color }}; transition: all 0.3s; }
                .post-card:hover { box-shadow: 0 8px 30px rgba(0,0,0,0.06); transform: translateY(-2px); }
                .post-card img { max-width: 100%; border-radius: 12px; margin-top: 15px; max-height: 300px; object-fit: cover; }
                .post-content { font-size: 1.05rem; line-height: 1.8; color: #1a1a1a; }
                .post-meta { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-top: 15px; padding-top: 12px; border-top: 1px solid #e4e6eb; gap: 10px; }
                .post-stats { display: flex; gap: 15px; color: #65676b; font-size: 0.85rem; }
                .post-date { color: #868e96; font-size: 0.85rem; }
                .post-category-badge { display: inline-block; padding: 2px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; margin-bottom: 10px; background: {{ color }}20; color: {{ color }}; border: 1px solid {{ color }}40; }
                .comments-preview { margin-top: 12px; padding-top: 12px; border-top: 1px solid #e4e6eb; }
                .comment-preview { display: flex; gap: 10px; padding: 8px 0; align-items: flex-start; }
                .comment-preview-avatar { width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(135deg, #667eea, #764ba2); display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 0.8rem; flex-shrink: 0; }
                .comment-preview-body { flex: 1; }
                .comment-preview-name { font-weight: 600; color: #1a1a1a; font-size: 0.85rem; }
                .comment-preview-text { color: #1a1a1a; font-size: 0.9rem; line-height: 1.5; }
                .view-all-comments { color: #1877f2; font-weight: 600; font-size: 0.9rem; text-decoration: none; display: inline-block; margin-top: 5px; cursor: pointer; }
                .view-all-comments:hover { text-decoration: underline; }
                .no-comments { color: #65676b; font-size: 0.85rem; padding: 5px 0; }
                .empty-state { text-align: center; padding: 60px 20px; background: white; border-radius: 16px; border: 2px dashed #dee2e6; }
                .empty-state i { font-size: 3.5rem; color: #dee2e6; }
                .pagination { display: flex; justify-content: center; gap: 8px; margin-top: 30px; }
                .pagination a { padding: 8px 16px; border: 1px solid #e9ecef; border-radius: 8px; text-decoration: none; color: #6c63ff; transition: all 0.3s; background: white; }
                .pagination a:hover { background: #6c63ff; color: white; }
                .pagination .active { background: #6c63ff; color: white; }
                .pagination .disabled { color: #ccc; pointer-events: none; }
                .read-more { color: #1877f2; text-decoration: none; font-weight: 600; }
                .read-more:hover { text-decoration: underline; }
                .footer { text-align: center; margin-top: 40px; color: #b2bec3; font-size: 0.8rem; }
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
                                    <span><i class="bi bi-hand-thumbs-up-fill" style="color: #1877f2;"></i> {{ post.likes }}</span>
                                    <span><i class="bi bi-chat"></i> {{ post.comments|length }}</span>
                                    <span><i class="bi bi-eye"></i> {{ post.views }}</span>
                                </div>
                                <span class="post-date"><i class="bi bi-clock"></i> {{ post.date.strftime('%Y-%m-%d %H:%M') }}</span>
                            </div>
                            
                            <div class="comments-preview">
                                {% if post.comments %}
                                    {% set comment_count = post.comments|length %}
                                    {% set preview_comments = post.comments[:3] %}
                                    {% for comment in preview_comments %}
                                        <div class="comment-preview">
                                            <div class="comment-preview-avatar">{{ comment.name[0] }}</div>
                                            <div class="comment-preview-body">
                                                <div class="comment-preview-name">{{ comment.name }}</div>
                                                <div class="comment-preview-text">
                                                    {{ comment.content[:60] }}{% if comment.content|length > 60 %}...{% endif %}
                                                </div>
                                            </div>
                                        </div>
                                    {% endfor %}
                                    {% if comment_count > 3 %}
                                        <a href="/post/{{ post._id }}" class="view-all-comments">
                                            عرض جميع التعليقات ({{ comment_count }})
                                        </a>
                                    {% endif %}
                                {% else %}
                                    <div class="no-comments"><i class="bi bi-chat"></i> لا توجد تعليقات</div>
                                {% endif %}
                            </div>
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
