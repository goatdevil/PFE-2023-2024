import bcrypt
import psycopg2
from fpdf import FPDF
from io import BytesIO


def find_group(id_user):
    groups_in = []
    search_query = f"SELECT id,id_users FROM groupe;"
    cursor.execute(search_query)
    results = cursor.fetchall()
    for element in results:
        if id_user in eval(element[1]):
            groups_in.append(element[0])
    return groups_in

def follow(id_user, id_follow):
    query = f"SELECT * FROM users WHERE id_user = '{id_follow}' ;"
    cursor.execute(query)
    results = cursor.fetchall()
    if results:
        query = f"SELECT follow FROM users WHERE id_user = '{id_user}';"
        cursor.execute(query)
        results = cursor.fetchall()
        follows = eval(results[0][0])
        if id_follow not in follows:
            follows.append(id_follow)
            update_query = f"UPDATE users SET follow = '{follows}' WHERE id_user = '{id_user}';"
            cursor.execute(update_query)
            connection.commit()


def recherche_private_docs(id_user):
    docs = []
    groups_in = find_group(id_user)
    query = f"SELECT  doc_id FROM association WHERE user_id = '{id_user}';"
    cursor.execute(query)
    results1 = cursor.fetchall()
    for elem in results1:
        docs.append(elem[0])
    for group_id in groups_in:
        query = f"SELECT doc_id FROM association WHERE groupe_id = '{group_id}';"
        cursor.execute(query)
        results2 = cursor.fetchall()
        for elem in results2:
            docs.append(elem[0])
    #docs = sorted(docs, key=lambda x: x[3])
    return docs


def recherche_public_docs(id_user):
    docs = []
    query = f"SELECT follow FROM users WHERE id_user = '{id_user}'"
    cursor.execute(query)
    follows = cursor.fetchall()
    follows = eval(follows[0][0])
    query = f"SELECT doc_id, user_id FROM association;"
    cursor.execute(query)
    response = cursor.fetchall()
    for elem in response:
        if elem[1] != None:
            if int(elem[1]) in follows:
                docs.append(elem[0])
    for id_doc in docs:
        query = f"SELECT public FROM doc WHERE id_doc='{id_doc}';"
        cursor.execute(query)
        public = cursor.fetchall()[0][0]
        if public == False:
            docs.remove(id_doc)
    #docs=sorted(docs, key=lambda x: x[3])
    return docs


def find_contenue(docs):
    tab_contenue = []
    for id in docs:
        query = f"SELECT * FROM doc WHERE id_doc='{id}'"
        cursor.execute(query)
        contenue = cursor.fetchall()[0]
        tab_contenue.append(contenue)
    return tab_contenue

def find_user(id_user):
    select_query = f"SELECT * FROM users WHERE id_user = '{id_user}';"
    cursor.execute(select_query)
    user = cursor.fetchone()[0]
    return user
def connexion_web(id_user,mdp):
    select_query = f"SELECT mdp FROM users WHERE id_user = '{id_user}';"
    cursor.execute(select_query)
    hash = cursor.fetchone()[0]
    hash = hash.encode('utf-8')

    userbytes = mdp.encode('utf-8')
    result = bcrypt.checkpw(userbytes, hash)
    if result == True:
        return True
    else:
        return False
        #passer le user_id en variable "d'environment" + redirection page menu

#def mdp_oublié(id_user):

def recherche_tag(docs,tag):
    tab_id = []
    for id in docs:
        query = f"SELECT * FROM doc WHERE id_doc='{id}'"
        cursor.execute(query)
        contenue = cursor.fetchall()[0]
        if tag in eval(contenue[4]):
            tab_id.append(id)
    print(tab_id)

def recherche_titre(docs,titre):
    tab_id = []
    for id in docs:
        query = f"SELECT * FROM doc WHERE id_doc='{id}'"
        cursor.execute(query)
        contenue = cursor.fetchall()[0]
        if titre == contenue[1]:
            tab_id.append(id)
    print(tab_id)


def recherche_groupeid(groupe_id):
    docs=[]
    query = f"SELECT doc_id FROM association WHERE groupe_id = '{groupe_id}';"
    cursor.execute(query)
    results2 = cursor.fetchall()
    for elem in results2:
        docs.append(elem[0])
def generer_pdf(id_doc):
    query=f"SELECT contenu FROM doc WHERE id_doc= '{id_doc}' ;"
    cursor.execute(query)
    text_article=cursor.fetchall()[0][0]

    # Créer un objet PDF
    pdf = FPDF()
    # Ajouter une page
    pdf.add_page()
    # Définir la police et la taille du texte
    pdf.set_font("Arial", size=12)
    # Ajouter du texte
    text = text_article
    pdf.multi_cell(0, 10, text)

    # Créer un flux de données en mémoire
    pdf_output = BytesIO()
    pdf_output.write(pdf.output(dest='S').encode('latin1'))

    # Définir la position du curseur au début du flux
    pdf_output.seek(0)
    return pdf_output



db_config = {
        'host': '34.163.148.165',
        'user': 'postgres',
        'password': '{Y]EA:cZG=:?AD9-',
        'database': 'postgres',
        'port': '5432',  # Par défaut, le port de PostgreSQL est 5432
    }
try:
    connection = psycopg2.connect(**db_config)
    print('connected')
    cursor = connection.cursor()
except:
    print('not connected')