const express = require('express');
const bodyParser = require('body-parser');
const session = require('express-session');
const path = require('path');
const multer = require('multer');
const fs = require('fs');

const app = express();

// --- إعداد رفع الصور ---
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        const dir = './uploads';
        if (!fs.existsSync(dir)) fs.mkdirSync(dir);
        cb(null, dir);
    },
    filename: (req, file, cb) => {
        cb(null, Date.now() + '-' + file.originalname);
    }
});
const upload = multer({ storage: storage });

// --- الإعدادات العامة ---
app.use(session({
    secret: 'pes_super_secret_2026',
    resave: false,
    saveUninitialized: true
}));
app.use(bodyParser.urlencoded({ extended: true }));
app.set('view engine', 'ejs');
app.set('views', __dirname);
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

// قاعدة بيانات وهمية (يتم تصفيرها عند إعادة تشغيل السيرفر)
let accounts = [];

// بيانات الدخول للوحة التحكم
const ADMIN_USER = "admin";
const ADMIN_PASS = "pes2026";

// --- المسارات (Routes) ---

// 1. الصفحة الرئيسية
app.get('/', (req, res) => {
    res.render('index', { accounts: accounts });
});

// 2. تسجيل الدخول
app.get('/login', (req, res) => res.render('login'));
app.post('/login', (req, res) => {
    const { username, password } = req.body;
    if (username === ADMIN_USER && password === ADMIN_PASS) {
        req.session.isAdmin = true;
        res.redirect('/admin-panel');
    } else {
        res.send("<script>alert('خطأ في البيانات'); window.location='/login';</script>");
    }
});

// 3. لوحة التحكم (محمية)
app.get('/admin-panel', (req, res) => {
    if (!req.session.isAdmin) return res.redirect('/login');
    res.render('admin', { accounts: accounts });
});

// 4. إضافة حساب جديد مع صورة
app.post('/add-account', upload.single('imageFile'), (req, res) => {
    if (!req.session.isAdmin) return res.status(403).send("Unauthorized");
    
    const newAcc = {
        id: Math.floor(1000 + Math.random() * 9000),
        title: req.body.title,
        price: req.body.price,
        players: req.body.players,
        stars: req.body.stars,
        featured: req.body.featured === 'on',
        img: req.file ? '/uploads/' + req.file.filename : 'https://via.placeholder.com/400x200'
    };
    
    accounts.push(newAcc);
    res.redirect('/admin-panel');
});

// 5. حذف حساب
app.get('/delete/:id', (req, res) => {
    if (!req.session.isAdmin) return res.status(403).send("Unauthorized");
    accounts = accounts.filter(acc => acc.id != req.params.id);
    res.redirect('/admin-panel');
});

// 6. تسجيل الخروج
app.get('/logout', (req, res) => {
    req.session.destroy();
    res.redirect('/');
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server started on http://localhost:${PORT}`));
