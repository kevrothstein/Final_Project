# Import statements
import os
import requests
import json
from omdb_api_key import api_key
from flask import Flask, render_template, session, redirect, request, url_for, flash
from flask_script import Manager, Shell
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField, PasswordField, BooleanField, SelectMultipleField, ValidationError
from wtforms.validators import Required, Length, Email, Regexp, EqualTo
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand
from werkzeug.security import generate_password_hash, check_password_hash

# Imports for login management
from flask_login import LoginManager, login_required, logout_user, login_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Application configurations
app = Flask(__name__)
app.debug = True
app.use_reloader = True
app.config['SECRET_KEY'] = 'hardtoguessstring'
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL') or "postgresql://localhost/FinalProject" # TODO 364: You should edit this to correspond to the database name YOURUNIQNAMEHW4db and create the database of that name (with whatever your uniqname is; for example, my database would be jczettaHW4db). You may also need to edit the database URL further if your computer requires a password for you to run this.
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# App addition setups
manager = Manager(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)

# Login configurations setup
login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'
login_manager.init_app(app) # set up login manager

########################
######## Models ########
########################
search_movies = db.Table('tags', db.Column('movie_id', db.Integer, db.ForeignKey('movies.id')), db.Column('movie_search_term', db.String(32), db.ForeignKey('movie_search_terms.term')))
search_series = db.Table('series_tags', db.Column('series_id', db.Integer, db.ForeignKey('series.id')), db.Column('series_search_term', db.String(32), db.ForeignKey('series_search_terms.term')))

user_collection = db.Table('user_collection', db.Column('movie_id', db.Integer, db.ForeignKey('movies.id')), db.Column('collection_id', db.Integer, db.ForeignKey('personal_movie_collections.id')))

## User-related Models

# Special model for users to log in
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, index=True)
    email = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    personal_movie_collections = db.relationship('PersonalMovieCollection', backref='User')

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

## DB load function
## Necessary for behind the scenes login manager that comes with flask_login capabilities! Won't run without this.
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id)) # returns User object or None

# Model to store gifs
class Movie(db.Model):
    __tablename__ = 'movies'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128))
    embedURL = db.Column(db.String(256))
    plot = db.Column(db.String(512))


    # TODO 364: Define a __repr__ method for the Gif model that shows the title and the URL of the gif
    def __repr__(self):
        return "{}: {}".format(self.title, self.embedURL)

# Model to store a personal gif collection
class PersonalMovieCollection(db.Model):
    __tablename__ = 'personal_movie_collections'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    movies = db.relationship('Movie', secondary=user_collection, backref=db.backref('personal_movie_collections', lazy='dynamic'), lazy='dynamic')



class MovieSearchTerm(db.Model):
    __tablename__ = 'movie_search_terms'
    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(32), unique=True)
    movie = db.relationship('Movie', secondary=search_movies, backref=db.backref('movie_search_terms', lazy='dynamic'), lazy='dynamic')
    # TODO 364: Define a __repr__ method for this model class that returns the term string
    def __repr__(self):
        return "{}".format(self.term)

# Model to store gifs
class Series(db.Model):
    __tablename__ = 'series'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128))
    embedURL = db.Column(db.String(256))
    plot = db.Column(db.String(512))

    # TODO 364: Define a __repr__ method for the Gif model that shows the title and the URL of the gif
    def __repr__(self):
        return "{}: {}".format(self.title, self.embedURL)

class SeriesSearchTerm(db.Model):
    __tablename__ = 'series_search_terms'
    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(32), unique=True)
    series = db.relationship('Series', secondary=search_series, backref=db.backref('Series_search_terms', lazy='dynamic'), lazy='dynamic')
    # TODO 364: Define a __repr__ method for this model class that returns the term string
    def __repr__(self):
        return "{}".format(self.term)

########################
######## Forms #########
########################

