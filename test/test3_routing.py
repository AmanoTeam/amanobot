import sys
import time
import random
import amanobot.helper
from amanobot.routing import (by_content_type, make_content_type_routing_table,
                             lower_key, by_chat_command, make_routing_table,
                             by_regex)

def random_key(msg):
    return random.choice([
        0,
        (1,),
        (2, ('a1',)),
        (3, ('a1', 'a2'), {'b1': 'b'}),
        (4, (), {'kw4': 4444, 'kw5': 'xyz'}),
        ((None,), ()),
    ])

def zero(msg):
    print('Zero')

def one(msg):
    print('One')

def two(msg, a1):
    print('Two', a1)

def three(msg, a1, a2, b1):
    print('Three', a1, a2, b1)

def none_tuple(msg):
    print('None tuple')

def none_of_above(msg, *args, **kwargs):
    print('None of above', msg, args, kwargs)

top_router = amanobot.helper.Router(random_key, {0: zero,
                                                1: one,
                                                2: two,
                                                3: three,
                                                (None,): none_tuple,
                                                None: none_of_above})

for i in range(0,20):
    top_router.route({})
print()


class ContentTypeHandler():
    @staticmethod
    def on_text(msg, text):
        print('Text', msg, text)

    @staticmethod
    def on_photo(msg, photo):
        print('Photo', msg, photo)

def make_message_like(mm):
    for d in mm:
        d.update({'chat': {'type': 'private', 'id': 1000}})

top_router.key_function = by_content_type()
top_router.routing_table = make_content_type_routing_table(ContentTypeHandler())
del top_router.routing_table['video']  # let video fall to default handler
top_router.routing_table[None] = none_of_above

messages = [{'text': 'abc'},
            {'photo': 'some photo'},
            {'video': 'some video'},]
make_message_like(messages)

for i in range(0,10):
    top_router.route(random.choice(messages))
print()


class CommandHandler():
    @staticmethod
    def on_start(msg):
        print('Command: start', msg)

    @staticmethod
    def on_settings(msg):
        print('Command: settings', msg)

    @staticmethod
    def on_invalid_text(msg):
        print('Invalid text', msg)

    @staticmethod
    def on_invalid_command(msg):
        print('Invalid command', msg)

command_handler = CommandHandler()
command_router = amanobot.helper.Router(lower_key(by_chat_command()),
                                       make_routing_table(command_handler, [
                                           'start',
                                           'settings',
                                           ((None,), command_handler.on_invalid_text),
                                           (None, command_handler.on_invalid_command),
                                       ]))

top_router.routing_table['text'] = command_router.route

messages = [{'text': '/start'},
            {'text': '/SETTINGS'},
            {'text': '/bad'},
            {'text': 'plain text'},
            {'photo': 'some photo'},
            {'video': 'some video'},]
make_message_like(messages)

for i in range(0,20):
    top_router.route(random.choice(messages))
print()


class RegexHandler():
    @staticmethod
    def on_CS101(msg, match):
        print('Someone mentioned CS101 !!!', msg, match.groups())

    @staticmethod
    def on_CS202(msg, match):
        print('Someone mentioned CS202 !!!', msg, match.groups())

    @staticmethod
    def no_cs_courses_mentioned(msg):
        print('No CS courses mentioned ...', msg)

    @staticmethod
    def course_not_exist(msg, match):
        print('%s does not exist' % match.group(1), msg)

regex_handler = RegexHandler()
regex_router = amanobot.helper.Router(by_regex(lambda msg: msg['text'], '(CS[0-9]{3})'),
                                     make_routing_table(regex_handler, [
                                         'CS101',
                                         'CS202',
                                         ((None,), regex_handler.no_cs_courses_mentioned),
                                         (None, regex_handler.course_not_exist),
                                     ]))

command_router.routing_table[(None,)] = regex_router.route

messages = [{'text': '/start'},
            {'text': '/SETTINGS'},
            {'text': '/bad'},
            {'text': 'plain text'},
            {'text': 'I want to take CS101.'},
            {'text': 'I\'d rather take CS202.'},
            {'text': 'Why don\'t you take CS303?'},
            {'text': 'I hate computer science!'},
            {'photo': 'some photo'},
            {'video': 'some video'},]
make_message_like(messages)

for i in range(0,30):
    top_router.route(random.choice(messages))
print()


TOKEN = sys.argv[1]

bot = amanobot.Bot(TOKEN)
bot._router.routing_table['chat'] = top_router.route

bot.message_loop()
print('Send me some messages ...')

while 1:
    time.sleep(10)
