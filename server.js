const express = require('express');
const bodyParser = require('body-parser');
const path = require('path');
const app = express();

app.use(bodyParser.urlencoded({ extended: true }));
app.set('view engine', 'ejs');
app.set('views', __dirname); // لجعل النظام يقرأ القوالب من المجلد الرئيسي مباشرة

// قاعدة بيانات وهمية (ستُمسح عند إعادة تشغيل السيرفر في Render)
// للمشاريع الحقيقية يفضل ربطها بـ MongoDB
let accounts = [
    { id: 1, title: "حساب خرافي - 5 نجوم", price: "50", players: "Messi, Ronaldo", stars: "5", img: "https://via.placeholder.com/300x150", featured: true },
    { id: 2, title: "حساب متميز - تشكيلة كاملة", price: "30", players: "Neymar, Mbappe", stars: "4", img: "https://via.placeholder.com/300x150", featured: false }
];

// الصفحة الرئيسية
app.get('/', (req, res) => {
    res.render('index', { accounts: accounts });
});

// صفحة لوحة التحكم (بسيطة جداً للبدء)
app.get('/admin-panel', (req, res) => {
    res.render('admin', { accounts: accounts });
});

// إضافة حساب جديد
app.post('/add-account', (req, res) => {
    const newAcc = {
        id: Date.now(),
        title: req.body.title,
        price: req.body.price,
        players: req.body.players,
        stars: req.body.stars,
        img: req.body.img || "https://via.placeholder.com/300x150",
        featured: req.body.featured === 'on'
    };
    accounts.push(newAcc);
    res.redirect('/admin-panel');
});

// حذف حساب
app.get('/delete/:id', (req, res) => {
    accounts = accounts.filter(acc => acc.id != req.params.id);
    res.redirect('/admin-panel');
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});
