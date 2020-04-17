from datetime import datetime
import re

def lang(update):
    if update.message:
        return update.message.from_user.language_code
    elif update.inline_query:
        return update.inline_query.from_user.language_code
    else:
        return update.callback_query.from_user.language_code

def handler_decorator(handler):
    def wrapper(update, context, *args):
        ret = handler(update, context, *args)
        time = datetime.now().timestamp()
        if not 'first_acc' in context.user_data:
            context.user_data['first_acc'] = time
        context.user_data['last_acc'] = time
        if not 'count' in context.user_data:
            context.user_data['count'] = 1
        else:
            context.user_data['count'] += 1
        context.dispatcher.persistence.flush()
        return ret
    return wrapper

def flag(code):
    return ''.join([chr(ord(c.upper())+127397) for c in code])

def check_flag(s):
    return re.match(r"[\U0001f1e6-\U0001f1ff]{2}", s)

def code_from_flag(flag):
    return ''.join([chr(ord(c)-127397) for c in flag])
