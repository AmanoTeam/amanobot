import sys
import time
import amanobot
from amanobot.loop import MessageLoop
from amanobot.delegate import per_inline_from_id, create_open, pave_event_space

"""
$ python3 inline.py <token>

It demonstrates answering inline query and getting chosen inline results.
"""

class InlineHandler(amanobot.helper.InlineUserHandler, amanobot.helper.AnswererMixin):

    def on_inline_query(self, msg):
        def compute_answer():
            query_id, from_id, query_string = amanobot.glance(msg, flavor='inline_query')
            print(self.id, ':', 'Inline Query:', query_id, from_id, query_string)

            articles = [{'type': 'article',
                             'id': 'abc', 'title': query_string, 'message_text': query_string}]

            return articles

        self.answerer.answer(msg, compute_answer)

    def on_chosen_inline_result(self, msg):
        from pprint import pprint
        pprint(msg)
        result_id, from_id, query_string = amanobot.glance(msg, flavor='chosen_inline_result')
        print(self.id, ':', 'Chosen Inline Result:', result_id, from_id, query_string)


TOKEN = sys.argv[1]

bot = amanobot.DelegatorBot(TOKEN, [
    pave_event_space()(
        per_inline_from_id(), create_open, InlineHandler, timeout=10),
])
MessageLoop(bot).run_as_thread()
print('Listening ...')

while 1:
    time.sleep(10)
