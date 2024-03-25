import time
import datetime
import telegram.ext
from telegram.ext import Filters, ConversationHandler, CommandHandler, MessageHandler, CallbackContext, Updater, CallbackQueryHandler
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from google.oauth2 import service_account
from google.cloud import speech, videointelligence, storage, secretmanager
import threading
import psycopg2
import openai
import bcrypt
from google.cloud import vision
from google.cloud.vision_v1 import types
import requests
import os


def requete_GPT(texte):
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": f'resume moi ce  texte : {texte}'}],
        max_tokens=300,
        temperature=1.2,
        stop=None
    )
    return response.choices[0].message.content


def requete_GPT_tags(texte):
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user",
                   "content": f'donne moi 5 tags dans le format d une liste python [] pour ce texte : {texte}'}],
        max_tokens=300,
        temperature=1.2,
        stop=None
    )
    return response.choices[0].message.content


def register(update, context):
    id_user = update.effective_user.id
    search_query = f"SELECT * FROM users WHERE id_user = '{id_user}';"
    cursor.execute(search_query)
    results = cursor.fetchall()
    if not results:
        mdp = update.message.text.split()[1]
        bytes = mdp.encode('utf-8')
        salt = bcrypt.gensalt()
        hash = bcrypt.hashpw(bytes, salt)
        coded_mdp = hash.decode('utf-8')
        insert_query = f"INSERT INTO users (mdp, id_user) VALUES ('{coded_mdp}', '{id_user}');"
        cursor.execute(insert_query)
        connection.commit()
        update.message.reply_text(f'Bravo, vous êtes inscrit')
    else:
        update.message.reply_text(f'vous êtes déjà inscrit')


def start(update, context):
    update.message.reply_text('Training PFE 2023')
    update.message.reply_text('Pour avoir des informations sur les commandes du bot, entrer: /help')
    id_user = update.effective_user.id

    update.message.reply_text(f'Votre ID : {id_user}')


def update_mdp(update, context):
    id_user = update.effective_user.id
    mdp = update.message.text.split()[1]
    new_mdp = update.message.text.split()[2]
    select_query = f"SELECT mdp FROM users WHERE id_user = '{id_user}';"
    cursor.execute(select_query)
    hash = cursor.fetchone()[0]
    hash = hash.encode('utf-8')
    userbytes = mdp.encode('utf-8')
    result = bcrypt.checkpw(userbytes, hash)
    if result:
        bytes = new_mdp.encode('utf-8')
        salt = bcrypt.gensalt()
        new_hash = bcrypt.hashpw(bytes, salt)
        coded_mdp = new_hash.decode('utf-8')
        update_query = f"UPDATE users SET mdp = '{coded_mdp}' WHERE id_user = '{id_user}';"
        cursor.execute(update_query)
        connection.commit()
        update.message.reply_text(f"mot de passe changer pour : {new_mdp}")


