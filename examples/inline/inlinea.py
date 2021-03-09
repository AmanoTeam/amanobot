import sys
import asyncio
import amanobot
from amanobot.aio.loop import MessageLoop
from amanobot.aio.helper import InlineUserHandler, AnswererMixin
from amanobot.aio.delegate import per_inline_from_id, create_open, pave_event_space

"""
$ python3 inlinea.py <token>

It demonstrates answering inline query and getting chosen inline results.
"""

class InlineHandler(InlineUserHandler, AnswererMixin):

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

bot = amanobot.aio.DelegatorBot(TOKEN, [
    pave_event_space()(
        per_inline_from_id(), create_open, InlineHandler, timeout=10),
])
loop = asyncio.get_event_loop()

loop.create_task(MessageLoop(bot).run_forever())
print('Listening ...')

loop.run_forever()
