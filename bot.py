#!/usr/bin/env python3
from datetime import datetime
import json
import logging
import re
import requests
from time import sleep

from telegram import ParseMode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, InlineQueryHandler
from telegram.ext import PicklePersistence, ConversationHandler, DispatcherHandlerStop
from telegram.error import TelegramError

from statistics_api import CovidApi
import wikidata
from resources.resolver import resolve
from utils import *

CONFIG_FILE="config.json"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

WORLD_IDENT="world"

api = CovidApi()

# command /start
def command_start(update, context):
    update.message.reply_markdown(resolve('start', lang(update), update.message.from_user.first_name))

# command /help
@handler_decorator
def command_help(update, context):
    update.message.reply_markdown(resolve('help', lang(update)), disable_web_page_preview=True)

### World & country stats + status report ###

def format_stats(update, code, data, icon=None, detailed=False):
    if code in api.countries:
        name = api.countries[code]['name']
    elif code == WORLD_IDENT:
        name = "the World"
        icon = '\U0001f310'
    else:
        name = code
    if not icon:
        icon = flag(code)
    p_dead = data['deaths'] / data['cases']
    if 'active' in data and 'todayCases' in data: # we have detailed data, so use more detailed view
        p_active = data['active'] / data['cases']
        p_recov = data['recovered'] / data['cases']
        text = resolve('stats_table', lang(update), name, icon, data['cases'],
                data['active'], p_active, data['recovered'], p_recov, data['deaths'], p_dead,
                data['todayCases'], data['todayDeaths'])
        if detailed:
            text += '\n'+resolve('stats_table_more', lang(update), data['casesPerOneMillion'] or 0,
                            data['deathsPerOneMillion'] or 0)
    else: # we only have limited data
        text = resolve('stats_table_simple', lang(update), name, icon, data['cases'], data['deaths'], p_dead)
    text += '\n'+resolve('stats_updated', lang(update), datetime.utcfromtimestamp(data['updated'] / 1e3))
    return text

def get_stats_keyboard(update, country_code, is_detailed=False):
    keyboard = [[]]
    caption_key = 'stats_more' if not is_detailed else 'stats_less'
    caption = resolve(caption_key, lang(update))
    keyboard[0].append(InlineKeyboardButton(caption,
                    callback_data="stats {} {}".format(country_code, 1 if is_detailed else 0)))
    return InlineKeyboardMarkup(keyboard)

# the text used for daily notifications and /today
def get_status_report(country_code=None, lang="en"):
    data = api.cases_world()
    if data:
        dt = datetime.utcfromtimestamp(data['updated'] / 1e3)
        text = resolve('today', lang,
                dt, dt, data['cases'], data['deaths'], data['todayCases'], data['todayDeaths'])
        # fetch data of home country if set
        if country_code:
            country_data = api.cases_country(country_code)
            text += '\n'+resolve('today_country', lang, flag(country_code),
                            api.countries[country_code]['name'], country_data['cases'], country_data['deaths'],
                            country_data['todayCases'], country_data['todayDeaths'], country_code.lower())
        else:
            text += '\n_'+resolve('no_country_set', lang)+'_\n'
        text += '\n'+resolve('today_footer', lang)
    else:
        text = resolve('no_data',lang)
    return text

# command /today
@handler_decorator
def command_today(update, context):
    if 'country' in context.chat_data:
        country_code = context.chat_data['country']
    else:
        country_code = None
    text = get_status_report(country_code, lang(update))
    update.message.reply_markdown(text)

def format_list_item(data, order):
    code = data['countryInfo']['iso2'].lower()
    icon = resolve('sort_order_'+order, None).split(' ')[0]
    number = data[order]
    text = """
{} *{}  -  {}*  -  {} `{:,}`
    """.format(flag(code), data['country'], '/'+code, icon, number)
    return text

def get_list_keyboard(update, current_index, limit, last=False):
    keyboard = [[]]
    if current_index > 0:
        keyboard[0].append(InlineKeyboardButton(resolve('page_left', lang(update), current_index),
                                callback_data="list {} {}".format(current_index-1, limit)))
    if not last:
        keyboard[0].append(InlineKeyboardButton(resolve('page_right', lang(update), current_index+2),
                                callback_data="list {} {}".format(current_index+1, limit)))
    if current_index > 0:
        keyboard.append([
            InlineKeyboardButton(resolve('to_start', lang(update)), callback_data="list 0 {}".format(limit))])
    else:
        keyboard.append([
            InlineKeyboardButton(resolve('to_end', lang(update)), callback_data="list -1 {}".format(limit))])
    keyboard.append([
        InlineKeyboardButton(resolve('sort_order', lang(update)),
                callback_data="list_order_menu 1 ({} {} {})".format(current_index, limit, int(last)))
    ])
    return InlineKeyboardMarkup(keyboard)

