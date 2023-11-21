import telegram.ext
from telegram.ext import Filters
from google.oauth2 import service_account
from google.cloud import speech



#from telegram import Update
#from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
token='*******'
updater = telegram.ext.Updater(token,use_context=True)
dispatcher=updater.dispatcher
GOOGLE_CLOUD_KEY_PATH = "forward-subject-404414-79ec7490f294.json"


def start(update,context):
    update.message.reply_text('Training PFE 2023')
def help(update,context):
    update.message.reply_text("""
    /start => message au debut
    /help => commande annexe"""
                              )
def send(update,context):
    text=update.message.text.strip('/send ')
    update.message.reply_text(text)
    print(text)

def send_pict(update, context):
    image=context.bot.get_file(update.message.photo[-1].file_id)
    print(image)
    print('ok')

def send_audio(update,context):
    file = context.bot.get_file(update.message.voice.file_id)
    audio = bytes(file.download_as_bytearray())

    client = speech.SpeechClient.from_service_account_file(GOOGLE_CLOUD_KEY_PATH)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
        sample_rate_hertz=48000,
        language_code="fr-FR",
    )

    audio=speech.RecognitionAudio(content=audio)
    response=client.recognize(config=config,audio=audio)

    for result in response.results:
        print("Transcription: {}".format(result.alternatives[0].transcript))




dispatcher.add_handler(telegram.ext.CommandHandler('start',start))
dispatcher.add_handler(telegram.ext.CommandHandler('help',help))
dispatcher.add_handler(telegram.ext.CommandHandler('send',send))
dispatcher.add_handler(telegram.ext.MessageHandler(Filters.photo, send_pict))
dispatcher.add_handler(telegram.ext.MessageHandler(Filters.voice, send_audio))

updater.start_polling()
updater.idle()

#app = ApplicationBuilder().token("6649338214:AAGS4ag-NDDZWX6gM5rRPP7RCH00vOBTUjg").build()

#app.add_handler(CommandHandler("hello", hello))

#app.run_polling()