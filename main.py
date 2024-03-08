import time
import datetime
import telegram.ext
from telegram.ext import Filters, ConversationHandler, CommandHandler, MessageHandler, CallbackContext, Updater
from google.oauth2 import service_account
from google.cloud import speech,videointelligence,storage
import threading
import psycopg2
import openai
import bcrypt
from google.cloud import vision
from google.cloud.vision_v1 import types
import requests





def requete_GPT (texte):


    response = openai.chat.completions.create(
        model = "gpt-3.5-turbo",
        messages=[{"role": "user", "content": f'resume moi ce  texte : {texte}'}],
        max_tokens=300,
        temperature=1.2,
        stop=None
    )
    return response.choices[0].message.content


def requete_GPT_tags (texte):
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": f'donne moi 5 tags dans le format d une liste python [] pour ce texte : {texte}'}],
        max_tokens=300,
        temperature=1.2,
        stop=None
    )
    return response.choices[0].message.content





def register (update,context):
    id_user = update.effective_user.id
    search_query = f"SELECT * FROM users WHERE id_user = '{id_user}';"
    cursor.execute(search_query)
    results = cursor.fetchall()
    if not results:
        mdp = update.message.text.split()[1]
        print(mdp)
        bytes=mdp.encode('utf-8')
        salt=bcrypt.gensalt()
        hash=bcrypt.hashpw(bytes,salt)
        coded_mdp=hash.decode('utf-8')
        insert_query = f"INSERT INTO users (mdp, id_user) VALUES ('{coded_mdp}', '{id_user}');"
        cursor.execute(insert_query)
        connection.commit()
        update.message.reply_text(f'Bravo, vous êtes inscrit')
    else :
        update.message.reply_text(f'vous êtes déjà inscrit')

def start(update,context):
    update.message.reply_text('Training PFE 2023')
    id_user = update.effective_user.id

    update.message.reply_text(f'Votre ID : {id_user}')


def update_mdp(update,context):
    id_user = update.effective_user.id
    mdp = update.message.text.split()[1]
    new_mdp =update.message.text.split()[2]
    select_query = f"SELECT mdp FROM users WHERE id_user = '{id_user}';"
    cursor.execute(select_query)
    hash = cursor.fetchone()[0]
    hash=hash.encode('utf-8')
    userbytes=mdp.encode('utf-8')
    result=bcrypt.checkpw(userbytes,hash)
    if result :
        bytes = new_mdp.encode('utf-8')
        salt = bcrypt.gensalt()
        new_hash = bcrypt.hashpw(bytes, salt)
        coded_mdp = new_hash.decode('utf-8')
        update_query = f"UPDATE users SET mdp = '{coded_mdp}' WHERE id_user = '{id_user}';"
        cursor.execute(update_query)
        connection.commit()
        update.message.reply_text(f"mot de passe changer pour : {new_mdp}")






def connexion(update,context):
    id_user = update.effective_user.id
    recherche_private_docs(id_user)
    if id_user in tokens_list.keys():
        update.message.reply_text('vous êtes déjà connecté')
    else:
        mdp=update.message.text.strip('/connexion ')
        select_query = f"SELECT mdp FROM users WHERE id_user = '{id_user}';"
        cursor.execute(select_query)
        hash = cursor.fetchone()[0]
        hash = hash.encode('utf-8')

        userbytes = mdp.encode('utf-8')
        result = bcrypt.checkpw(userbytes, hash)
        if result==True:
            with lock:
                tokens_list[id_user]=time.time()
                print(tokens_list)
                update.message.reply_text('Connecté')


def check_connexion():
    user_to_disconnect = []
    while True:
        for id in user_to_disconnect:
                del tokens_list[id]
        user_to_disconnect=[]
        time.sleep(60)
        current_time = time.time()
        with lock:
            for id_user, last_action_time in tokens_list.items():
                time_difference = current_time - last_action_time
                if time_difference >= 1800:  # 30 minutes en secondes
                    user_to_disconnect.append(id_user)








def help(update,context):
    update.message.reply_text("""
    /start => Message au debut (obsolète mais ca existe quand même pour la premiere fois qu'on lance le bot)
    /help => Commande annexe
    /register => Permet de s'enregistrer dans la base en renseignant un mot de passe (/register mdp)
    /connexion => Permet de ce connecter en renseignant son mot de passe (/connexion mdp)
    /update_mdp => Permet de changer de mot de passe en renseignant l'ancien et le nouveau mot de passe (/update_mdp ancien_mdp nouveau_mdp)
    /send_text => Permet de lancer une procedure de résumer de texte.
    /send_audio => Permet de lancer une procedure de résumer de note vocale.
    """
                              )
