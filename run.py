# run.py
import os
import requests
from flask import Flask, render_template, request, redirect, session, url_for, flash
from models import db, Media, SubMedia, Genre, Studio, Person, Platform
from dotenv import load_dotenv
from ytmusicapi import YTMusic

# Load API keys from the .env file
load_dotenv()
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
RAWG_API_KEY = os.getenv('RAWG_API_KEY')

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'fallback_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rankings.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
ytmusic = YTMusic() # Initialize YouTube Music API

# --- UI HELPERS ---
def is_legendary(media_type, score):
    if score is None: return False
    thresholds = {
        'Movie': 9.0, 'TV Show': 9.0, 'TV Show Season': 9.0, 'Videogame': 9.0, 'Videogame Part': 9.0,
        'Album': 8.5, 'Extended Play': 8.5, 'Mixtape': 8.5, 'Compilation': 8.5, 'OST': 8.5,
        'TV Show Episode': 9.5, 'Song': 9.5
    }
    required_score = thresholds.get(media_type, 10.0)
    return score >= required_score

def get_media_color(media_type):
    colors = {
        'Movie': 'blue', 'TV Show': 'green', 'TV Show Season': 'green', 'TV Show Episode': 'green',
        'Album': 'red', 'Extended Play': 'red', 'Mixtape': 'red', 'Compilation': 'red', 'OST': 'red',
        'Single': 'yellow', 'Song': 'yellow', 
        'Videogame': 'purple', 'Videogame Part': 'purple'
    }
    return colors.get(media_type, 'grey')

app.context_processor(lambda: dict(is_legendary=is_legendary, get_media_color=get_media_color))

# --- DATABASE HELPER ---
def get_or_create(session, model, **kwargs):
    """Helper to avoid creating duplicate genres, studios, etc."""
    instance = session.query(model).filter_by(**kwargs).first()
    if not instance:
        instance = model(**kwargs)
        session.add(instance)
    return instance

# --- API FETCHING HELPERS ---
def fetch_tmdb(title, media_type):
    search_type = 'movie' if media_type == 'Movie' else 'tv'
    search_url = f"https://api.themoviedb.org/3/search/{search_type}?api_key={TMDB_API_KEY}&query={title}"
    res = requests.get(search_url).json()
    
    if not res.get('results'): return None
    
    # Get ID of the top result to fetch deep details (Studios, Directors, etc)
    item_id = res['results'][0]['id']
    detail_url = f"https://api.themoviedb.org/3/{search_type}/{item_id}?api_key={TMDB_API_KEY}&append_to_response=credits"
    details = requests.get(detail_url).json()
    
    year_str = details.get('release_date', '') if media_type == 'Movie' else details.get('first_air_date', '')
    
    # Check for Marvel/DC to add custom genres
    studios = [s['name'] for s in details.get('production_companies', [])]
    genres = [g['name'] for g in details.get('genres',[])]
    if any("Marvel" in s for s in studios): genres.append("Marvel")
    if any("DC Comics" in s for s in studios): genres.append("DC")

    return {
        'title': details.get('title') or details.get('name'),
        'release_year': int(year_str.split('-')[0]) if year_str else None,
        'poster_url': f"https://image.tmdb.org/t/p/w500{details.get('poster_path')}" if details.get('poster_path') else None,
        'genres': genres,
        'studios': studios,
        'creators': [crew['name'] for crew in details.get('credits', {}).get('crew', []) if crew['job'] in ['Director', 'Executive Producer']][:3] # Get top 3
    }

def fetch_rawg(title):
    url = f"https://api.rawg.io/api/games?key={RAWG_API_KEY}&search={title}"
    res = requests.get(url).json()
    
    if not res.get('results'): return None
    
    game = res['results'][0]
    # Get deeper details for Developer
    detail_res = requests.get(f"https://api.rawg.io/api/games/{game['id']}?key={RAWG_API_KEY}").json()
    
    year_str = game.get('released', '')
    
    return {
        'title': game['name'],
        'release_year': int(year_str.split('-')[0]) if year_str else None,
        'poster_url': game.get('background_image'),
        'genres': [g['name'] for g in game.get('genres', [])],
        'platforms': [p['platform']['name'] for p in game.get('platforms', [])],
        'creators': [d['name'] for d in detail_res.get('developers', [])], # Developers
        'studios': [p['name'] for p in detail_res.get('publishers',[])]  # Publishers
    }

def fetch_ytmusic(title):
    results = ytmusic.search(title, filter="albums")
    if not results: return None
    
    album_id = results[0]['browseId']
    album_info = ytmusic.get_album(album_id)
    
    thumbnails = album_info.get('thumbnails',[])
    
    return {
        'title': album_info['title'],
        'release_year': album_info.get('year'),
        'poster_url': thumbnails[-1]['url'] if thumbnails else "",
        'creators': [artist['name'] for artist in album_info.get('artists',[])],
        'tracks': [{'number': i+1, 'title': t['title']} for i, t in enumerate(album_info.get('tracks',[]))]
    }

# --- ROUTES ---
@app.before_request
def create_tables():
    db.create_all()

@app.route('/')
def index():
    filter_type = request.args.get('filter', 'All')
    if filter_type == 'All':
        media_items = Media.query.order_by(Media.score.desc()).all()
    elif filter_type == 'Songs':
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

@app.route('/add', methods=['GET', 'POST'])
def add_media():
    if not session.get('admin'): return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        data = None
        
        # 1. Fetch Data
        try:
            if category in['Movie', 'TV Show']:
                data = fetch_tmdb(title, category)
            elif category == 'Videogame':
                data = fetch_rawg(title)
            elif category == 'Album':
                data = fetch_ytmusic(title)
        except Exception as e:
            return f"Error fetching data: {str(e)}"
            
        if not data:
            return "Could not find that media online!"

        # 2. Save Main Media
        new_media = Media(
            title=data['title'],
            media_type=category,
            release_year=data.get('release_year'),
            poster_url=data.get('poster_url'),
            score=0.0 # Default score, you will edit this later
        )
        
        # 3. Save Normalized Data (Genres, Studios, Creators, Platforms)
        for g_name in data.get('genres',[]):
            new_media.genres.append(get_or_create(db.session, Genre, name=g_name))
            
        for s_name in data.get('studios',[]):
            new_media.studios.append(get_or_create(db.session, Studio, name=s_name))
            
        for c_name in data.get('creators',[]):
            new_media.creators.append(get_or_create(db.session, Person, name=c_name))
            
        for p_name in data.get('platforms',[]):
            new_media.platforms.append(get_or_create(db.session, Platform, name=p_name))
            
        db.session.add(new_media)
        db.session.commit() # Commit to get the new_media.id
        
        # 4. Save SubMedia (Like Songs in an Album)
        if 'tracks' in data:
            for track in data['tracks']:
                new_song = SubMedia(
                    parent_id=new_media.id,
                    title=track['title'],
                    sub_type='Song',
                    number=track['number'],
                    score=0.0
                )
                db.session.add(new_song)
            db.session.commit()
            
        return redirect(url_for('detail', media_id=new_media.id))
        
    return render_template('add.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