def connexion(update, context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        update.message.reply_text('vous êtes déjà connecté')
    else:
        mdp = update.message.text.strip('/connexion ')
        select_query = f"SELECT mdp FROM users WHERE id_user = '{id_user}';"
        cursor.execute(select_query)
        hash = cursor.fetchone()[0]
        hash = hash.encode('utf-8')

        userbytes = mdp.encode('utf-8')
        result = bcrypt.checkpw(userbytes, hash)
        if result == True:
            with lock:
                tokens_list[id_user] = time.time()
                update.message.reply_text('Connecté')


def check_connexion():
    user_to_disconnect = []
    while True:
        for id in user_to_disconnect:
            del tokens_list[id]
        user_to_disconnect = []
        time.sleep(60)
        current_time = time.time()
        with lock:
            for id_user, last_action_time in tokens_list.items():
                time_difference = current_time - last_action_time
                if time_difference >= 1800:  # 30 minutes en secondes
                    user_to_disconnect.append(id_user)


def help(update, context):
    update.message.reply_text("""
    /start => Message au debut (obsolète mais ca existe quand même pour la premiere fois qu'on lance le bot)
    /help => Commande annexe
    /register => Permet de s'enregistrer dans la base en renseignant un mot de passe (/register mdp)
    /connexion => Permet de ce connecter en renseignant son mot de passe (/connexion mdp)
    /update_mdp => Permet de changer de mot de passe en renseignant l'ancien et le nouveau mot de passe (/update_mdp ancien_mdp nouveau_mdp)
    /send_text => Permet de lancer une procedure de note textuel.
    /send_audio => Permet de lancer une procedure de note vocale.
    /send_video => Permet de lancer une procedure de note à partir d'une video.
    /send_pict => Permet de lancer une procedure de note à partir d'une image.
    /create_group => Permet de crée un groupe d'utilisateur pour partager des notes beaucoup plus facilement ensuite (/create_group id_user1 id_user2 ...)
    /check_groups => Permet d'afficher les groupes desquelles vous faites parties(/check_groups)
    /add_user_group => Permet d'ajouter un membre à un groupe dont vous êtes membres (/add_user_group group_id user_add_id)
    /del_user_group => Permet de supprimer un membre d'un groupe dont vous êtes l'admin(/del_user_group group_id user_del_id)
    /change_admin_group => Permet de transferer votre rôle d'admin d'un groupe à un autre user(/change_admin_group group_id new_admin_id)
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


def send_text(update, context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        context.chat_data['grouped'] = False
        update.message.reply_text("Vous avez choisi d'envoyer un texte. Veuillez entrer le texte maintenant.")
        return TEXT_INPUT


def define_text(update, context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        tokens_list[id_user] = time.time()
        text = update.message.text.replace('/send ', '')

        context.chat_data['text'] = text

        tags = requete_GPT_tags(text)
        tags = tags.replace("'", ' ')
        context.chat_data['tags'] = tags
        context.chat_data['type'] = 'text'

        inline_keyboard = [[InlineKeyboardButton('Oui', callback_data='Oui'),
                            InlineKeyboardButton('Non', callback_data='Non')]]
        markup = InlineKeyboardMarkup(inline_keyboard)

        update.message.reply_text('Voulez-vous que la note soit résumé ?', reply_markup=markup)
        return CHOICE_RESUME
    else:
        update.message.reply_text('Veuillez vous connecter')
        return ConversationHandler.END


def send_audio(update, context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        update.message.reply_text("Veuillez envoyer une note vocale")
        return VOICE_INPUT


def define_audio(update, context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        tokens_list[id_user] = time.time()
        file = context.bot.get_file(update.message.voice.file_id, timeout=30)

        audio = bytes(file.download_as_bytearray())

        client = speech.SpeechClient.from_service_account_file(GOOGLE_CLOUD_KEY_PATH)
        # noinspection PyTypeChecker
        config = speech.RecognitionConfig(encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
                                          sample_rate_hertz=48000, language_code="fr-FR",
                                          enable_automatic_punctuation=True

                                          )

        audio = speech.RecognitionAudio(content=audio)
        response = client.recognize(config=config, audio=audio)

        for result in response.results:
            text = result.alternatives[0].transcript

            context.chat_data['text'] = text

            tags = requete_GPT_tags(text)
            tags = tags.replace("'", ' ')
            context.chat_data['tags'] = tags
            context.chat_data['type'] = 'audio'
            context.chat_data['grouped'] = False

        inline_keyboard = [[InlineKeyboardButton('Oui', callback_data='Oui'),
                            InlineKeyboardButton('Non', callback_data='Non')]]
        markup = InlineKeyboardMarkup(inline_keyboard)

        update.message.reply_text('Voulez-vous que la note soit résumé ?', reply_markup=markup)
        return CHOICE_RESUME_AUDIO
    else:
        update.message.reply_text('Veuillez vous connecter')
        return ConversationHandler.END


def send_pict(update, context):
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
        texte = texts[0].description
        context.chat_data['text'] = texte

        client = vision.ImageAnnotatorClient(client_options=client_options).from_service_account_file(
            GOOGLE_CLOUD_KEY_PATH)
        response = client.label_detection(image=image)
        texts = response.label_annotations
        tab_tags = []
        for text in texts:
            tab_tags.append(text.description)

        tags2 = requete_GPT_tags(texte)

        context.chat_data['type'] = 'image'
        context.chat_data['grouped'] = False
        try:
            tab_tags.extend(eval(tags2))
            context.chat_data['tags'] = tab_tags
        except:
            context.chat_data['tags'] = tab_tags
        inline_keyboard = [[InlineKeyboardButton('Oui', callback_data='Oui'),
                            InlineKeyboardButton('Non', callback_data='Non')]]
        markup = InlineKeyboardMarkup(inline_keyboard)

        update.message.reply_text('Voulez-vous que la note soit résumé ?', reply_markup=markup)
        return CHOICE_RESUME_IMAGE
    else:
        update.message.reply_text('Veuillez vous connecter')
        return ConversationHandler.END


def send_video(update, context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        update.message.reply_text("Veuillez envoyer une vidéo")
        return VIDEO_INPUT


def define_video(update, context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        context.chat_data['type'] = 'video'
        context.chat_data['grouped'] = False
        video = context.bot.get_file(update.message.video, timeout=30)
        video_url = video['file_path']
        video_content = requests.get(video_url).content

        client = storage.Client.from_service_account_json(GOOGLE_CLOUD_KEY_PATH)
        bucket = client.get_bucket('bucket-pfe-video')
        nom = f'video{id_user}'
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
        textes = []
        for speech_transcription in annotation_results.speech_transcriptions:
            texte = speech_transcription.alternatives[0].transcript
            textes.append(texte)
        client_videointel = videointelligence.VideoIntelligenceServiceClient().from_service_account_file(
            GOOGLE_CLOUD_KEY_PATH)
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

        context.chat_data['text'] = textes[0]
        tab_labels = tab_labels[:5]
        tags = [tup[0] for tup in tab_labels]
        context.chat_data['tags'] = tags
        inline_keyboard = [[InlineKeyboardButton('Oui', callback_data='Oui'),
                            InlineKeyboardButton('Non', callback_data='Non')]]
        markup = InlineKeyboardMarkup(inline_keyboard)

        update.message.reply_text('Voulez-vous que la note soit résumé ?', reply_markup=markup)
        return CHOICE_RESUME_VIDEO


def do_resume(update, context):
    query = update.callback_query
    choix = query.data
    if choix == 'Oui':
        text = context.chat_data.get('text', None)
        resume = requete_GPT(text)
        resume = resume.replace("'", ' ')
        context.chat_data['text'] = resume
        query.edit_message_text(text=f"Voici la note résumer : {resume}")

    inline_keyboard = [[InlineKeyboardButton('Note de groupe', callback_data='Groupe'),
                        InlineKeyboardButton('Note personelle', callback_data='Personelle')]]
    markup = InlineKeyboardMarkup(inline_keyboard)

    query.edit_message_text('Voulez-vous que la note soit une note de groupe ou une note personnelle ?',
                            reply_markup=markup)
    type = context.chat_data.get('type', None)
    if type == 'text':
        return ISGROUP_INPUT
    elif type == 'audio':
        return ISGROUP_INPUT_AUDIO
    elif type == 'image':
        return ISGROUP_INPUT_IMAGE
    elif type == 'video':
        return ISGROUP_INPUT_VIDEO


def is_group(update, context):
    query = update.callback_query
    choix = query.data
    type = context.chat_data.get('type', None)
    if choix == 'Groupe':
        id_user = update.effective_user.id
        groups_in = find_group(id_user)

        buttons_line = []
        line_width = 2
        for i in range(0, len(groups_in), line_width):
            ligne = []
            for valeur in groups_in[i:i + line_width]:
                ligne.append(InlineKeyboardButton(valeur,
                                                  callback_data=valeur))  # Créer un bouton avec la valeur et son callback_data
            buttons_line.append(ligne)

        markup = InlineKeyboardMarkup(buttons_line)
        query.edit_message_text("Quelle est l'id du groupe ?", reply_markup=markup)

        if type == 'text':
            return GROUP_INPUT
        elif type == 'audio':
            return GROUP_INPUT_AUDIO
        elif type == 'image':
            return GROUP_INPUT_IMAGE
        elif type == 'video':
            return GROUP_INPUT_VIDEO

    else:
        inline_keyboard = [[InlineKeyboardButton('Oui', callback_data='Oui'),
                            InlineKeyboardButton('Non', callback_data='Non')]]
        markup = InlineKeyboardMarkup(inline_keyboard)

        query.edit_message_text('Voulez vous que la note soit publique ?', reply_markup=markup)
        if type == 'text':
            return CHOICE_INPUT
        elif type == 'audio':
            return CHOICE_INPUT_AUDIO
        elif type == 'image':
            return CHOICE_INPUT_IMAGE
        elif type == 'video':
            return CHOICE_INPUT_VIDEO


def id_group(update, context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        query = update.callback_query
        group_id = query.data
        search_query = f"SELECT id_users FROM groupe WHERE id = {group_id};"
        cursor.execute(search_query)
        results = cursor.fetchall()
        ids = eval(results[0][0])
        if id_user in ids:
            context.chat_data['grouped'] = True
            context.chat_data['id_group'] = group_id
            tags = context.chat_data.get('tags', '[]')
            query.edit_message_text(f'Voici les tags actuel : {tags}')
            inline_keyboard = [[InlineKeyboardButton('Oui', callback_data='Oui'),
                                InlineKeyboardButton('Non', callback_data='Non')]]
            markup = InlineKeyboardMarkup(inline_keyboard)
            query.message.reply_text('Voulez-vous ajouter un autre tags ?', reply_markup=markup)
            type = context.chat_data.get('type', 'Aucune donnée enregistré')
            if type == 'text':
                return CHOICE_TAGS
            elif type == 'audio':
                return CHOICE_TAGS_AUDIO
            elif type == 'image':
                return CHOICE_TAGS_IMAGE
            elif type == 'video':
                return CHOICE_TAGS_VIDEO
        else:
            query.message.reply_text('Vous ne faites pas partie de ce groupe')


def is_public(update, context):
    query = update.callback_query
    choix = query.data
    if choix == 'Oui':
        context.chat_data['public'] = True
    else:
        context.chat_data['public'] = False

    tags = context.chat_data.get('tags', '[]')
    query.edit_message_text(f'Voici les tags actuel : {tags}')
    inline_keyboard = [[InlineKeyboardButton('Oui', callback_data='Oui'),
                        InlineKeyboardButton('Non', callback_data='Non')]]
    markup = InlineKeyboardMarkup(inline_keyboard)

    query.message.reply_text('Voulez-vous ajouter un autre tags ?', reply_markup=markup)

    type = context.chat_data.get('type', 'Aucune donnée enregistré')
    if type == 'text':
        return CHOICE_TAGS
    elif type == 'audio':
        return CHOICE_TAGS_AUDIO
    elif type == 'image':
        return CHOICE_TAGS_IMAGE
    elif type == 'video':
        return CHOICE_TAGS_VIDEO


def choose_add_tags(update, context):
    query = update.callback_query
    choix = query.data
    type = context.chat_data.get('type', 'Aucune donnée enregistré')
    if choix == 'Oui':
        query.answer()
        query.edit_message_text(text=f"entré le tag a ajouté")
        if type == 'text':
            return ADD_TAGS
        elif type == 'audio':
            return ADD_TAGS_AUDIO
        elif type == 'image':
            return ADD_TAGS_IMAGE
        elif type == 'video':
            return ADD_TAGS_VIDEO

    else:
        query.edit_message_text(text=f"entrer un titre")
        if type == 'text':
            return TITLE_INPUT
        elif type == 'audio':
            return TITLE_INPUT_AUDIO
        elif type == 'image':
            return TITLE_INPUT_IMAGE
        elif type == 'video':
            return TITLE_INPUT_VIDEO


def add_tags(update, context):
    tags = context.chat_data.get('tags', 'Aucune donnée enregistré')
    try:
        try:
            tags = tags.replace('"', '')
        except:
            None
        tags = tags.replace('[', '').replace(']', '').split(', ')
    except:
        None
    type = context.chat_data.get('type', 'Aucune donnée enregistré')
    new_tag = update.message.text
    tags.append(new_tag)
    tags = str(tags)
    tags.replace("'", '"')
    context.chat_data['tags'] = tags
    update.message.reply_text(f'Voici les tags actuel : {tags}')
    inline_keyboard = [[InlineKeyboardButton('Oui', callback_data='Oui'),
                        InlineKeyboardButton('Non', callback_data='Non')]]
    markup = InlineKeyboardMarkup(inline_keyboard)

    update.message.reply_text('Voulez-vous ajouter un autre tags ?', reply_markup=markup)

    if type == 'text':
        return CHOICE_TAGS
    elif type == 'audio':
        return CHOICE_TAGS_AUDIO
    elif type == 'image':
        return CHOICE_TAGS_IMAGE
    elif type == 'video':
        return CHOICE_TAGS_VIDEO


def define_title(update, context):
    id_user = update.effective_user.id
    title = update.message.text
    context.user_data.clear()
    update.message.reply_text(f'Le titre du document est : {title}')
    text = context.chat_data.get('text', 'Aucun texte enregistré')
    tags = context.chat_data.get('tags', 'Aucun texte enregistré')
    tags = tags.replace("'", '')
    text = text.replace("'", " ").replace('\n', ' ')
    type = context.chat_data.get('type', 'Aucune donnée enregistré')
    grouped = context.chat_data.get('grouped', False)
    public = context.chat_data.get('public', False)
    date = datetime.datetime.now()
    date = date.strftime("%Y-%m-%d %H:%M:%S")
    insert_query_doc = f"""INSERT INTO doc (titre, contenu, date_creation, tags, type, public, grouped_doc) values ('{title}','{text}','{date}','{tags}','{type}','{public}','{grouped}');"""
    cursor.execute(insert_query_doc)
    connection.commit()
    if grouped == True:
        id_group = context.chat_data.get('id_group', 'Aucune donnée enregistré')
        insert_query_doc = f"""INSERT INTO association (doc_id, groupe_id)
            SELECT
                (SELECT id_doc FROM doc WHERE contenu='{text}'),
                (SELECT id FROM Groupe WHERE id={id_group})"""
    else:
        insert_query_doc = f"""INSERT INTO association (doc_id, user_id)
                    SELECT
                        (SELECT id_doc FROM doc WHERE contenu='{text}'),
                        (SELECT id_user FROM users WHERE id_user='{id_user}')"""
    cursor.execute(insert_query_doc)
    connection.commit()
    context.chat_data.clear()
    return ConversationHandler.END


def create_group(update, context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        validate_ids = True
        tokens_list[id_user] = time.time()
        ids = update.message.text.replace('/create_group ', '').split()
        for i in range(len(ids)):
            id = ids[i]
            id = int(id)
            ids[i] = id
            search_query = f"SELECT * FROM users WHERE id_user = '{id}';"
            cursor.execute(search_query)
            results = cursor.fetchall()
            if not results:
                update.message.reply_text(f"L'id : {id}, n'est pas valide'")
                validate_ids = False
        if validate_ids == True:
            ids.append(id_user)
            insert_query = f"INSERT INTO groupe (id_users,admin) VALUES ('{ids}','{id_user}');"
            cursor.execute(insert_query)
            connection.commit()

            search_query = f"SELECT id FROM groupe WHERE id_users = '{ids}';"
            cursor.execute(search_query)
            group_id = cursor.fetchall()

            update.message.reply_text(f"Le groupe a été crée avec succés, l'id du groupe est : {group_id}")


def add_user_group(update, context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        message = update.message.text.replace('/add_user_group ', '').split()
        group_id = message[0]
        add_id = message[1]
        search_query = f"SELECT id,id_users,admin FROM groupe WHERE id = {group_id};"
        cursor.execute(search_query)
        results = cursor.fetchall()
        user_ids = eval(results[0][1])
        admin = results[0][2]
        if id_user == int(admin) and int(add_id) not in user_ids:
            user_ids.append(int(add_id))
            update_query = f"UPDATE groupe SET id_users = '{user_ids}' WHERE id = {group_id};"
            cursor.execute(update_query)
            connection.commit()
            update.message.reply_text(f'Vous avez ajouter le user : {add_id} dans le groupe {group_id}')
        else:
            update.message.reply_text(f"vous n'êtes pas admin du groupe {group_id} ou {add_id} en fait déjà partie")


def del_user_group(update, context):
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
        if id_user == int(admin) and del_id in user_ids:
            user_ids.remove(del_id)
            update_query = f"UPDATE groupe SET id_users = '{user_ids}' WHERE id = {group_id};"
            cursor.execute(update_query)
            connection.commit()
            update.message.reply_text(f'Vous avez supprimer le user : {del_id} du groupe {group_id}')
        else:
            update.message.reply_text(f"vous n'êtes pas admin du groupe {group_id} ou {del_id} n'en fait pas partie")


def change_admin_group(update, context):
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


def check_groups(update, context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        groups_in = find_group(id_user)
        update.message.reply_text(f'vous faites partis des groupes suivants : {groups_in}')


def cancel(update, context):
    context.chat_data.clear()
    return ConversationHandler.END


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
    return docs


def find_contenue(docs):
    tab_contenue = []
    for id in docs:
        query = f"SELECT * FROM doc WHERE id_doc='{id}'"
        cursor.execute(query)
        contenue = cursor.fetchall()[0]
        tab_contenue.append(contenue)

def recup_secret(secret_name):
    project_id = "our-ratio-415208"

    secret_id = secret_name

    client = secretmanager.SecretManagerServiceClient()

    secret_path = f"projects/{project_id}/secrets/{secret_id}/versions/latest"

    response = client.access_secret_version(request={"name": secret_path})
    return response.payload.data.decode("UTF-8")


if __name__ == "__main__":

    openai_api =recup_secret('OPENAI_API_KEY')
    mdp_bdd =recup_secret('MDP_BDD')
    token_telegram =recup_secret('TELEGRAM_TOKEN')

    connected=False
    db_config = {
        'host':'34.163.148.165',
        'user': 'postgres',
        'password': mdp_bdd,
        'database': 'postgres',
        'port': '5432',  # Par défaut, le port de PostgreSQL est 5432
    }

    openai.api_key = openai_api
    while connected==False:
        time.sleep(5)
        try:
            connection = psycopg2.connect(**db_config)
            print('connected')
            cursor = connection.cursor()
            connected=True
        except:
            print('not connected')

    TEXT_INPUT, CHOICE_RESUME, ISGROUP_INPUT, GROUP_INPUT, CHOICE_INPUT, CHOICE_TAGS, ADD_TAGS, TITLE_INPUT = range(8)
    VOICE_INPUT, CHOICE_RESUME_AUDIO, ISGROUP_INPUT_AUDIO, GROUP_INPUT_AUDIO, CHOICE_INPUT_AUDIO, CHOICE_TAGS_AUDIO, ADD_TAGS_AUDIO, TITLE_INPUT_AUDIO = range(
        8)
    IMAGE_INPUT, CHOICE_RESUME_IMAGE, ISGROUP_INPUT_IMAGE, GROUP_INPUT_IMAGE, CHOICE_INPUT_IMAGE, CHOICE_TAGS_IMAGE, ADD_TAGS_IMAGE, TITLE_INPUT_IMAGE = range(
        8)
    VIDEO_INPUT, CHOICE_RESUME_VIDEO, ISGROUP_INPUT_VIDEO, GROUP_INPUT_VIDEO, CHOICE_INPUT_VIDEO, CHOICE_TAGS_VIDEO, ADD_TAGS_VIDEO, TITLE_INPUT_VIDEO = range(
        8)




    GOOGLE_CLOUD_KEY_PATH = "our-ratio-415208-75a140e48770.json"

    tokens_list = {}
    lock = threading.Lock()
    check_thread = threading.Thread(target=check_connexion)
    check_thread.start()

    updater = Updater(token_telegram, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help))

    conversation_handler_text = ConversationHandler(
        entry_points=[CommandHandler('send_text', send_text)],
        states={
            TEXT_INPUT: [MessageHandler(Filters.text & ~Filters.command, define_text)],
            CHOICE_RESUME: [CallbackQueryHandler(do_resume)],
            ISGROUP_INPUT: [CallbackQueryHandler(is_group)],
            GROUP_INPUT: [CallbackQueryHandler(id_group)],
            CHOICE_INPUT: [CallbackQueryHandler(is_public)],
            CHOICE_TAGS: [CallbackQueryHandler(choose_add_tags)],
            ADD_TAGS: [MessageHandler(Filters.text & ~Filters.command, add_tags)],
            TITLE_INPUT: [MessageHandler(Filters.text & ~Filters.command, define_title)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conversation_handler_text)

    conversation_handler_image = ConversationHandler(
        entry_points=[CommandHandler('send_pict', send_pict)],
        states={
            IMAGE_INPUT: [MessageHandler(Filters.photo, define_pict)],
            CHOICE_RESUME_IMAGE: [CallbackQueryHandler(do_resume)],
            ISGROUP_INPUT_IMAGE: [CallbackQueryHandler(is_group)],
            GROUP_INPUT_IMAGE: [CallbackQueryHandler(id_group)],
            CHOICE_INPUT_IMAGE: [CallbackQueryHandler(is_public)],
            CHOICE_TAGS_IMAGE: [CallbackQueryHandler(choose_add_tags)],
            ADD_TAGS_IMAGE: [MessageHandler(Filters.text & ~Filters.command, add_tags)],
            TITLE_INPUT_IMAGE: [MessageHandler(Filters.text & ~Filters.command, define_title)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conversation_handler_image)

    conversation_handler_video = ConversationHandler(
        entry_points=[CommandHandler('send_video', send_video)],
        states={
            VIDEO_INPUT: [MessageHandler(Filters.video, define_video)],
            CHOICE_RESUME_VIDEO: [CallbackQueryHandler(do_resume)],
            ISGROUP_INPUT_VIDEO: [CallbackQueryHandler(is_group)],
            GROUP_INPUT_VIDEO: [CallbackQueryHandler(id_group)],
            CHOICE_INPUT_VIDEO: [CallbackQueryHandler(is_public)],
            CHOICE_TAGS_VIDEO: [CallbackQueryHandler(choose_add_tags)],
            ADD_TAGS_VIDEO: [MessageHandler(Filters.text & ~Filters.command, add_tags)],
            TITLE_INPUT_VIDEO: [MessageHandler(Filters.text & ~Filters.command, define_title)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conversation_handler_video)

    conversation_handler_voice = ConversationHandler(
        entry_points=[CommandHandler('send_audio', send_audio)],
        states={
            VOICE_INPUT: [MessageHandler(Filters.voice, define_audio)],
            CHOICE_RESUME_AUDIO: [CallbackQueryHandler(do_resume)],
            ISGROUP_INPUT_AUDIO: [CallbackQueryHandler(is_group)],
            GROUP_INPUT_AUDIO: [CallbackQueryHandler(id_group)],
            CHOICE_INPUT_AUDIO: [CallbackQueryHandler(is_public)],
            CHOICE_TAGS_AUDIO: [CallbackQueryHandler(choose_add_tags)],
            ADD_TAGS_AUDIO: [MessageHandler(Filters.text & ~Filters.command, add_tags)],
            TITLE_INPUT_AUDIO: [MessageHandler(Filters.text & ~Filters.command, define_title)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conversation_handler_voice)

    dispatcher.add_handler(CommandHandler('connexion', connexion))
    dispatcher.add_handler(CommandHandler('register', register))
    dispatcher.add_handler(CommandHandler('update_mdp', update_mdp))
    dispatcher.add_handler(CommandHandler('create_group', create_group))
    dispatcher.add_handler(CommandHandler('check_groups', check_groups))
    dispatcher.add_handler(CommandHandler('add_user_group', add_user_group))
    dispatcher.add_handler(CommandHandler('del_user_group', del_user_group))
    dispatcher.add_handler(CommandHandler('change_admin_group', change_admin_group))

    updater.start_polling()
    updater.idle()
