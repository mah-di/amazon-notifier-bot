import configparser

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

from core_funcs import register, stop_updates, stop_all_updates, restart_updates, process_update, bulk_update
from utils import start_response, about_response, help_response
from db_utils import fetch_or_create_user


CFG = configparser.ConfigParser()
CFG.read('config.ini')
URL_PREFIX = CFG['settings']['url_prefix']
URL_SUFFIX = CFG['settings']['url_suffix']
TOKEN = CFG['credentials']['token']

START_TEXT = start_response()
ABOUT_TEXT = about_response()
HELP_TEXT = help_response()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await fetch_or_create_user(update.effective_user)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{START_TEXT}")

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=ABOUT_TEXT)

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=HELP_TEXT)

async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        message = 'Please provide valid amazon product URL(s) or ASIN number(s).'
        return await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

    await register(update.effective_chat.id, update.effective_user, context.args)

async def update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_message = update.effective_message.reply_to_message
    this_bot = await context.bot.get_me()

    response = await process_update(this_bot, update.effective_chat.id, update.effective_user.username, reply_message)
    if response:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

async def updateall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = await bulk_update(update.effective_chat.id)
    if response:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_message = update.effective_message.reply_to_message
    this_bot = await context.bot.get_me()

    response = await stop_updates(this_bot, update.effective_user.username, reply_message)
    if response:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

async def stopall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = await stop_all_updates(update.effective_user.username)
    if response:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_message = update.effective_message.reply_to_message
    this_bot = await context.bot.get_me()
    
    response = await restart_updates(this_bot, update.effective_chat.id, update.effective_user.username, reply_message)
    if response:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    start_handler = CommandHandler('start', start)
    app.add_handler(start_handler)
    about_handler = CommandHandler('about', about)
    app.add_handler(about_handler)
    help_handler = CommandHandler('help', help)
    app.add_handler(help_handler)
    track_handler = CommandHandler('track', track)
    app.add_handler(track_handler)
    update_handler = CommandHandler('update', update)
    app.add_handler(update_handler)
    updateall_handler = CommandHandler('updateall', updateall)
    app.add_handler(updateall_handler)
    stop_handler = CommandHandler('stop', stop)
    app.add_handler(stop_handler)
    stopall_handler = CommandHandler('stopall', stopall)
    app.add_handler(stopall_handler)
    restart_handler = CommandHandler('restart', restart)
    app.add_handler(restart_handler)

    app.run_polling()
