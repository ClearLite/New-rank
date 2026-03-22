# run.py
from flask import Flask, render_template, request, redirect, session, url_for
from models import db, Media, SubMedia, Genre
import os

app = Flask(__name__)
app.secret_key = 'super_secret_key_change_this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rankings.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db.init_app(app)

# Helper function to check Legendary Status (Rainbow Border)
def is_legendary(media_type, score):
    if score is None: return False
    
    thresholds = {
        'Movie': 9.0, 'TV Show': 9.0, 'TV Show Season': 9.0, 'Videogame': 9.0, 'Videogame Part': 9.0,
        'Album': 8.5, 'Extended Play': 8.5, 'Mixtape': 8.5, 'Compilation': 8.5, 'OST': 8.5,
        'TV Show Episode': 9.5, 'Song': 9.5
    }
    
    # Default to 10.0 if not found, but it should be mapped above
    required_score = thresholds.get(media_type, 10.0)
    return score >= required_score

# Helper to assign UI Colors based on media type
def get_media_color(media_type):
    colors = {
        'Movie': 'blue', 'TV Show': 'green', 'TV Show Season': 'green', 'TV Show Episode': 'green',
        'Album': 'red', 'Extended Play': 'red', 'Mixtape': 'red', 'Compilation': 'red', 'OST': 'red',
        'Single': 'yellow', 'Song': 'yellow', 
        'Videogame': 'purple', 'Videogame Part': 'purple'
    }
    return colors.get(media_type, 'grey')

# Pass helpers to templates
app.context_processor(lambda: dict(is_legendary=is_legendary, get_media_color=get_media_color))

@app.before_request
def create_tables():
    db.create_all()

@app.route('/')
def index():
    # Filter functionality
    filter_type = request.args.get('filter', 'All')
    if filter_type == 'All':
        media_items = Media.query.order_by(Media.score.desc()).all()
    elif filter_type == 'Songs':
        # Special filter for songs (SubMedia)
        media_items = SubMedia.query.filter_by(sub_type='Song').order_by(SubMedia.score.desc()).all()
    else:
        media_items = Media.query.filter_by(media_type=filter_type).order_by(Media.score.desc()).all()
    return render_template('index.html', media_items=media_items, filter_type=filter_type)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'Ryan' and request.form['password'] == '06242005':
            session['admin'] = True
            return redirect(url_for('index'))
        else:
            return "Invalid Credentials"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/media/<int:media_id>')
def detail(media_id):
    media = Media.query.get_or_404(media_id)
    sub_items = SubMedia.query.filter_by(parent_id=media.id).order_by(SubMedia.number.asc()).all()
    return render_template('detail.html', media=media, sub_items=sub_items)

# --- API AUTO-POPULATION STUBS ---
# To implement real fetching, you will need to pip install 'tmdbv3api' for movies/tv, 
# 'spotipy' for music, and use RAWG API for games.
@app.route('/add_from_internet', methods=['POST'])
def add_from_internet():
    if not session.get('admin'): return redirect(url_for('login'))
    search_term = request.form['title']
    media_category = request.form['category']
    
    # EXAMPLE LOGIC (You will replace this with actual API calls):
    # if media_category == 'Movie':
    #     data = fetch_tmdb_movie(search_term)
    #     new_media = Media(title=data['title'], release_year=data['year'], ...)
    #     db.session.add(new_media)
    #     db.session.commit()
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
