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
        with lock:
            tokens_list[id_user] = time.time()
            update.message.reply_text('Vous êtes onnecté')
    else:
        update.message.reply_text(f'Vous êtes déjà inscrit')


def start(update, context):
    update.message.reply_text("""
    Bienvenue sur SummBuddy. Je suis un bot qui vous permets de crée des notes à partir de textes, d'images, de messages audios et de vidéos.
    
    Pour pouvoir commancer à m'utiliser, il faut que tu t'enregistre en utilisant la commande /register. Les prochaines fois tu n'aura plus qu'à te connecter avec /connexion.
    
    Attention, ton ID Telegram et ton mot de passe te serviront aussi à te connecter sur le site web où tu retrouveras toutes tes notes.
    """)
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
        update.message.reply_text(f"Mot de passe changer pour : {new_mdp}")


def connexion(update, context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        update.message.reply_text('Vous êtes déjà connecté')
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
    /id => Affiche ton ID Telegram (si tu ne t'en souviens plus)
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
        tokens_list[id_user] = time.time()
        context.chat_data['grouped'] = False
        update.message.reply_text("Vous avez choisi d'envoyer un texte. Veuillez entrer le texte maintenant.")
        return TEXT_INPUT
    else:
        update.message.reply_text('Veuillez vous connecter')


def define_text(update, context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        text = update.message.text.replace('/send ', '')

        context.chat_data['text'] = text
        update.message.reply_text(f'Votre note actuelle est: {text}')

        tags = requete_GPT_tags(text)
        tags = tags.replace("'", ' ')
        context.chat_data['tags'] = tags
        context.chat_data['type'] = 'text'

        inline_keyboard = [[InlineKeyboardButton('Oui', callback_data='Oui'),
                            InlineKeyboardButton('Non', callback_data='Non')]]
        markup = InlineKeyboardMarkup(inline_keyboard)

        update.message.reply_text('Voulez-vous que la note soit résumée ?', reply_markup=markup)
        return CHOICE_RESUME
    else:
        update.message.reply_text('Veuillez vous connecter')
        return ConversationHandler.END


def send_audio(update, context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        tokens_list[id_user] = time.time()
        update.message.reply_text("Veuillez envoyer une note vocale")
        return VOICE_INPUT
    else:
        update.message.reply_text('Veuillez vous connecter')



def define_audio(update, context):
    id_user = update.effective_user.id
    if id_user in tokens_list.keys():
        file = context.bot.get_file(update.message.voice.file_id, timeout=30)

        audio = bytes(file.download_as_bytearray())

        client = speech.SpeechClient.from_service_account_file(GOOGLE_CLOUD_KEY_PATH)
        # noinspection PyTypeChecker
        con
    
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
    dispatcher.add_handler(CommandHandler('id', show_id))

    updater.start_polling()
    updater.idle()
