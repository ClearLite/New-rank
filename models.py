# models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# --- SEPARATED REFERENCE TABLES ---
class Genre(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False) # e.g. "Action", "Marvel", "DC"

class Studio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)

class Person(db.Model): # Handles Directors, Artists, etc.
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)

class Platform(db.Model): # For Videogames
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

# --- MEDIA TABLES ---
class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    media_type = db.Column(db.String(50), nullable=False) # 'Movie', 'TV Show', 'Videogame', 'Album', 'Single', etc.
    release_year = db.Column(db.Integer)
    score = db.Column(db.Float, default=0.0) # Can exceed 10.0
    poster_url = db.Column(db.String(500)) # Online URL or local upload path
    banner_url = db.Column(db.String(500))
    
    # Relationships to normalized tables (Many-to-Many)
    genres = db.relationship('Genre', secondary='media_genre', backref='media_items')
    studios = db.relationship('Studio', secondary='media_studio', backref='media_items')
    creators = db.relationship('Person', secondary='media_person', backref='media_items') # Directors/Artists
    platforms = db.relationship('Platform', secondary='media_platform', backref='games')

# --- MANY-TO-MANY ASSOCIATION TABLES ---
media_genre = db.Table('media_genre',
    db.Column('media_id', db.Integer, db.ForeignKey('media.id'), primary_key=True),
    db.Column('genre_id', db.Integer, db.ForeignKey('genre.id'), primary_key=True)
)
media_studio = db.Table('media_studio',
    db.Column('media_id', db.Integer, db.ForeignKey('media.id'), primary_key=True),
    db.Column('studio_id', db.Integer, db.ForeignKey('studio.id'), primary_key=True)
)
media_person = db.Table('media_person',
    db.Column('media_id', db.Integer, db.ForeignKey('media.id'), primary_key=True),
    db.Column('person_id', db.Integer, db.ForeignKey('person.id'), primary_key=True)
)
media_platform = db.Table('media_platform',
    db.Column('media_id', db.Integer, db.ForeignKey('media.id'), primary_key=True),
    db.Column('platform_id', db.Integer, db.ForeignKey('platform.id'), primary_key=True)
)

# For sub-media (Episodes, Game Parts, Songs)
class SubMedia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('media.id'))
    title = db.Column(db.String(255))
    sub_type = db.Column(db.String(50)) # 'Episode', 'Song', 'Game Part'
    number = db.Column(db.Integer) # Episode number / Track number
    score = db.Column(db.Float, default=0.0)