SORT_ORDERS = ['cases', 'deaths', 'casesPerOneMillion', 'deathsPerOneMillion', 'todayCases', 'todayDeaths']

def get_list_order_keyboard(update, current_index, limit, last=False):
    keyboard = []
    for i, sort_order in enumerate(SORT_ORDERS):
        button = InlineKeyboardButton(resolve("sort_order_"+sort_order, lang(update)), callback_data="list_order {} {}".format(sort_order, limit))
        if i % 2 == 0:
            l = [button]
        else:
            l.append(button)
            keyboard.append(l)
    keyboard.append([InlineKeyboardButton(resolve('back', lang(update)),
                callback_data="list_order_menu 0 ({} {} {})".format(current_index, limit, int(last)))])
    return InlineKeyboardMarkup(keyboard)

# command /world
@handler_decorator
def command_world(update, context):
    photo_file = wikidata.cases_world_map()
    data = api.cases_world()
    if data:
        text = format_stats(update, WORLD_IDENT, data)
        update.message.reply_photo(photo=photo_file, caption=text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=get_stats_keyboard(update, WORLD_IDENT))
    else:
        update.message.reply_text(resolve('no_data', lang(update)))

# command /[country]
@handler_decorator
def command_country(update, context, country_code):
    photo_file = wikidata.cases_country_map(country_code)
    data = api.cases_country(country_code)
    if data:
        text = format_stats(update, country_code, data)
        if photo_file:
            update.message.reply_photo(photo=photo_file, caption=text, parse_mode=ParseMode.MARKDOWN,
                                       reply_markup=get_stats_keyboard(update, country_code))
        else:
            update.message.reply_markdown(text, reply_markup=get_stats_keyboard(update, country_code))
    else:
        update.message.reply_text(resolve('no_data', lang(update)))

def command_us_state(update, context, state):
    data = api.cases_us_state(state)
    if data:
        text = format_stats(update, state.title(), data, icon='\uD83C\uDDFA\uD83C\uDDF8')
        update.message.reply_markdown(text)
    else:
        update.message.reply_text(resolve('no_data', lang(update)))

def command_de_state(update, context, state):
    data = api.cases_de_state(state)
    if data:
        text = format_stats(update, state.title(), data, icon='\uD83C\uDDE9\uD83C\uDDEA')
        update.message.reply_markdown(text)
    else:
        update.message.reply_text(resolve('no_data', lang(update)))

def callback_stats(update, context):
    query = update.callback_query
    country_code = context.match.group(1)
    # True if we want to *show* detailed mode, False otherwise
    is_detailed = not bool(int(context.match.group(2)))
    if country_code == WORLD_IDENT:
        data = api.cases_world()
    else:
        data = api.cases_country(country_code)
    if data:
        text = format_stats(update, country_code, data, detailed=is_detailed)
        if query.message.caption:
            query.edit_message_caption(caption=text, parse_mode=ParseMode.MARKDOWN,
                                       reply_markup=get_stats_keyboard(update, country_code, is_detailed))
        else:
            query.edit_message_text(text=text, parse_mode=ParseMode.MARKDOWN,
                                    reply_markup=get_stats_keyboard(update, country_code, is_detailed))

### Country list ###

# command /list
@handler_decorator
def command_list(update, context):
    # set or retrieve sort order
    if len(context.args) > 0:
        order = context.args[0]
        context.chat_data['order'] = order
    elif 'order' in context.chat_data:
        order = context.chat_data['order']
    else:
        # use first possible order as default
        order = SORT_ORDERS[0]
        context.chat_data['order'] = order
    # by default, return 7 items. min 2 and max 20.
    limit = int(context.args[1]) if len(context.args) > 1 else 7
    limit = min(max(2, limit), 20)
    case_list = api.cases_country_list(sort_by=order)[:limit]
    if len(case_list) > 0:
        text = resolve('list_header', lang(update), resolve("sort_order_"+order, lang(update)))
        for item in case_list:
            text += format_list_item(item, order)
        update.message.reply_markdown(text, reply_markup=get_list_keyboard(update, 0, limit))
    else:
        update.message.reply_text(resolve('no_data', lang(update)))

