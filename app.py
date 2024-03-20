from flask import Flask, session, render_template, redirect, url_for, request, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import fonction_web


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'



# Articles codés en dur avec des dates
articles = [
    {'id': 1, 'title': 'Article Public 1', 'content': 'Contenu de l\'article public 1...', 'date': '2024-01-01'},
    {'id': 2, 'title': 'Article Public 2', 'content': 'Contenu de l\'article public 2...', 'date': '2024-01-02'},
    {'id': 3, 'title': 'Article Public 3', 'content': 'Contenu de l\'article public 3...', 'date': '2024-01-03'},
]

class User(UserMixin):
    def __init__(self, user_id, password,follow):
        self.id = user_id
        self.password = password
        self.follow = follow

    def get_id(self):
        return str(self.id)

    def get(user_id):
        return fonction_web.find_user(user_id)
# class Article(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(150), nullable=False)
#     content = db.Column(db.Text, nullable=False)
#     public = db.Column(db.Boolean, default=False)
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# class LoginForm(FlaskForm):
#     username = StringField('username', validators=[InputRequired(), Length(min=1, max=15)])
#     password = PasswordField('password', validators=[InputRequired(), Length(min=1, max=80)])
#     remember = BooleanField('Remember me')
#
# @login_manager.user_loader
# def load_user(user_id):
#     return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if fonction_web.connexion_web(username,password)==True :
            session['id_user']=username
            return redirect('/')




    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
def index():
    return render_template('index1.html')

# @app.route('/dashboard')
# @login_required
# def dashboard():
#     articles = Article.query.filter_by(user_id=current_user.id).all()
#     return render_template('dashboard.html', articles=articles)

@app.route('/public_articles')
def public_articles():
    user_id = session['id_user']
    docs = fonction_web.recherche_public_docs(user_id)
    contenue = fonction_web.find_contenue(docs)
    print(contenue)
    return render_template('public_articles.html', contenue=contenue)

@app.route('/perso')
def perso():
    user_id=session['id_user']
    docs=fonction_web.recherche_private_docs(user_id)
    contenue=fonction_web.find_contenue(docs)
    print(contenue)
    return render_template('perso.html',contenue=contenue)

@app.route('/download/<id_doc>')
def download_file(id_doc):
    pdf_output=fonction_web.generer_pdf(id_doc)
    return send_file(pdf_output, mimetype='application/pdf',as_attachment=False)

if __name__ == '__main__':
    app.run(debug=True)

