const express = require('express');
const bodyParser = require('body-parser');
const session = require('express-session');
const path = require('path');
const multer = require('multer');
const fs = require('fs');

const app = express();

// إعداد رفع الصور
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

app.use(session({
    secret: 'pes_2026_secret',
    resave: false,
    saveUninitialized: true
}));
app.use(bodyParser.urlencoded({ extended: true }));
app.set('view engine', 'ejs');
app.set('views', __dirname);
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

let accounts = []; 

const ADMIN_USER = "admin";
const ADMIN_PASS = "pes2026";

// المسارات
app.get('/', (req, res) => res.render('index', { accounts: accounts }));
app.get('/login', (req, res) => res.render('login'));
app.post('/login', (req, res) => {
    if (req.body.username === ADMIN_USER && req.body.password === ADMIN_PASS) {
        req.session.isAdmin = true;
        res.redirect('/admin-panel');
    } else {
        res.send("<script>alert('خطأ!'); window.location='/login';</script>");
    }
});

app.get('/admin-panel', (req, res) => {
    if (!req.session.isAdmin) return res.redirect('/login');
    res.render('admin', { accounts: accounts });
});

app.post('/add-account', upload.single('imageFile'), (req, res) => {
    if (!req.session.isAdmin) return res.status(403).send("Unauthorized");
    const newAcc = {
        id: Math.floor(1000 + Math.random() * 9000),
        title: req.body.title,
        price: parseFloat(req.body.price),
        players: req.body.players,
        featured: req.body.featured === 'on',
        img: req.file ? '/uploads/' + req.file.filename : 'https://via.placeholder.com/400x200'
    };
    accounts.push(newAcc);
    res.redirect('/admin-panel');
});

app.get('/delete/:id', (req, res) => {
    if (!req.session.isAdmin) return res.status(403).send("Unauthorized");
    accounts = accounts.filter(acc => acc.id != req.params.id);
    res.redirect('/admin-panel');
});

app.get('/logout', (req, res) => {
    req.session.destroy();
    res.redirect('/');
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server: http://localhost:${PORT}`));