def callback_list_pages(update, context):
    query = update.callback_query
    order = context.chat_data.get('order', SORT_ORDERS[0]) # for backward comp
    page, limit = int(context.match.group(1)), int(context.match.group(2))
    case_list = api.cases_country_list(sort_by=order)
    if page >= 0:
        case_list = case_list[page*limit:(page+1)*limit]
    else:
        # if the given page number is negative, we want to access the last page
        page = len(case_list) // limit
        offset = len(case_list) % limit
        case_list = case_list[-offset:]
    query.answer()
    if len(case_list) > 0:
        text = resolve('list_header', lang(update), resolve("sort_order_"+order, lang(update)))
        for item in case_list:
            text += format_list_item(item, order)
        query.edit_message_text(text=text, parse_mode=ParseMode.MARKDOWN,
                                reply_markup=get_list_keyboard(update, page, limit, len(case_list) < limit))
    else:
        query.edit_message_text(resolve('no_data', lang(update)),
                                reply_markup=get_list_keyboard(update, page, limit, len(case_list) < limit))

def callback_list_order_menu(update, context):
    query = update.callback_query
    on = int(context.match.group(1))
    payload = [int(g) for g in context.match.group(2).split(" ")]
    query.answer()
    if on:
        query.edit_message_reply_markup(reply_markup=get_list_order_keyboard(update, *payload))
    else:
        query.edit_message_reply_markup(reply_markup=get_list_keyboard(update, *payload))

def callback_list_order(update, context):
    query = update.callback_query
    order = context.match.group(1)
    # save the selected order
    context.chat_data['order'] = order
    limit = int(context.match.group(2))
    case_list = api.cases_country_list(sort_by=order)[:limit]
    query.answer()
    if len(case_list) > 0:
        text = resolve('list_header', lang(update), resolve("sort_order_"+order, lang(update)))
        for item in case_list:
            text += format_list_item(item, order)
        query.edit_message_text(text=text, parse_mode=ParseMode.MARKDOWN,
                                reply_markup=get_list_keyboard(update, 0, limit, len(case_list) < limit))
    else:
        query.edit_message_text(resolve('no_data', lang(update)),
                                reply_markup=get_list_keyboard(update, 0, limit, len(case_list) < limit))

### Free text & inline ###

# free text input
@handler_decorator
def handle_text(update, context):
    query_string = update.message.text.lower()
    if query_string in api.name_map:
        command_country(update, context, api.name_map[query_string])
    elif WORLD_IDENT in query_string:
        command_world(update, context)
    elif check_flag(query_string):
        code = code_from_flag(query_string).lower()
        if code in api.name_map:
            command_country(update, context, api.name_map[code])
    elif query_string.title() in api.us_states:
        command_us_state(update, context, query_string)
    elif query_string.title() in api.de_states:
        command_de_state(update, context, query_string)
    else:
        update.message.reply_text(resolve('unknown_place', lang(update)))

# inline queries
def handle_inlinequery(update, context):
    inline_query = update.inline_query
    query_string = inline_query.query.lower()
    if not query_string:
        return
    results = []
    # a special case matching 'world'
    if WORLD_IDENT.startswith(query_string):
        results.append((WORLD_IDENT, WORLD_IDENT))
    for name in api.name_map.keys():
        if name.startswith(query_string):
            results.append((name, "country"))
        # limit to the first threee results
        if len(results) >= 3:
            break
    if len(results) < 3:
        for state in api.us_states:
            if state.lower().startswith(query_string):
                results.append((state.lower(), "us_state"))
            if len(results) >= 3:
                break
    if len(results) < 3:
        for state in api.de_states:
            if state.lower().startswith(query_string):
                results.append((state.lower(), "de_state"))
            if len(results) >= 3:
                break
    query_results = []
    for i,(s, t) in enumerate(results):
        if t == WORLD_IDENT:
            data = api.cases_world()
            text = format_stats(update, WORLD_IDENT, data, detailed=True)
        elif t == "us_state":
            data = api.cases_us_state(s)
            text = format_stats(update, s.title(), data, icon='\uD83C\uDDFA\uD83C\uDDF8')
        elif t == "de_state":
            data = api.cases_de_state(s)
            text = format_stats(update, s.title(), data, icon='\uD83C\uDDE9\uD83C\uDDEA')
        else:
            country_code = api.name_map[s]
            data = api.cases_country(country_code)
            text = format_stats(update, country_code, data, detailed=True)
        text+='\n'+resolve('more', lang(update))
        result_content = InputTextMessageContent(text, parse_mode=ParseMode.MARKDOWN)
        query_results.append(
            InlineQueryResultArticle(id=i, title=s, input_message_content=result_content)
        )
    inline_query.answer(query_results)

