import telegram.ext
from telegram.ext import Filters

#from telegram import Update
#from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
token='6649338214:AAGS4ag-NDDZWX6gM5rRPP7RCH00vOBTUjg'
updater = telegram.ext.Updater('6649338214:AAGS4ag-NDDZWX6gM5rRPP7RCH00vOBTUjg',use_context=True)
dispatcher=updater.dispatcher

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
    print("sound ok")
    sound=context.bot.get_file(update.message.voice.file_id)
    print(sound)

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