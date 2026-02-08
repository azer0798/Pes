const express = require('express');
const bodyParser = require('body-parser');
const session = require('express-session');
const path = require('path');
const multer = require('multer');
const fs = require('fs');

const app = express();

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
    secret: 'wassitdz_2026_web',
    resave: false,
    saveUninitialized: true
}));

app.use(bodyParser.urlencoded({ extended: true }));
app.set('view engine', 'ejs');
app.set('views', __dirname);
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

let accounts = []; 
let siteSettings = {
    supportLink: "https://t.me/zedx07",
    mediationLink: "https://t.me/zedx07",
    sellAccountLink: "https://t.me/zedx07",
    announcement: "مرحباً بكم في WassitDZ Game - نشتري ونبيع حسابات eFootball بأفضل الأسعار!"
};

const ADMIN_USER = "admin";
const ADMIN_PASS = "pes2026";

app.get('/', (req, res) => {
    res.render('index', { accounts: accounts, settings: siteSettings });
});

app.get('/login', (req, res) => res.render('login'));

app.post('/login', (req, res) => {
    if (req.body.username === ADMIN_USER && req.body.password === ADMIN_PASS) {
        req.session.isAdmin = true;
        res.redirect('/admin-panel');
    } else {
        res.send("<script>alert('البيانات خاطئة'); window.location='/login';</script>");
    }
});

app.get('/admin-panel', (req, res) => {
    if (!req.session.isAdmin) return res.redirect('/login');
    res.render('admin', { accounts: accounts, settings: siteSettings });
});

app.post('/update-settings', (req, res) => {
    if (!req.session.isAdmin) return res.status(403).send("Unauthorized");
    siteSettings.supportLink = req.body.supportLink;
    siteSettings.mediationLink = req.body.mediationLink;
    siteSettings.sellAccountLink = req.body.sellAccountLink;
    siteSettings.announcement = req.body.announcement;
    res.redirect('/admin-panel');
});

app.post('/add-account', upload.array('imageFiles', 5), (req, res) => {
    if (!req.session.isAdmin) return res.status(403).send("Unauthorized");
    const imagePaths = req.files.map(file => '/uploads/' + file.filename);
    const newAcc = {
        id: Math.floor(1000 + Math.random() * 9000),
        title: req.body.title,
        price: parseFloat(req.body.price),
        players: req.body.players,
        linkType: req.body.linkType,
        imgs: imagePaths.length > 0 ? imagePaths : ['https://via.placeholder.com/400x225']
    };
    accounts.push(newAcc);
    res.redirect('/admin-panel');
});

app.get('/delete/:id', (req, res) => {
    if (!req.session.isAdmin) return res.status(403).send("Unauthorized");
    accounts = accounts.filter(acc => acc.id != req.params.id);
    res.redirect('/admin-panel');
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`WassitDZ Game running on port ${PORT}`));
