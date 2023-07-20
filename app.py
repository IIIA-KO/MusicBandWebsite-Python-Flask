from flask import Flask, render_template, request, redirect, url_for, session, flash, current_app
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'my_secret_key_for_imagine_dragons_website'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///albums.db'
app.config['COVER_IMAGE_UPLOAD_FOLDER'] = 'static/images/covers/'

db = SQLAlchemy(app)
migrate = Migrate(app, db)

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}


# ------------------------------------------------------------------------------
class Albums(db.Model):
    __tablename__ = 'albums'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    cover = db.Column(db.String(255))


# ------------------------------------------------------------------------------
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return '<User %r>' % self.username


def is_valid_password(password):
    if not any(char.isupper() for char in password) or not any(char.isdigit() for char in password):
        return False

    if len(password) < 8:
        return False

    return True


@app.route('/', methods=['GET', 'POST'])
def index():
    if 'username' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        action = request.form['action']
        if action == 'register':
            return redirect(url_for('register'))
        elif action == 'login':
            return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = Users.query.filter_by(username=username).first()
        if existing_user:
            flash('A user with this name already exists')
            return redirect(url_for('register'))

        if not is_valid_password(password):
            flash(
                'The password must contain at least one capital letter, one digit and be no shorter than 8 characters')
            return redirect(url_for('register'))

        new_user = Users(username=username, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = Users.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['username'] = user.username
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('index'))
    return render_template('home.html', username=session['username'])


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


# ------------------------------------------------------------------------------
@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/history')
def history():
    return render_template('history.html')


@app.route('/albums')
def albums():
    albums_to_show = Albums.query.all()
    return render_template('albums.html', albums=albums_to_show)


@app.route('/album/<int:album_id>')
def album_details(album_id):
    album = Albums.query.get(album_id)
    return render_template('album_details.html', album=album)


# ------------------------------------------------------------------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/add_album', methods=['GET', 'POST'])
def add_album():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        cover_image = request.files['cover_image'] if 'cover_image' in request.files else None

        new_album = Albums(title=title, description=description)

        if cover_image and allowed_file(cover_image.filename):
            db.session.add(new_album)
            db.session.commit()

            album_id = new_album.id
            filename = secure_filename(cover_image.filename)
            filename = f"{album_id}{os.path.splitext(filename)[1]}"
            cover_image_path = os.path.join(app.config['COVER_IMAGE_UPLOAD_FOLDER'], filename)
            cover_image.save(cover_image_path)
            new_album.cover = f'/images/covers/{filename}'

            db.session.commit()
        else:
            new_album.cover = '/images/default_cover.jpg'

            db.session.add(new_album)
            db.session.commit()

        return redirect(url_for('albums'))
    return render_template('add_album.html')


def get_file_extension(filename):
    return os.path.splitext(filename)[1].lower()


@app.route('/edit_album/<int:album_id>', methods=['GET', 'POST'])
def edit_album(album_id):
    album = Albums.query.get(album_id)
    if request.method == 'POST':
        album.title = request.form['title']
        album.description = request.form['description']
        cover_image = request.files['cover_image'] if 'cover_image' in request.files else None

        if cover_image and allowed_file(cover_image.filename):
            extension = get_file_extension(cover_image.filename)
            filename = f"{album.id}{extension}"
            cover_image_path = os.path.join(app.root_path, 'static', 'images', 'covers', filename)
            cover_image.save(cover_image_path)
            album.cover = f'/images/covers/{filename}'

        db.session.commit()
        return redirect(url_for('albums'))
    return render_template('edit_album.html', album=album)


@app.route('/delete_album/<int:album_id>', methods=['GET', 'POST', 'DELETE'])
def delete_album(album_id):
    album = Albums.query.get(album_id)
    return render_template('delete_album.html', album=album)


@app.route('/confirm_delete_album/<int:album_id>', methods=['GET', 'POST', 'DELETE'])
def confirm_delete_album(album_id):
    album = Albums.query.get(album_id)
    if album.cover and album.cover != '/images/default_cover.jpg':
        file_path = os.path.join(app.static_folder, album.cover.strip('/'))
        if os.path.exists(file_path):
            os.remove(file_path)
    db.session.delete(album)
    db.session.commit()
    return redirect(url_for('albums'))


if __name__ == '__main__':
    db.create_all()
    app.run(host='0.0.0.0', port=5000)
