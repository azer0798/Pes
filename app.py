from flask import Flask, render_template_string, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your_strong_secret_key' # غيره لمفتاح سري
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
db = SQLAlchemy(app)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context(): db.create_all()

@app.route('/')
def index():
    posts = Post.query.order_by(Post.date.desc()).all()
    return render_template_string(open('index.html', encoding='utf-8').read(), posts=posts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['password'] == '1234': # كلمة المرور هنا
            session['admin'] = True
            return redirect(url_for('index'))
    return render_template_string('<form method="POST">كلمة السر: <input type="password" name="password"><button>دخول</button></form>')

@app.route('/add', methods=['POST'])
def add():
    if not session.get('admin'): return "غير مصرح لك", 403
    db.session.add(Post(content=request.form['content']))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    if not session.get('admin'): return "غير مصرح لك", 403
    db.session.delete(Post.query.get(id))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

if __name__ == '__main__': app.run(debug=True)
