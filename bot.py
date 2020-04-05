#!/usr/bin/env python3
from datetime import datetime
import json
import logging
import re
import requests

from telegram import ParseMode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, InlineQueryHandler
from telegram.ext import PicklePersistence
from telegram.error import TelegramError

from statistics_api import CovidApi
import wikidata
from resources.resolver import resolve

CONFIG_FILE="config.json"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

WORLD_IDENT="world"

api = CovidApi()

def _lang(update):
    if update.message:
        return update.message.from_user.language_code
    elif update.inline_query:
        return update.inline_query.from_user.language_code
    else:
        return update.callback_query.from_user.language_code

def handler_decorator(handler):
    def wrapper(update, context, *args):
        handler(update, context, *args)
        time = datetime.now().timestamp()
        if not 'first_acc' in context.user_data:
            context.user_data['first_acc'] = time
        context.user_data['last_acc'] = time
        if not 'count' in context.user_data:
            context.user_data['count'] = 1
        else:
            context.user_data['count'] += 1
        context.dispatcher.persistence.flush()
    return wrapper

# command /start
def command_start(update, context):
    update.message.reply_markdown(resolve('start', _lang(update), update.message.from_user.first_name))

# command /help
@handler_decorator
def command_help(update, context):
    update.message.reply_markdown(resolve('help', _lang(update)), disable_web_page_preview=True)

def flag(code):
    return ''.join([chr(ord(c.upper())+127397) for c in code])

def format_stats(update, code, data, icon=None):
    if code in api.countries:
        name = api.countries[code]['name']
    else:
        name = code
    if not icon:
        icon = flag(code)
    p_active = data['active'] / data['cases']
    p_recov = data['recovered'] / data['cases']
    p_dead = data['deaths'] / data['cases']
    text = resolve('stats_table', _lang(update), name, icon, data['cases'],
            data['active'], p_active, data['recovered'], p_recov, data['deaths'], p_dead,
            data['todayCases'], data['todayDeaths'],
            datetime.fromtimestamp(data['updated'] / 1e3))
    return text

# command /today
@handler_decorator
def command_today(update, context):
    data = api.cases_world()
    if data:
        dt = datetime.fromtimestamp(data['updated'] / 1e3)
        text = resolve('today', _lang(update),
                dt, dt, data['todayCases'], data['todayDeaths'], data['cases'], data['deaths'])
        update.message.reply_markdown(text)
    else:
        update.message.reply_text(resolve('no_data', _lang(update)))

# command /world
@handler_decorator
def command_world(update, context):
    photo_file = wikidata.cases_world_map()
    data = api.cases_world()
    if data:
        text = format_stats(update, "the World", data, icon='\U0001f310')
        update.message.reply_photo(photo=photo_file, caption=text, parse_mode=ParseMode.MARKDOWN)
    else:
        update.message.reply_text(resolve('no_data', _lang(update)))

def format_list_item(data):
    code = data['countryInfo']['iso2'].lower()
    text = """
{} *{}  -  {}*
      \U0001f9a0 `{:,}`  \u26B0\uFE0F `{:,}`
    """.format(flag(code), data['country'], '/'+code, data['cases'], data['deaths'])
    return text

def get_list_keyboard(update, current_index, limit, last=False):
    keyboard = [[]]
    if current_index > 0:
        keyboard[0].append(InlineKeyboardButton(resolve('page_left', _lang(update), current_index),
                                callback_data="list {} {}".format(current_index-1, limit)))
    if not last:
        keyboard[0].append(InlineKeyboardButton(resolve('page_right', _lang(update), current_index+2),
                                callback_data="list {} {}".format(current_index+1, limit)))
    if current_index > 0:
        keyboard.append([
            InlineKeyboardButton(resolve('to_start', _lang(update)), callback_data="list 0 {}".format(limit))])
    else:
        keyboard.append([
            InlineKeyboardButton(resolve('to_end', _lang(update)), callback_data="list -1 {}".format(limit))])
    return InlineKeyboardMarkup(keyboard)

# command /list
@handler_decorator
def command_list(update, context):
    # by default, return 7 items. min 2 and max 20.
    limit = int(context.args[0]) if len(context.args) > 0 else 7
    limit = min(max(2, limit), 20)
    case_list = api.cases_country_list()[:limit]
    if len(case_list) > 0:
        text = resolve('list_header', _lang(update))
        for item in case_list:
            text += format_list_item(item)
        update.message.reply_markdown(text, reply_markup=get_list_keyboard(update, 0, limit))
    else:
        update.message.reply_text(resolve('no_data', _lang(update)))