### Set country ###

# command /setcountry
@handler_decorator
def handle_setcountry_start(update, context):
    update.message.reply_markdown(resolve('setcountry_start', lang(update)))
    return 1

def handle_setcountry_input(update, context):
    query_string = update.message.text.lower()
    if query_string in api.name_map:
        code = api.name_map[query_string]
        context.chat_data['country'] = code
        update.message.reply_markdown(
                resolve('setcountry_success', lang(update), api.countries[code]['name']))
        return ConversationHandler.END
    else:
        update.message.reply_text(resolve('unknown_place', lang(update)))

def handle_setcountry_cancel(update, context):
    update.message.reply_text(resolve('cancel', lang(update)))
    return ConversationHandler.END

### Notification subscription ###

@handler_decorator
def command_subscribe(update, context):
    if not 'subscribers' in context.bot_data:
        context.bot_data['subscribers'] = [update.message.chat.id]
    elif not update.message.chat.id in context.bot_data['subscribers']:
        context.bot_data['subscribers'].append(update.message.chat.id)
    update.message.reply_markdown(resolve('subscribe', lang(update)))

@handler_decorator
def command_unsubscribe(update, context):
    if 'subscribers' in context.bot_data:
        if update.message.chat.id in context.bot_data['subscribers']:
            context.bot_data['subscribers'].remove(update.message.chat.id)
    update.message.reply_markdown(resolve('unsubscribe', lang(update)))

# runs the status notification job once per day
def run_notify(context):
    if not 'subscribers' in context.bot_data:
        logger.warn("No subscribers list specified.")
        return
    count = 0
    for chat_id in context.bot_data['subscribers']:
        try:
            country_code = context.dispatcher.chat_data[chat_id].get('country', None)
            text = get_status_report(country_code=country_code) # TODO always English
            context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN)
            count+=1
            sleep(0.05) # try to avoid flood limits
        except Exception as ex:
            # remove user from subscribers if he blocked or kicked the bot
            if isinstance(ex, TelegramError) and ex.message.startswith("Forbidden: "):
                context.bot_data['subscribers'].remove(chat_id)
            logger.error("Failed to send daily notification to {}".format(chat_id), exc_info=True)
    logger.info("Successfully sent daily notification to {} users.".format(count))

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
    dp.add_handler(CallbackQueryHandler(callback_list_order_menu, pattern=r"list_order_menu (\d+) \(([\d\s]+)\)"))
    dp.add_handler(CallbackQueryHandler(callback_list_order, pattern=r"list_order (\w+) (\d+)"))
    # for every country, add a command for the iso2 and iso3 codes and the name
    for iso, country in api.countries.items():
        callback = lambda update, context, code=iso: command_country(update, context, code)
        dp.add_handler(CommandHandler(iso, callback))
        if country['iso3']:
            dp.add_handler(CommandHandler(country['iso3'], callback))
        name_normal = re.sub(r"[^a-z]", "_", country['name'].lower())
        dp.add_handler(CommandHandler(name_normal, callback))
    # country detailed button callback
    dp.add_handler(CallbackQueryHandler(callback_stats, pattern=r"stats (\w+) (\d)"))
    # set country (this has to be added before the free text handler)
    dp.add_handler(ConversationHandler(
        entry_points=[CommandHandler("setcountry", handle_setcountry_start)],
        states={
            1: [MessageHandler(Filters.text & ~Filters.command, handle_setcountry_input)]
        },
        fallbacks=[CommandHandler("cancel", handle_setcountry_cancel)],
        conversation_timeout=60*10 # = 10 minutes
    ))
    # subscription
    dp.add_handler(CommandHandler("subscribe", command_subscribe))
    dp.add_handler(CommandHandler("unsubscribe", command_unsubscribe))
    # subscription job
    job_queue = updater.job_queue
    if 'notify_time' in config:
        job_queue.run_daily(run_notify, datetime.strptime(config['notify_time'], '%H:%M').time())
    # free text input
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dp.add_handler(InlineQueryHandler(handle_inlinequery))
    dp.add_error_handler(error)
    # start the bot
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    main(config)