def find_group(id_user):
    groups_in = []
    search_query = f"SELECT id,id_users FROM groupe;"
    cursor.execute(search_query)
    results = cursor.fetchall()
    for element in results:
        if id_user in eval(element[1]):
            groups_in.append(element[0])
    return groups_in


def send_text (update,context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        context.chat_data['grouped'] = False
        update.message.reply_text("Vous avez choisi d'envoyer un texte. Veuillez entrer le texte maintenant.")
        return TEXT_INPUT

def send_text_group (update,context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        group_id = update.message.text.strip('/send_text_group ')
        search_query = f"SELECT id_users FROM groupe WHERE id = {group_id};"
        cursor.execute(search_query)
        results = cursor.fetchall()
        ids=eval(results[0][0])
        if id_user in ids:
            context.chat_data['grouped'] = True
            context.chat_data['id_group'] = group_id
            update.message.reply_text("Vous avez choisi d'envoyer un texte. Veuillez entrer le texte maintenant.")
            return TEXT_INPUT
        else:
            update.message.reply_text('Vous ne faites pas partie de ce groupe')
            return ConversationHandler.END
def define_text(update,context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        tokens_list[id_user]=time.time()
        text=update.message.text.replace('/send ','')

        resume=requete_GPT(text)
        update.message.reply_text(resume)
        resume=resume.replace("'",' ')

        context.chat_data['text'] = resume

        tags=requete_GPT_tags(text)
        tags = tags.replace("'", ' ')
        context.chat_data['tags'] = tags
        context.chat_data['type'] = 'text'

        update.message.reply_text('Voulez-vous que la note soit publique ?')
        print(context.chat_data.get('tags', '[]'))
        return CHOICE_INPUT
    else:
        update.message.reply_text('Veuillez vous connecter')
        return ConversationHandler.END

    # noinspection PyUnreachableCode
def define_text_brute(update, context):
        id_user = update.effective_user.id
        if id_user in tokens_list.keys():
            tokens_list[id_user] = time.time()
            text = update.message.text.replace('/send ', '')

            context.chat_data['text'] = text

            tags = requete_GPT_tags(text)
            tags = tags.replace("'", ' ')
            context.chat_data['tags'] = tags
            context.chat_data['type'] = 'text_brute'

            update.message.reply_text('Voulez-vous que la note soit publique ?')
            print(context.chat_data.get('tags', '[]'))
            return CHOICE_RAW_INPUT
        else:
            update.message.reply_text('Veuillez vous connecter')
            return ConversationHandler.END



def send_audio(update,context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        update.message.reply_text("Veuillez envoyer une note vocale")
        return VOICE_INPUT

def send_audio_group(update,context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        group_id = update.message.text.strip('/send_audio_group ')
        search_query = f"SELECT id_users FROM groupe WHERE id = {group_id};"
        cursor.execute(search_query)
        results = cursor.fetchall()
        ids = eval(results[0][0])
        if id_user in ids:
            context.chat_data['grouped'] = True
            context.chat_data['id_group'] = group_id
            update.message.reply_text("Veuillez envoyer une note vocale")
            return VOICE_INPUT
        else:
            update.message.reply_text('Vous ne faites pas partie de ce groupe')
            return ConversationHandler.END


def define_audio(update,context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        tokens_list[id_user] = time.time()
        file = context.bot.get_file(update.message.voice.file_id,timeout=30)
        print('vocal recus')
        audio = bytes(file.download_as_bytearray())

        client = speech.SpeechClient.from_service_account_file(GOOGLE_CLOUD_KEY_PATH)
        # noinspection PyTypeChecker
        config = speech.RecognitionConfig(encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
                                          sample_rate_hertz=48000, language_code="fr-FR",
                                          enable_automatic_punctuation=True

        )

        audio=speech.RecognitionAudio(content=audio)
        response=client.recognize(config=config,audio=audio)

        for result in response.results:
            text=result.alternatives[0].transcript
            print("Transcription: {}".format(text))
            resume = requete_GPT(text)
            resume = resume.replace("'", ' ')
            context.chat_data['text'] = resume
            update.message.reply_text(resume)
            tags = requete_GPT_tags(text)
            tags = tags.replace("'", ' ')
            context.chat_data['tags'] = tags
            context.chat_data['type'] = 'audio'
            context.chat_data['grouped'] = False

        update.message.reply_text('Voulez-vous que la note soit publique ?')
        return CHOICE_INPUT
    else:
        update.message.reply_text('Veuillez vous connecter')
        return ConversationHandler.END

def send_pict(update,context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        update.message.reply_text("Veuillez envoyer une image/photo")
        return IMAGE_INPUT

def define_pict(update, context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        tokens_list[id_user] = time.time()
        # Configurez l'authentification en utilisant votre clé d'API
        client_options = {"api_endpoint": "eu-vision.googleapis.com"}

        client = vision.ImageAnnotatorClient(client_options=client_options).from_service_account_file(
            GOOGLE_CLOUD_KEY_PATH)
        # # Chargez l'image à partir de laquelle vous souhaitez détecter le texte
        image = context.bot.get_file(update.message.photo[-1].file_id)
        link = image['file_path']
        response = requests.get(link)
        image = types.Image(content=response.content)

        # Effectuez la demande de détection de texte
        response = client.text_detection(image=image)
        texts = response.text_annotations
        texte=texts[0].description
        context.chat_data['text'] = texte

        client = vision.ImageAnnotatorClient(client_options=client_options).from_service_account_file(GOOGLE_CLOUD_KEY_PATH)
        response = client.label_detection(image=image)
        texts = response.label_annotations
        tab_tags=[]
        for text in texts:
            tab_tags.append(text.description)

        tags2=requete_GPT_tags(texte)

        context.chat_data['type'] = 'image'
        context.chat_data['grouped'] = False
        print(tab_tags)
        print(tags2)
        try:
            tab_tags.extend(eval(tags2))
            context.chat_data['tags']=tab_tags
        except:
            print('erreur')
            context.chat_data['tags'] = tab_tags
        update.message.reply_text('Voulez-vous que la note soit publique ?')
        return CHOICE_INPUT_IMAGE
    else:
        update.message.reply_text('Veuillez vous connecter')
        return ConversationHandler.END

def send_video(update,context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        update.message.reply_text("Veuillez envoyer une vidéo")
        return VIDEO_INPUT
def define_video(update, context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        print('ok')
        context.chat_data['type'] = 'video'
        context.chat_data['grouped'] = False
        video = context.bot.get_file(update.message.video, timeout=30)
        video_url = video['file_path']
        video_content = requests.get(video_url).content

        client = storage.Client.from_service_account_json('our-ratio-415208-65186935a597.json')
        bucket = client.get_bucket('bucket-pfe-video')
        nom = 'video'
        blob = bucket.blob(nom)
        blob.upload_from_string(video_content, content_type='video/mp4')

        client_videointel = videointelligence.VideoIntelligenceServiceClient().from_service_account_file(
            GOOGLE_CLOUD_KEY_PATH)
        features = [videointelligence.Feature.SPEECH_TRANSCRIPTION]
        config = videointelligence.SpeechTranscriptionConfig(language_code="fr-FR", enable_automatic_punctuation=True)

        video_context = videointelligence.VideoContext(speech_transcription_config=config)

        operation = client_videointel.annotate_video(
            request={"features": features, "input_uri": f"gs://bucket-pfe-video/{nom}", "video_context": video_context}
        )
        result = operation.result(timeout=600)
        annotation_results = result.annotation_results[0]
        textes=[]
        for speech_transcription in annotation_results.speech_transcriptions:
            texte=speech_transcription.alternatives[0].transcript
            textes.append(texte)
        print('ok')
        client_videointel = videointelligence.VideoIntelligenceServiceClient().from_service_account_file(GOOGLE_CLOUD_KEY_PATH)
        features = [videointelligence.Feature.LABEL_DETECTION]
        mode = videointelligence.LabelDetectionMode.SHOT_AND_FRAME_MODE
        config = videointelligence.LabelDetectionConfig(label_detection_mode=mode)
        video_context = videointelligence.VideoContext(label_detection_config=config)

        operation = client_videointel.annotate_video(
            request={"features": features, "input_uri": f"gs://bucket-pfe-video/{nom}", "video_context": video_context}
        )

        result = operation.result(timeout=180)
        tab_labels = []
        segment_labels = result.annotation_results[0].segment_label_annotations
        for i, segment_label in enumerate(segment_labels):
            for i, segment in enumerate(segment_label.segments):
                confidence = segment.confidence
                tab_labels.append((segment_label.entity.description, confidence))
        tab_labels = sorted(tab_labels, key=lambda x: x[1], reverse=True)
        print(textes[0])

        context.chat_data['text'] = textes[0]
        tab_labels=tab_labels[:5]
        tags = [tup[0] for tup in tab_labels]
        print(tags)
        context.chat_data['tags'] = tags
        update.message.reply_text('Voulez-vous que la note soit publique ?')
        return CHOICE_INPUT_VIDEO

def is_public(update,context):
    choix=update.message.text
    if choix=='oui' or choix=="yes" or choix=='Oui' or choix=="Yes":
        context.chat_data['public'] = True
    else:
        context.chat_data['public'] = False

    tags=context.chat_data.get('tags', '[]')
    update.message.reply_text(f'Voici les tags actuel : {tags}')
    update.message.reply_text('Voulez-vous ajouter un autre tags ?')

    type=context.chat_data.get('type', 'Aucune donnée enregistré')
    if type=='text':
        return CHOICE_TAGS
    elif type=='audio':
        return CHOICE_TAGS_AUDIO
    elif type == 'image':
        return CHOICE_TAGS_IMAGE
    elif type == 'video':
        return CHOICE_TAGS_VIDEO
    elif type=='text_brute':
        return CHOICE_RAW_TAGS

def choose_add_tags(update,context):
    choix = update.message.text
    type = context.chat_data.get('type', 'Aucune donnée enregistré')
    if choix == 'oui' or choix == "yes" or choix == 'Oui' or choix == "Yes":
        update.message.reply_text('entré le tag a ajouté')
        if type == 'text':
            return ADD_TAGS
        elif type == 'audio':
            return ADD_TAGS_AUDIO
        elif type == 'image':
            return ADD_TAGS_IMAGE
        elif type == 'video':
            return ADD_TAGS_VIDEO
        elif type == 'text_brute':
            return ADD_RAW_TAGS
    else:
        update.message.reply_text('entré un titre')
        if type == 'text':
            return TITLE_INPUT
        elif type == 'audio':
            return TITLE_INPUT_AUDIO
        elif type == 'image':
            return TITLE_INPUT_IMAGE
        elif type == 'video':
            return TITLE_INPUT_VIDEO
        elif type == 'text_brute':
            return TITLE_RAW_INPUT


def add_tags (update,context):
    tags=context.chat_data.get('tags', 'Aucune donnée enregistré')
    try:
        try:
            tags=tags.replace('"', '')
        except:
            None
        tags=tags.replace('[','').replace(']','').split(', ')
    except:
        None
    type = context.chat_data.get('type', 'Aucune donnée enregistré')
    new_tag = update.message.text
    tags.append(new_tag)
    tags=str(tags)
    tags.replace("'",'"')
    context.chat_data['tags'] = tags
    update.message.reply_text(f'Voici les tags actuel : {tags}')
    update.message.reply_text('Voulez-vous ajouter un autre tags ?')

    if type == 'text':
        return CHOICE_TAGS
    elif type == 'audio':
        return CHOICE_TAGS_AUDIO
    elif type == 'image':
        return CHOICE_TAGS_IMAGE
    elif type == 'video':
        return CHOICE_TAGS_VIDEO
    elif type=='text_brute':
        return CHOICE_RAW_TAGS


def define_title(update,context):
    id_user = update.effective_user.id
    title=update.message.text
    context.user_data.clear()
    update.message.reply_text(f'Le titre du document est : {title}')
    text = context.chat_data.get('text', 'Aucun texte enregistré')
    tags = context.chat_data.get('tags', 'Aucun texte enregistré')
    tags=tags.replace("'",'')
    text=text.replace("'"," ").replace('\n',' ')
    type = context.chat_data.get('type', 'Aucune donnée enregistré')
    grouped=context.chat_data.get('grouped', False)
    public=context.chat_data.get('public',False)
    date=datetime.datetime.now()
    date = date.strftime("%Y-%m-%d %H:%M:%S")
    insert_query_doc = f"""INSERT INTO doc (titre, contenu, date_creation, tags, type, public, grouped_doc) values ('{title}','{text}','{date}','{tags}','{type}','{public}','{grouped }');"""
    cursor.execute(insert_query_doc)
    connection.commit()
    if grouped==True:
        id_group=context.chat_data.get('id_group', 'Aucune donnée enregistré')
        insert_query_doc = f"""INSERT INTO association (doc_id, groupe_id)
            SELECT
                (SELECT id_doc FROM doc WHERE contenu='{text}'),
                (SELECT id FROM Groupe WHERE id={id_group})"""
    else :
        insert_query_doc = f"""INSERT INTO association (doc_id, user_id)
                    SELECT
                        (SELECT id_doc FROM doc WHERE contenu='{text}'),
                        (SELECT id_user FROM users WHERE id_user='{id_user}')"""
    cursor.execute(insert_query_doc)
    connection.commit()
    context.chat_data.clear()
    return ConversationHandler.END

def create_group(update,context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        validate_ids = True
        tokens_list[id_user] = time.time()
        ids = update.message.text.replace('/create_group ', '').split()
        for i in range(len(ids)) :
            id=ids[i]
            id=int(id)
            ids[i]=id
            search_query = f"SELECT * FROM users WHERE id_user = '{id}';"
            cursor.execute(search_query)
            results = cursor.fetchall()
            if not results:
                update.message.reply_text(f"L'id : {id}, n'est pas valide'")
                validate_ids =False
        if validate_ids==True:
            ids.append(id_user)
            insert_query = f"INSERT INTO groupe (id_users,admin) VALUES ('{ids}','{id_user}');"
            cursor.execute(insert_query)
            connection.commit()

            search_query = f"SELECT id FROM groupe WHERE id_users = '{ids}';"
            cursor.execute(search_query)
            group_id = cursor.fetchall()

            update.message.reply_text(f"Le groupe a été crée avec succés, l'id du groupe est : {group_id}")

def add_user_group(update,context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        message =update.message.text.replace('/add_user_group ','').split()
        group_id=message[0]
        add_id=message[1]
        search_query = f"SELECT id,id_users,admin FROM groupe WHERE id = {group_id};"
        cursor.execute(search_query)
        results = cursor.fetchall()
        user_ids=eval(results[0][1])
        admin=results[0][2]
        print(admin)
        if id_user==int(admin)  and int(add_id) not in user_ids :
            user_ids.append(int(add_id))
            update_query = f"UPDATE groupe SET id_users = '{user_ids}' WHERE id = {group_id};"
            cursor.execute(update_query)
            connection.commit()
            update.message.reply_text(f'Vous avez ajouter le user : {add_id} dans le groupe {group_id}')
        else :
            update.message.reply_text(f"vous n'êtes pas admin du groupe {group_id} ou {add_id} en fait déjà partie")

def del_user_group (update, context) :
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        message = update.message.text.replace('/del_user_group ', '').split()
        group_id = message[0]
        del_id = int(message[1])
        search_query = f"SELECT id,id_users,admin FROM groupe WHERE id = {group_id};"
        cursor.execute(search_query)
        results = cursor.fetchall()
        user_ids = eval(results[0][1])
        admin = results[0][2]
        if id_user == int(admin) and del_id  in user_ids:
            user_ids.remove(del_id)
            update_query = f"UPDATE groupe SET id_users = '{user_ids}' WHERE id = {group_id};"
            cursor.execute(update_query)
            connection.commit()
            update.message.reply_text(f'Vous avez supprimer le user : {del_id} du groupe {group_id}')
        else:
            update.message.reply_text(f"vous n'êtes pas admin du groupe {group_id} ou {del_id} n'en fait pas partie")


def change_admin_group(update,context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        message = update.message.text.replace('/change_admin_group ', '').split()
        group_id = message[0]
        change_id = int(message[1])
        search_query = f"SELECT id,id_users,admin FROM groupe WHERE id = {group_id};"
        cursor.execute(search_query)
        results = cursor.fetchall()
        user_ids = eval(results[0][1])
        admin = results[0][2]
        if id_user == int(admin) and change_id in user_ids:
            update_query = f"UPDATE groupe SET admin = '{change_id}' WHERE id = {group_id};"
            cursor.execute(update_query)
            connection.commit()
            update.message.reply_text(f"Le nouvel admin du group {group_id} est l'utilisateur : {change_id}")
        else:
            update.message.reply_text(f"vous n'êtes pas admin du groupe {group_id} ou {change_id} n'en fait pas partie")

def check_groups(update,context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        groups_in=find_group(id_user)
        update.message.reply_text(f'vous faites partis des groupes suivants : {groups_in}')


def cancel (update,context) :
    context.chat_data.clear()
    return ConversationHandler.END


def follow(id_user,id_follow):
    query=f"SELECT * FROM users WHERE id_user = '{id_follow}' ;"
    cursor.execute(query)
    results = cursor.fetchall()
    if results :
        query=f"SELECT follow FROM users WHERE id_user = '{id_user}';"
        cursor.execute(query)
        results = cursor.fetchall()
        follows=eval(results[0][0])
        if id_follow not in follows :
            follows.append(id_follow)
            update_query=f"UPDATE users SET follow = '{follows}' WHERE id_user = '{id_user}';"
            cursor.execute(update_query)
            connection.commit()



def recherche_private_docs(id_user):
    docs=[]
    groups_in=find_group(id_user)
    query=f"SELECT  doc_id FROM association WHERE user_id = '{id_user}';"
    cursor.execute(query)
    results1 = cursor.fetchall()
    for elem in results1:
        docs.append(elem[0])
    for group_id in groups_in:
        query=f"SELECT doc_id FROM association WHERE groupe_id = '{group_id}';"
        cursor.execute(query)
        results2 = cursor.fetchall()
        for elem in results2:
            docs.append(elem[0])
    print(docs)


if __name__ == "__main__":
    db_config = {
        'host': '34.163.148.165',
        'user': 'postgres',
        'password': '{Y]EA:cZG=:?AD9-',
        'database': 'postgres',
        'port': '5432',  # Par défaut, le port de PostgreSQL est 5432
    }

    openai.api_key='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'

    try:
        connection = psycopg2.connect(**db_config)
        print('connected')
        cursor = connection.cursor()
    except:
        print('not connected')

    TEXT_INPUT,CHOICE_INPUT,CHOICE_TAGS,ADD_TAGS,TITLE_INPUT = range(5)
    TEXT_RAW_INPUT,CHOICE_RAW_INPUT,CHOICE_RAW_TAGS,ADD_RAW_TAGS,TITLE_RAW_INPUT = range(5)
    VOICE_INPUT,CHOICE_INPUT_AUDIO ,CHOICE_TAGS_AUDIO,ADD_TAGS_AUDIO,TITLE_INPUT_AUDIO = range(5)
    IMAGE_INPUT,CHOICE_INPUT_IMAGE ,CHOICE_TAGS_IMAGE,ADD_TAGS_IMAGE,TITLE_INPUT_IMAGE = range(5)
    VIDEO_INPUT,CHOICE_INPUT_VIDEO ,CHOICE_TAGS_VIDEO,ADD_TAGS_VIDEO,TITLE_INPUT_VIDEO = range(5)

    token='6649338214:AAGS4ag-NDDZWX6gM5rRPP7RCH00vOBTUjg'

    GOOGLE_CLOUD_KEY_PATH = "our-ratio-415208-65186935a597.json"

    tokens_list={}
    lock = threading.Lock()
    check_thread = threading.Thread(target=check_connexion)
    check_thread.start()

    updater = Updater(token,use_context=True)
    dispatcher=updater.dispatcher
    dispatcher.add_handler(CommandHandler('start',start))
    dispatcher.add_handler(CommandHandler('help',help))


    conversation_handler_text = ConversationHandler(
            entry_points=[CommandHandler('send_text', send_text)],
            states={
                TEXT_INPUT : [MessageHandler(Filters.text & ~Filters.command, define_text)],
                CHOICE_INPUT : [MessageHandler(Filters.text & ~Filters.command, is_public)],
                CHOICE_TAGS : [MessageHandler(Filters.text & ~Filters.command, choose_add_tags)],
                ADD_TAGS : [MessageHandler(Filters.text & ~Filters.command, add_tags)],
                TITLE_INPUT: [MessageHandler(Filters.text & ~Filters.command, define_title)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )

    dispatcher.add_handler(conversation_handler_text)
    conversation_handler_text_brute = ConversationHandler(
            entry_points=[CommandHandler('send_text_brute', send_text)],
            states={
                TEXT_RAW_INPUT : [MessageHandler(Filters.text & ~Filters.command, define_text_brute)],
                CHOICE_RAW_INPUT : [MessageHandler(Filters.text & ~Filters.command, is_public)],
                CHOICE_RAW_TAGS : [MessageHandler(Filters.text & ~Filters.command, choose_add_tags)],
                ADD_RAW_TAGS : [MessageHandler(Filters.text & ~Filters.command, add_tags)],
                TITLE_RAW_INPUT: [MessageHandler(Filters.text & ~Filters.command, define_title)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )

    dispatcher.add_handler(conversation_handler_text_brute)


    conversation_handler_image = ConversationHandler(
            entry_points=[CommandHandler('send_pict', send_pict)],
            states={
                IMAGE_INPUT : [MessageHandler(Filters.photo, define_pict)],
                CHOICE_INPUT_IMAGE : [MessageHandler(Filters.text & ~Filters.command, is_public)],
                CHOICE_TAGS_IMAGE : [MessageHandler(Filters.text & ~Filters.command, choose_add_tags)],
                ADD_TAGS_IMAGE : [MessageHandler(Filters.text & ~Filters.command, add_tags)],
                TITLE_INPUT_IMAGE: [MessageHandler(Filters.text & ~Filters.command, define_title)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )

    dispatcher.add_handler(conversation_handler_image)



    conversation_handler_video = ConversationHandler(
            entry_points=[CommandHandler('send_video', send_video)],
            states={
                VIDEO_INPUT : [MessageHandler(Filters.video, define_video)],
                CHOICE_INPUT_VIDEO : [MessageHandler(Filters.text & ~Filters.command, is_public)],
                CHOICE_TAGS_VIDEO : [MessageHandler(Filters.text & ~Filters.command, choose_add_tags)],
                ADD_TAGS_VIDEO : [MessageHandler(Filters.text & ~Filters.command, add_tags)],
                TITLE_INPUT_VIDEO: [MessageHandler(Filters.text & ~Filters.command, define_title)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )

    dispatcher.add_handler(conversation_handler_video)
    conversation_handler_text_group = ConversationHandler(
            entry_points=[CommandHandler('send_text_group', send_text_group)],
            states={
                TEXT_INPUT : [MessageHandler(Filters.text & ~Filters.command, define_text)],
                TITLE_INPUT: [MessageHandler(Filters.text & ~Filters.command, define_title)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )

    dispatcher.add_handler(conversation_handler_text_group)

    conversation_handler_voice=ConversationHandler(
        entry_points=[CommandHandler('send_audio',send_audio)],
        states={
            VOICE_INPUT : [MessageHandler(Filters.voice, define_audio)],
            CHOICE_INPUT_AUDIO : [MessageHandler(Filters.text & ~Filters.command, is_public)],
            CHOICE_TAGS_AUDIO :[MessageHandler(Filters.text & ~Filters.command, choose_add_tags)],
            ADD_TAGS_AUDIO :[MessageHandler(Filters.text & ~Filters.command, add_tags)],
            TITLE_INPUT_AUDIO : [MessageHandler(Filters.text & ~Filters.command, define_title)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conversation_handler_voice)

    conversation_handler_voice_group=ConversationHandler(
        entry_points=[CommandHandler('send_audio_group',send_audio_group)],
        states={
            VOICE_INPUT : [MessageHandler(Filters.voice, define_audio)],
            TITLE_INPUT_AUDIO : [MessageHandler(Filters.text & ~Filters.command, define_title)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conversation_handler_voice_group)

    dispatcher.add_handler(CommandHandler('connexion',connexion))
    dispatcher.add_handler(CommandHandler('register',register))
    dispatcher.add_handler(CommandHandler('update_mdp',update_mdp))
    dispatcher.add_handler(CommandHandler('create_group',create_group))
    dispatcher.add_handler(CommandHandler('check_groups',check_groups))
    dispatcher.add_handler(CommandHandler('add_user_group',add_user_group))
    dispatcher.add_handler(CommandHandler('del_user_group',del_user_group))
    dispatcher.add_handler(CommandHandler('change_admin_group',change_admin_group))
    dispatcher.add_handler(telegram.ext.MessageHandler(Filters.photo, send_pict))


    updater.start_polling()
    updater.idle()