def callback_list_pages(update, context):
    query = update.callback_query
    page, limit = int(context.match.group(1)), int(context.match.group(2))
    case_list = api.cases_country_list()
    if page >= 0:
        case_list = case_list[page*limit:(page+1)*limit]
    else:
        # if the given page number is negative, we want to access the last page
        page = len(case_list) // limit
        offset = len(case_list) % limit
        case_list = case_list[-offset:]
    query.answer()
    if len(case_list) > 0:
        text = resolve('list_header', _lang(update))
        for item in case_list:
            text += format_list_item(item)
        query.edit_message_text(text=text, parse_mode=ParseMode.MARKDOWN,
                                reply_markup=get_list_keyboard(update, page, limit, len(case_list) < limit))
    else:
        query.edit_message_text(resolve('no_data', _lang(update)),
                                reply_markup=get_list_keyboard(update, page, limit, len(case_list) < limit))


# command /[country]
@handler_decorator
def command_country(update, context, country_code):
    photo_file = wikidata.cases_country_map(country_code)
    data = api.cases_country(country_code)
    if data:
        text = format_stats(update, country_code, data)
        update.message.reply_photo(photo=photo_file, caption=text, parse_mode=ParseMode.MARKDOWN)
    else:
        update.message.reply_text(resolve('no_data', _lang(update)))

# free text input
@handler_decorator
def handle_text(update, context):
    query_string = update.message.text.lower()
    if query_string in api.name_map:
        command_country(update, context, api.name_map[query_string])
    elif WORLD_IDENT in query_string:
        command_world(update, context)
    else:
        update.message.reply_text(resolve('unknown_place', _lang(update)))

# inline queries
def handle_inlinequery(update, context):
    inline_query = update.inline_query
    query_string = inline_query.query
    if not query_string:
        return
    results = []
    # a special case matching 'world'
    if WORLD_IDENT.startswith(query_string):
        results.append(WORLD_IDENT)
    for name in api.name_map.keys():
        if name.startswith(query_string):
            results.append(name)
        # limit to the first threee results
        if len(results) >= 3:
            break
    query_results = []
    for i,s in enumerate(results):
        if s == WORLD_IDENT:
            data = api.cases_world()
            text = format_stats(update, "the World", data, icon='\U0001f310')
        else:
            country_code = api.name_map[s]
            data = api.cases_country(country_code)
            text = format_stats(update, country_code, data)
        text+='\n'+resolve('more', _lang(update))
        result_content = InputTextMessageContent(text, parse_mode=ParseMode.MARKDOWN)
        query_results.append(
            InlineQueryResultArticle(id=i, title=s, input_message_content=result_content)
        )
    inline_query.answer(query_results)

def error(update, context):
    try:
        raise context.error
    except TelegramError:
        logger.warning('Update {} caused error "{}"'.format(update, context.error))

def main(config):
    persistence = PicklePersistence("database.pkl")
    updater = Updater(config['token'], persistence=persistence, use_context=True)
    # add commands
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", command_start))
    dp.add_handler(CommandHandler("help", command_help))
    dp.add_handler(CommandHandler("today", command_today))
    dp.add_handler(CommandHandler("world", command_world))
    dp.add_handler(CommandHandler("list", command_list))
    # callbacks for page buttons in list
    dp.add_handler(CallbackQueryHandler(callback_list_pages, pattern=r"list (-?\d+) (\d+)"))
    # for every country, add a command for the iso2 and iso3 codes and the name
    for iso, country in api.countries.items():
        callback = lambda update, context, code=iso: command_country(update, context, code)
        dp.add_handler(CommandHandler(iso, callback))
        if country['iso3']:
            dp.add_handler(CommandHandler(country['iso3'], callback))
        name_normal = re.sub(r"[^a-z]", "_", country['name'].lower())
        dp.add_handler(CommandHandler(name_normal, callback))
    # free text input
    dp.add_handler(MessageHandler(Filters.text, handle_text))
    dp.add_handler(InlineQueryHandler(handle_inlinequery))
    dp.add_error_handler(error)
    # start the bot
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    main(config)
