from flask import Flask
import os
import os.path as op
import flask_admin as admin
from flask import request
from flask_admin.contrib.fileadmin import FileAdmin
import os
from flask import Flask, url_for, redirect, render_template, request
from flask.ext.admin import Admin
from flask.ext.admin import AdminIndexView
from flask.ext.sqlalchemy import SQLAlchemy
from wtforms import form, fields, validators
import flask.ext.login as login
from flask.ext.admin.contrib import sqla
from flask.ext.admin import helpers, expose
from werkzeug.security import generate_password_hash, check_password_hash


class NewAlgoView(admin.BaseView):
    @admin.expose('/', methods=('GET', 'POST'))
    def index(self):
        if request.method == 'POST':
            if request.values.get('algorithm_name') and \
                            request.values.get('dependency') and \
                            request.values.get('code'):
                with open("requirements.txt", "w") as text_file:
                    text_file.write(request.values.get('dependency'))
                with open(request.values.get('algorithm_name') + '.py', "w") as text_file:
                    text_file.write(request.values.get('code'))
        return self.render('new_algo.html')

    # @admin.expose('/', methods=['POST'])
    # def index(self):
    #     text = request.form['text']
    #     processed_text = text.upper()
    #     return processed_text
    def is_visible(self):
        if not login.current_user.is_anonymous:
            return True
        else:
            return False


class ManageAlgoView(admin.BaseView):
    @admin.expose('/')
    def index(self):
        return self.render('manage_algo.html')

    @admin.expose('/test/')
    def test(self):
        return self.render('test.html')

    def is_visible(self):
        if not login.current_user.is_anonymous:
            return True
        else:
            return False


class MyFileAdmin(FileAdmin):
    def get_base_path(self):
        path = FileAdmin.get_base_path(self)

        if not login.current_user.is_anonymous:
            path = os.path.join(path, login.current_user.login)
            try:
                os.mkdir(path)
            except OSError:
                pass
            return path
        else:
            return path

    def is_visible(self):
        if not login.current_user.is_anonymous:
            return True
        else:
            return False


# Create flask app
app = Flask(__name__, template_folder='templates', static_folder='files')
app.debug = True
# Create dummy secrey key so we can use flash
app.config['SECRET_KEY'] = '123456790'
app.config['DATABASE_FILE'] = 'sample_db.sqlite'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + app.config['DATABASE_FILE']
app.config['SQLALCHEMY_ECHO'] = True
db = SQLAlchemy(app)
# Flask views

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    login = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120))
    password = db.Column(db.String(64))

    # Flask-Login integration
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    # Required for administrative interface
    def __unicode__(self):
        return self.username


# Define login and registration forms (for flask-login)
class LoginForm(form.Form):
    login = fields.TextField(validators=[validators.required()])
    password = fields.PasswordField(validators=[validators.required()])

    def validate_login(self, field):
        user = self.get_user()

        if user is None:
            raise validators.ValidationError('Invalid user')

        # we're comparing the plaintext pw with the the hash from the db
        if not check_password_hash(user.password, self.password.data):
        # to compare plain text passwords use
        # if user.password != self.password.data:
            raise validators.ValidationError('Invalid password')

    def get_user(self):
        return db.session.query(User).filter_by(login=self.login.data).first()


class RegistrationForm(form.Form):
    login = fields.TextField(validators=[validators.required()])
    email = fields.TextField()
    password = fields.PasswordField(validators=[validators.required()])

    def validate_login(self, field):
        if db.session.query(User).filter_by(login=self.login.data).count() > 0:
            raise validators.ValidationError('Duplicate username')


# Initialize flask-login
def init_login():
    login_manager = login.LoginManager()
    login_manager.init_app(app)

    # Create user loader function
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(User).get(user_id)


# Create customized model view class
class MyModelView(sqla.ModelView):

    def is_accessible(self):
        return login.current_user.is_authenticated and login.current_user.login == 'admin'


