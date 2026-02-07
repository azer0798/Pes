const express = require('express');
const bodyParser = require('body-parser');
const session = require('express-session');
const path = require('path');

const app = express();

// إعدادات الجلسة (Session) للامان
app.use(session({
    secret: 'pes_secret_key_2024',
    resave: false,
    saveUninitialized: true
}));

app.use(bodyParser.urlencoded({ extended: true }));
app.set('view engine', 'ejs');
app.set('views', __dirname);

// قاعدة بيانات وهمية محسنة
let accounts = [
    { id: 101, title: "تشكيلة أساطير كاملة", price: "120", stars: "5", players: "Epic Rummenigge, Big Time Messi", img: "https://via.placeholder.com/400x200", featured: true, category: "Premium" },
    { id: 102, title: "حساب كوينز عالي", price: "45", stars: "4", players: "Neymar, Mbappe", img: "https://via.placeholder.com/400x200", featured: false, category: "Starter" }
];

const ADMIN_CREDENTIALS = { user: "admin", pass: "pes2024" };

// الصفحة الرئيسية
app.get('/', (req, res) => {
    res.render('index', { accounts: accounts });
});

// لوحة التحكم - تسجيل الدخول
app.get('/login', (req, res) => res.render('login'));

app.post('/login', (req, res) => {
    const { username, password } = req.body;
    if (username === ADMIN_CREDENTIALS.user && password === ADMIN_CREDENTIALS.pass) {
        req.session.isAdmin = true;
        res.redirect('/admin-panel');
    } else {
        res.send("خطأ في البيانات! <a href='/login'>حاول مجدداً</a>");
    }
});

// لوحة التحكم (محمية)
app.get('/admin-panel', (req, res) => {
    if (!req.session.isAdmin) return res.redirect('/login');
    res.render('admin', { accounts: accounts });
});

// إضافة حساب
app.post('/add-account', (req, res) => {
    if (!req.session.isAdmin) return res.status(403).send("Forbidden");
    const newAcc = {
        id: Math.floor(1000 + Math.random() * 9000), // رقم طلب عشوائي
        ...req.body,
        featured: req.body.featured === 'on'
    };
    accounts.push(newAcc);
    res.redirect('/admin-panel');
});

// حذف
app.get('/delete/:id', (req, res) => {
    if (!req.session.isAdmin) return res.status(403).send("Forbidden");
    accounts = accounts.filter(acc => acc.id != req.params.id);
    res.redirect('/admin-panel');
});

// تسجيل الخروج
app.get('/logout', (req, res) => {
    req.session.destroy();
    res.redirect('/');
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on http://localhost:${PORT}`));
