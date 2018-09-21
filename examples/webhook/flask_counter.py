import sys
from flask import Flask, request
import amanobot
from amanobot.loop import OrderedWebhook
from amanobot.delegate import per_chat_id, create_open, pave_event_space

"""
$ python3 flask_counter.py <token> <listening_port> <webhook_url>

Webhook path is '/webhook', therefore:

<webhook_url>: https://<base>/webhook
"""

class MessageCounter(amanobot.helper.ChatHandler):
    def __init__(self, *args, **kwargs):
        super(MessageCounter, self).__init__(*args, **kwargs)
        self._count = 0

    def on_chat_message(self, msg):
        self._count += 1
        self.sender.sendMessage(self._count)


TOKEN = sys.argv[1]
PORT = int(sys.argv[2])
URL = sys.argv[3]

app = Flask(__name__)

bot = amanobot.DelegatorBot(TOKEN, [
    pave_event_space()(
        per_chat_id(), create_open, MessageCounter, timeout=10),
])

webhook = OrderedWebhook(bot)

@app.route('/webhook', methods=['GET', 'POST'])
def pass_update():
    webhook.feed(request.data)
    return 'OK'

if __name__ == '__main__':
    try:
        bot.setWebhook(URL)
    # Sometimes it would raise this error, but webhook still set successfully.
    except amanobot.exception.TooManyRequestsError:
        pass

    webhook.run_as_thread()
    app.run(port=PORT, debug=True)