# Provided
class RegistrationForm(FlaskForm):
    email = StringField('Email:', validators=[Required(),Length(1,64),Email()])
    username = StringField('Username:',validators=[Required(),Length(1,64),Regexp('^[A-Za-z][A-Za-z0-9_.]*$',0,'Usernames must have only letters, numbers, dots or underscores')])
    password = PasswordField('Password:',validators=[Required(),EqualTo('password2',message="Passwords must match")])
    password2 = PasswordField("Confirm Password:",validators=[Required()])
    submit = SubmitField('Register User')

    def validate_email(self,field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self,field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken')

# Provided
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[Required(), Length(1,64), Email()])
    password = PasswordField('Password', validators=[Required()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log In')

# TODO 364: The following forms for searching for gifs and creating collections are provided and should not be edited. You SHOULD examine them so you understand what data they pass along and can investigate as you build your view functions in TODOs below.
class MovieSearchForm(FlaskForm):
    search = StringField("Enter a term to search Movies", validators=[Required()])
    submit = SubmitField('Submit')

    def validate_search(self, field):
        if len(self.search.data) > 30:
            raise ValidationError('Please keep searches under 30 characters')
        if "'" in self.search.data:
            raise ValidationError('Please no single quotes in searches')
        

class SeriesSearchForm(FlaskForm):
    search = StringField("Enter a term to search TV Series", validators=[Required()])
    submit = SubmitField('Submit')

class CollectionCreateForm(FlaskForm):
    name = StringField('Collection Name',validators=[Required()])
    movie_picks = SelectMultipleField('Movies to include')
    submit = SubmitField("Create Collection")

    def validate_movie_picks(self, field):
        print(field.data)
        if len(field.data) == 0:
            raise ValidationError('A movie collection must contain at least one movie.')

class DeleteSearchForm(FlaskForm):
    submit = SubmitField("Delete Search Term")

class UpdateCollectionButton(FlaskForm):
    submit = SubmitField("Change name of Collection")

class UpdateCollectionForm(FlaskForm):
    name = StringField('New Collection Name',validators=[Required()])
    submit = SubmitField("Update Collection Name")

########################
### Helper functions ###
########################

def get_movies_from_omdb(search_string):
    baseurl = "http://www.omdbapi.com/?t={}&apikey={}&type=movie".format(search_string, api_key)
    print(baseurl)
    r = requests.get(baseurl)
    print(r.json())
    movie = r.json()
    return movie

def get_series_from_omdb(search_string):
    baseurl = "http://www.omdbapi.com/?t={}&apikey={}&type=series".format(search_string, api_key)
    print(baseurl)
    r = requests.get(baseurl)
    print(r.json())
    series = r.json()
    return series

def get_movie_by_id(id):
    m = Movie.query.filter_by(id=id).first()
    return m

def get_or_create_movie(db_session, title, url, plot):
    movie = db_session.query(Movie).filter_by(title=title).first()
    if movie:
        return movie
    else:
        print("creating movie {}".format(title))
        movie = Movie(title=title, embedURL=url, plot=plot)
        db_session.add(movie)
        db_session.commit()
        return movie

def get_or_create_movie_search_term(db_session, term, movie_list = []):
    """Always returns a SearchTerm instance"""
    movie_search_term = db_session.query(MovieSearchTerm).filter_by(term=term).first()
    if movie_search_term:
        print("found term")
        return movie_search_term
    else:
        print ("adding term")
        movie_search_term = MovieSearchTerm(term = term)
        result = get_movies_from_omdb(term)     
        movie = get_or_create_movie(db_session, title = result['Title'], url = result['Poster'], plot = result['Plot'])
        movie_search_term.movie.append(movie)
        db_session.add(movie_search_term)
        db_session.commit()

        return movie_search_term

def get_or_create_collection(db_session, name, current_user, movie_list):
    collection = PersonalMovieCollection.query.filter_by(name=name, user_id=current_user.id).first()
    if collection:
        return collection
    else:
        collection = PersonalMovieCollection(name=name, user_id=current_user.id, movies=[])
        for m in movie_list:
            collection.movies.append(m)
        db_session.add(collection)
        db_session.commit()
        return collection

def get_or_create_series(db_session, title, url):
    s = db_session.query(Movie).filter_by(title=title).first()
    if s:
        return s
    else:
        print("createing series {}".format(title))
        s = Series(title=title, embedURL=url)
        db_session.add(s)
        db_session.commit()
        return s

def get_or_create_series_search_term(db_session, term, series_list = []):
    series_search_term = db_session.query(SeriesSearchTerm).filter_by(term=term).first()
    if series_search_term:
        print("found term")
        return series_search_term
    else:
        print ("adding term")
        series_search_term = SeriesSearchTerm(term = term)
        result = get_series_from_omdb(term)   
        series = get_or_create_series(db_session, title = result['Title'], url = result['Poster'])
        series_search_term.series.append(series)
        db_session.add(series_search_term)
        db_session.commit()

        return series_search_term

########################
#### View functions ####
########################

## Error handling routes
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


## Login-related routes
@app.route('/login',methods=["GET","POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            return redirect(request.args.get('next') or url_for('index'))
        flash('Invalid username or password.')
    return render_template('login.html',form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out')
    return redirect(url_for('index'))

@app.route('/register',methods=["GET","POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,username=form.username.data,password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('You can now log in!')
        return redirect(url_for('login'))
        flash('You are now logged in!')
        return redirect(url_for('index'))
    return render_template('register.html',form=form)

@app.route('/secret')
@login_required
def secret():
    return "You are authenticated"

## Other routes
@app.route('/', methods=['GET', 'POST'])
def index():
    form = MovieSearchForm()
    if request.method == "POST" and form.validate_on_submit():
        movie_search_term = get_or_create_movie_search_term(db.session, term=form.search.data)
        return redirect(url_for('movie_search_results', movie_search_term=form.search.data))
    else:
        errors = [e for e in form.errors.values()]
        if len(errors) > 0:
            flash(str(errors))
        return render_template('index.html', form=form)

@app.route('/search_series', methods=['GET', 'POST'])
def search_series():
    form = SeriesSearchForm(request.args)
    if request.method == "GET" and form.search.data:
        series_search_term = get_or_create_series_search_term(db.session, term=form.search.data)
        return redirect(url_for('series_search_results', series_search_term=form.search.data))
    else:
        return render_template('search_series.html', form=form)

@app.route('/series_searched/<series_search_term>')
def series_search_results(series_search_term):
    term = SeriesSearchTerm.query.filter_by(term=series_search_term).first()
    relevant_series = term.series.all()

    return render_template('searched_series.html',series=relevant_series, term=term)

# Provided
@app.route('/movies_searched/<movie_search_term>')
def movie_search_results(movie_search_term):
    term = MovieSearchTerm.query.filter_by(term=movie_search_term).first()
    relevant_movies = term.movie.all()

    return render_template('searched_movies.html',movies=relevant_movies, term=term)

@app.route('/movie_search_terms')
def movie_search_terms():
    form= DeleteSearchForm()
    movie_search_terms = MovieSearchTerm.query.all()
    return render_template('movie_search_terms.html', all_terms=movie_search_terms, form=form)

@app.route('/series_search_terms')
def series_search_terms():
    form= DeleteSearchForm()
    series_search_terms = SeriesSearchTerm.query.all()
    return render_template('series_search_terms.html', all_terms=series_search_terms, form=form)

# Provided
@app.route('/all_movies')
def all_movies():
    movies = Movie.query.all()
    return render_template('all_movies.html',all_movies=movies)

@app.route('/create_collection',methods=["GET","POST"])
@login_required
def create_collection():
    form = CollectionCreateForm()
    movies = Movie.query.all()
    choices = [(str(g.id), g.title) for g in movies]
    form.movie_picks.choices = choices
    if request.method == "POST" and form.validate_on_submit():
        movies_selected = form.movie_picks.data
        movie_objects = [get_movie_by_id(int(id)) for id in movies_selected]
        get_or_create_collection(db.session, name=form.name.data, current_user=current_user, movie_list=movie_objects)
        print("Collection created")
        return redirect(url_for('collections'))
    else:
        errors = [e for e in form.errors.values()]
        if len(errors) > 0:
            flash(str(errors))
        return render_template('create_collection.html', form=form)

@app.route('/update/<id>', methods = ['GET','POST'])
def update_collection(id):
    form = UpdateCollectionForm()
    collection = PersonalMovieCollection.query.filter_by(id = id).first()
    if form.name.data:
        new_name = form.name.data
        collection.name = new_name
        db.session.commit()
        return redirect(url_for('collections'))
    return render_template('update_collection.html', collection=collection,  form = form)

@app.route('/collections',methods=["GET","POST"])
@login_required
def collections():
    all_collections = PersonalMovieCollection.query.filter_by(user_id=current_user.id).all()
    return render_template('collections.html', collections=all_collections)

@app.route('/collection/<id_num>', methods = ['GET','POST'])
def single_collection(id_num):
    id_num = int(id_num)
    collection = PersonalMovieCollection.query.filter_by(id=id_num).first()
    movies = collection.movies.all()
    form = UpdateCollectionButton()
    return render_template('collection.html',collection=collection, id=id_num, movies=movies, form=form)

@app.route('/delete/<movie_term>',methods=["GET","POST"])
def delete(movie_term):
    db.session.delete(MovieSearchTerm.query.filter_by(term=movie_term).first())
    db.session.commit()
    return redirect(url_for('movie_search_terms'))

if __name__ == '__main__':
    db.create_all()
    manager.run()
