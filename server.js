const express = require('express');
const bodyParser = require('body-parser');
const path = require('path');

const app = express();

// --- الإعدادات (Settings) ---
app.use(bodyParser.urlencoded({ extended: true }));
app.set('view engine', 'ejs');
app.set('views', __dirname);
app.use(express.static(path.join(__dirname, 'public'))); // لتشغيل ملفات CSS أو الصور لاحقاً

// --- قاعدة البيانات (مؤقتة في الذاكرة) ---
// ملاحظة: عند إعادة تشغيل السيرفر في Render، ستعود البيانات لهذه القيم الافتراضية
let accounts = [
    { 
        id: 1, 
        title: "حساب خرافي - 5 نجوم", 
        price: "50", 
        players: "Messi, Ronaldo", 
        stars: "5", 
        img: "https://via.placeholder.com/300x150", 
        featured: true 
    },
    { 
        id: 2, 
        title: "حساب متميز - تشكيلة كاملة", 
        price: "30", 
        players: "Neymar, Mbappe", 
        stars: "4", 
        img: "https://via.placeholder.com/300x150", 
        featured: false 
    }
];

// كلمة مرور بسيطة لحماية لوحة التحكم (يمكنك تغييرها)
const ADMIN_PASSWORD = "admin123";

// --- Middleware للحماية ---
const checkAuth = (req, res, next) => {
    // نتحقق من وجود كلمة المرور في الرابط كحل سريع وبسيط
    // مثال: /admin-panel?pass=admin123
    if (req.query.pass === ADMIN_PASSWORD) {
        next();
    } else {
        res.status(403).send('<h2>عذراً، الوصول غير مصرح به.</h2><p>يجب إضافة كلمة المرور الصحيحة للرابط.</p>');
    }
};

// --- المسارات (Routes) ---

// 1. الصفحة الرئيسية للمستخدمين
app.get('/', (req, res) => {
    res.render('index', { accounts: accounts });
});

// 2. صفحة لوحة التحكم (محمية)
app.get('/admin-panel', checkAuth, (req, res) => {
    res.render('admin', { 
        accounts: accounts, 
        pass: req.query.pass // نمرر الباسورد ليبقى في الروابط داخل الصفحة
    });
});

// 3. إضافة حساب جديد
app.post('/add-account', (req, res) => {
    const { title, price, players, stars, img, featured, adminPass } = req.body;
    
    const newAcc = {
        id: Date.now(),
        title: title,
        price: price,
        players: players || "غير محدد",
        stars: stars || "0",
        img: img || "https://via.placeholder.com/300x150",
        featured: featured === 'on'
    };

    accounts.push(newAcc);
    // نعود للوحة التحكم مع الحفاظ على كلمة المرور في الرابط
    res.redirect(`/admin-panel?pass=${adminPass || ADMIN_PASSWORD}`);
});

// 4. حذف حساب
app.get('/delete/:id', (req, res) => {
    const pass = req.query.pass;
    if (pass === ADMIN_PASSWORD) {
        accounts = accounts.filter(acc => acc.id != req.params.id);
        res.redirect(`/admin-panel?pass=${pass}`);
    } else {
        res.status(403).send('غير مصرح بالحذف');
    }
});

// --- تشغيل السيرفر ---
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`-----------------------------------`);
    console.log(`✅ Server is running on port ${PORT}`);
    console.log(`🔗 Main site: http://localhost:${PORT}`);
    console.log(`⚙️ Admin panel: http://localhost:${PORT}/admin-panel?pass=${ADMIN_PASSWORD}`);
    console.log(`-----------------------------------`);
});
