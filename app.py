from flask import Flask, session, render_template, redirect, url_for, request, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import fonction_web


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'




@app.route('/')
def index():
    if 'id_user' not in session:
        return redirect(url_for('login'))
    else:
        return render_template('index1.html')

@app.route('/follow_form', methods=['POST'])
def follow_form():
    id_user=session['id_user']
    user_input = request.form['follow_id']
    if user_input!="":
        test=fonction_web.follow(id_user,user_input)

    if test==True:
        print(f'{user_input} est maintenant follow')
    else:
        print("erreur")
    return redirect('/')



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
def logout():
    session.pop("id_user", None)
    return redirect('/login')



@app.route('/public_articles')
def public_articles():
    user_id = session['id_user']
    docs, type = fonction_web.recherche_public_docs(user_id)
    contenue = fonction_web.find_contenue(docs,type)
    return render_template('public_articles.html', contenue=contenue)
@app.route('/publique_filter_form', methods=['POST'])
def publique_filter_form():
    user_id = session['id_user']
    docs, type = fonction_web.recherche_public_docs(user_id)

    user_input_titre = request.form['title']
    user_input_tags = request.form['tags']
    user_input_date = request.form['date']

    if user_input_titre !="":
        docs=fonction_web.filtre_titre(docs,user_input_titre)
    if user_input_tags != "" :
        docs = fonction_web.filtre_tag(docs, user_input_tags)

    contenue=fonction_web.find_contenue(docs,type)
    return render_template('public_articles.html', contenue=contenue)

@app.route('/perso')
def perso():
    user_id=session['id_user']
    docs,type=fonction_web.recherche_private_docs(user_id)
    contenue=fonction_web.find_contenue(docs,type)
    return render_template('perso.html',contenue=contenue)

@app.route('/private_filter_form', methods=['POST'])
def private_filter_form():
    user_id = session['id_user']
    docs, type = fonction_web.recherche_private_docs(user_id)

    user_input_titre = request.form['title']
    user_input_tags = request.form['tags']
    user_input_date = request.form['date']
    print(f'Title : {user_input_titre}')
    print(f'Tag : {user_input_tags}')
    print(f'Date : {user_input_date}')
    if user_input_titre !="":
        docs=fonction_web.filtre_titre(docs,user_input_titre)
    if user_input_tags != "" :
        docs = fonction_web.filtre_tag(docs, user_input_tags)
    if user_input_date != "":
        docs=fonction_web.filtre_date(docs,user_input_date)
    contenue=fonction_web.find_contenue(docs,type)
    return render_template('perso.html',contenue=contenue)



@app.route('/download/<id_doc>')
def download_file(id_doc):
    pdf_output=fonction_web.generer_pdf(id_doc)
    return send_file(pdf_output, mimetype='application/pdf',as_attachment=False)

if __name__ == '__main__':
    app.run(debug=True)