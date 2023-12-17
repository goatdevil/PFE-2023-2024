import time

import telegram.ext
from telegram.ext import Filters, ConversationHandler, CommandHandler, MessageHandler, CallbackContext, Updater
from google.oauth2 import service_account
from google.cloud import speech
import threading
import psycopg2
import openai


#from telegram import Update
#from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes



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
    /start => message au debut
    /help => commande annexe"""
                              )
def send(update,context):
    user_id = update.effective_user.id
    if user_id in tokens_list.keys():
        tokens_list[user_id]=time.time()
        text=update.message.text.replace('/send ','')

        resume=requete_GPT(text)
        print(resume)
        update.message.reply_text(resume)

    else:
        update.message.reply_text('Veuillez vous connecter')

def send_pict(update, context):
    user_id = update.effective_user.id
    if user_id in tokens_list.keys():
        tokens_list[user_id] = time.time()
        image=context.bot.get_file(update.message.photo[-1].file_id)
        print(image)
        print('ok')
    else:
        update.message.reply_text('Veuillez vous connecter')

def send_audio(update,context):
    user_id = update.effective_user.id
    if user_id in tokens_list.keys():
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
            print(resume)
            update.message.reply_text(resume)
    else:
        update.message.reply_text('Veuillez vous connecter')


db_config = {
    'host': '34.163.90.30',
    'user': 'postgres',
    'password': 'jn{2J$Rr{)[L~_17',
    'database': 'PFE_bot',
    'port': '5432',  # Par défaut, le port de PostgreSQL est 5432
}

openai.api_key='************************'

try:
    connection = psycopg2.connect(**db_config)
    print('connected')
    cursor = connection.cursor()
except:
    print('not connected')

token='************'

GOOGLE_CLOUD_KEY_PATH = "forward-subject-404414-79ec7490f294.json"

tokens_list={}
lock = threading.Lock()
check_thread = threading.Thread(target=check_connexion)
check_thread.start()

updater = Updater(token,use_context=True)
dispatcher=updater.dispatcher
dispatcher.add_handler(CommandHandler('start',start))
dispatcher.add_handler(CommandHandler('help',help))
dispatcher.add_handler(CommandHandler('send',send))
dispatcher.add_handler(CommandHandler('connexion',connexion))
dispatcher.add_handler(CommandHandler('register',register))
dispatcher.add_handler(CommandHandler('update_mdp',update_mdp))
dispatcher.add_handler(telegram.ext.MessageHandler(Filters.photo, send_pict))
dispatcher.add_handler(telegram.ext.MessageHandler(Filters.voice, send_audio))

updater.start_polling()
updater.idle()