# Create customized index view class that handles login & registration
class MyAdminIndexView(AdminIndexView):

    @expose('/')
    def index(self):
        if not login.current_user.is_authenticated:
            return redirect(url_for('.login_view'))
        return super(MyAdminIndexView, self).index()

    @expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        # handle user login
        form = LoginForm(request.form)
        if helpers.validate_form_on_submit(form):
            user = form.get_user()
            login.login_user(user)

        if login.current_user.is_authenticated:
            return redirect(url_for('.index'))
        link = '<p>Don\'t have an account? <a href="' + url_for('.register_view') + '">Click here to register.</a></p>'
        self._template_args['form'] = form
        self._template_args['link'] = link
        return super(MyAdminIndexView, self).index()

    @expose('/register/', methods=('GET', 'POST'))
    def register_view(self):
        form = RegistrationForm(request.form)
        if helpers.validate_form_on_submit(form):
            user = User()

            form.populate_obj(user)
            # we hash the users password to avoid saving it as plaintext in the db,
            # remove to use plain text:
            user.password = generate_password_hash(form.password.data)

            db.session.add(user)
            db.session.commit()

            login.login_user(user)
            return redirect(url_for('.index'))
        link = '<p>Already have an account? <a href="' + url_for('.login_view') + '">Click here to log in.</a></p>'
        self._template_args['form'] = form
        self._template_args['link'] = link
        return super(MyAdminIndexView, self).index()

    @expose('/logout/')
    def logout_view(self):
        login.logout_user()
        return redirect(url_for('.index'))


# Flask views
# @app.route('/')
# def index():
#     return render_template('index.html')

@app.route('/')
def index():
    return '<a href="/admin/">Click me to get to Admin!</a>'

def build_sample_db():
    """
    Populate a small db with some example entries.
    """

    import string
    import random

    db.drop_all()
    db.create_all()
    # passwords are hashed, to use plaintext passwords instead:
    # test_user = User(login="test", password="test")
    test_user = User(login="test", password=generate_password_hash("test"))
    db.session.add(test_user)

    first_names = [
        'Harry', 'Amelia', 'Oliver', 'Jack', 'Isabella', 'Charlie','Sophie', 'Mia',
        'Jacob', 'Thomas', 'Emily', 'Lily', 'Ava', 'Isla', 'Alfie', 'Olivia', 'Jessica',
        'Riley', 'William', 'James', 'Geoffrey', 'Lisa', 'Benjamin', 'Stacey', 'Lucy'
    ]
    last_names = [
        'Brown', 'Smith', 'Patel', 'Jones', 'Williams', 'Johnson', 'Taylor', 'Thomas',
        'Roberts', 'Khan', 'Lewis', 'Jackson', 'Clarke', 'James', 'Phillips', 'Wilson',
        'Ali', 'Mason', 'Mitchell', 'Rose', 'Davis', 'Davies', 'Rodriguez', 'Cox', 'Alexander'
    ]

    for i in range(len(first_names)):
        user = User()
        user.first_name = first_names[i]
        user.last_name = last_names[i]
        user.login = user.first_name.lower()
        user.email = user.login + "@example.com"
        user.password = generate_password_hash(''.join(random.choice(string.ascii_lowercase + string.digits) for i in range(10)))
        db.session.add(user)

    db.session.commit()
    return

# Create directory
path = op.join(op.dirname(__file__), 'files')
try:
    os.mkdir(path)
except OSError:
    pass

init_login()
# Create admin interface
# admin = admin.Admin(name="Algorithm", template_mode='bootstrap3')
admin = admin.Admin(app, 'Algorithm', index_view=MyAdminIndexView(), base_template='master.html')
admin.add_view(MyFileAdmin(path, '/files/', name='Files'))
admin.add_view(NewAlgoView(name="new algo", category='Algo'))
admin.add_view(ManageAlgoView(name="manage algo", category='Algo'))
admin.add_view(MyModelView(User, db.session))
# admin.init_app(app)


if __name__ == '__main__':
    app_dir = os.path.realpath(os.path.dirname(__file__))
    database_path = os.path.join(app_dir, app.config['DATABASE_FILE'])
    if not os.path.exists(database_path):
        build_sample_db()
    # Start app
    app.run(debug=True)
