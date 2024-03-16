
hello

import time

import telegram.ext
from telegram.ext import Filters, ConversationHandler, CommandHandler, MessageHandler, CallbackContext, Updater
from google.oauth2 import service_account
from google.cloud import speech
import threading
import psycopg2
import openai




def requete_GPT (texte):


    response = openai.chat.completions.create(
        model = "gpt-3.5-turbo",
        messages=[{"role": "user", "content": f'resume moi ce  texte : {texte}'}],
        max_tokens=300,
        temperature=1.2,
        stop=None
    )
    return response.choices[0].message.content





def register (update,context):
    user_id = update.effective_user.id
    search_query = f"SELECT * FROM connexion WHERE user_id = '{user_id}';"
    cursor.execute(search_query)
    results = cursor.fetchall()
    if not results:
        mdp = update.message.text.split()[1]
        print(mdp)
        insert_query = f"INSERT INTO connexion (mdp, user_id) VALUES ('{mdp}', '{user_id}');"
        cursor.execute(insert_query)
        connection.commit()
        update.message.reply_text(f'Bravo, vous êtes inscrit')
    else :
        update.message.reply_text(f'vous êtes déjà inscrit')

def start(update,context):
    update.message.reply_text('Training PFE 2023')
    user_id = update.effective_user.id

    update.message.reply_text(f'Votre ID : {user_id}')


def update_mdp(update,context):
    user_id = update.effective_user.id
    mdp = update.message.text.split()[1]
    new_mdp =update.message.text.split()[2]
    select_query = f"SELECT * FROM connexion WHERE user_id = '{user_id}' AND mdp = '{mdp}';"
    cursor.execute(select_query)
    result = cursor.fetchone()
    if result :
        update_query = f"UPDATE connexion SET mdp = '{new_mdp}' WHERE user_id = '{user_id}';"
        cursor.execute(update_query)
        connection.commit()
        update.message.reply_text(f"mot de passe changer pour : {new_mdp}")



def connexion(update,context):
    user_id = update.effective_user.id
    if user_id in tokens_list.keys():
        update.message.reply_text('vous êtes déjà connecté')
    else:
        mdp=update.message.text.strip('/connexion ')
        select_query = f"SELECT mdp FROM connexion WHERE user_id = '{user_id}';"
        cursor.execute(select_query)
        result = cursor.fetchone()
        if str(mdp)==str(result[0]):
            with lock:
                tokens_list[user_id]=time.time()
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
            for user_id, last_action_time in tokens_list.items():
                time_difference = current_time - last_action_time
                if time_difference >= 1800:  # 30 minutes en secondes
                    user_to_disconnect.append(user_id)



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


def send_text (update,context):
    update.message.reply_text("Vous avez choisi d'envoyer un texte. Veuillez entrer le texte maintenant.")
    return TEXT_INPUT
def define_text(update,context):
    user_id = update.effective_user.id
    if user_id in tokens_list.keys():
        tokens_list[user_id]=time.time()
        text=update.message.text.replace('/send ','')

        resume=requete_GPT(text)
        update.message.reply_text(resume)
        resume=resume.replace("'",' ')
        update.message.reply_text('entré un titre')

        context.chat_data['text'] = resume

        return TITLE_INPUT
    else:
        update.message.reply_text('Veuillez vous connecter')
        return ConversationHandler.END



def send_audio(update,context):
    update.message.reply_text("Veuillez envoyer une note vocale")
    return VOICE_INPUT

def define_audio(update,context):
    print('Define audio called')
    user_id = update.effective_user.id
    if user_id in tokens_list.keys():
        print('vocal recus')
        tokens_list[user_id] = time.time()
        file = context.bot.get_file(update.message.voice.file_id)
        audio = bytes(file.download_as_bytearray())

        client = speech.SpeechClient.from_service_account_file(GOOGLE_CLOUD_KEY_PATH)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
            sample_rate_hertz=48000,
            language_code="fr-FR",
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
        update.message.reply_text('entré un titre')
        return TITLE_INPUT_AUDIO
    else:
        update.message.reply_text('Veuillez vous connecter')
        return ConversationHandler.END

def define_title(update,context):
    user_id = update.effective_user.id
    title=update.message.text
    context.user_data.clear()
    update.message.reply_text(f'Le titre du document est : {title}')
    text = context.chat_data.get('text', 'Aucun texte enregistré')
    insert_query_doc = f"""INSERT INTO doc (contenue,id_user,title)
    SELECT '{text}',c.id,'{title}'
    FROM connexion c
    WHERE c.user_id = '{user_id}';"""
    cursor.execute(insert_query_doc)
    connection.commit()
    context.chat_data.clear()
    print(text)
    return ConversationHandler.END

def cancel (update,context) :
    context.chat_data.clear()
    return ConversationHandler.END


def send_pict(update, context):
    user_id = update.effective_user.id
    if user_id in tokens_list.keys():
        tokens_list[user_id] = time.time()
        image=context.bot.get_file(update.message.photo[-1].file_id)
        print(image)
        print('ok')
    else:
        update.message.reply_text('Veuillez vous connecter')

db_config = {
    'host': '34.163.90.30',
    'user': 'postgres',
    'password': 'jn{2J$Rr{)[L~_17',
    'database': 'PFE_bot',
    'port': '5432',  # Par défaut, le port de PostgreSQL est 5432
}

openai.api_key='**********'

try:
    connection = psycopg2.connect(**db_config)
    print('connected')
    cursor = connection.cursor()
except:
    print('not connected')

TEXT_INPUT,TITLE_INPUT = range(2)
VOICE_INPUT, TITLE_INPUT_AUDIO = range(2)

token='**********'

GOOGLE_CLOUD_KEY_PATH = "forward-subject-404414-79ec7490f294.json"

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
            TITLE_INPUT: [MessageHandler(Filters.text & ~Filters.command, define_title)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

dispatcher.add_handler(conversation_handler_text)


conversation_handler_voice=ConversationHandler(
    entry_points=[CommandHandler('send_audio',send_audio)],
    states={
        VOICE_INPUT : [MessageHandler(Filters.voice, define_audio)],
        TITLE_INPUT_AUDIO : [MessageHandler(Filters.text & ~Filters.command, define_title)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)

dispatcher.add_handler(conversation_handler_voice)
dispatcher.add_handler(CommandHandler('connexion',connexion))
dispatcher.add_handler(CommandHandler('register',register))
dispatcher.add_handler(CommandHandler('update_mdp',update_mdp))
dispatcher.add_handler(telegram.ext.MessageHandler(Filters.photo, send_pict))



updater.start_polling()
updater.idle()
