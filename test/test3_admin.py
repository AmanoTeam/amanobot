import sys
import time
import amanobot
import amanobot.namedtuple
from amanobot.routing import by_content_type, make_content_type_routing_table
from amanobot.exception import NotEnoughRightsError

class AdminBot(amanobot.Bot):
    def on_chat_message(self, msg):
        content_type, chat_type, chat_id = amanobot.glance(msg)

        if 'edit_date' not in msg:
            self.sendMessage(chat_id, 'Edit the message, please.')
        else:
            self.sendMessage(chat_id, 'Add me to a group, please.')

            # Make a router to route `new_chat_member` and `left_chat_member`
            r = amanobot.helper.Router(by_content_type(), make_content_type_routing_table(self))

            # Replace current handler with that router
            self._router.routing_table['chat'] = r.route

    def on_new_chat_member(self, msg, new_chat_member):
        print('New chat member:', new_chat_member)
        content_type, chat_type, chat_id = amanobot.glance(msg)

        r = self.getChat(chat_id)
        print(r)

        r = self.getChatAdministrators(chat_id)
        print(r)
        print(amanobot.namedtuple.ChatMemberArray(r))

        r = self.getChatMembersCount(chat_id)
        print(r)

        while 1:
            try:
                self.setChatTitle(chat_id, 'AdminBot Title')
                print('Set title successfully.')
                break
            except NotEnoughRightsError:
                print('No right to set title. Try again in 10 seconds ...')
                time.sleep(10)

        while 1:
            try:
                self.setChatPhoto(chat_id, open('gandhi.png', 'rb'))
                print('Set photo successfully.')
                time.sleep(2)  # let tester see photo briefly
                break
            except NotEnoughRightsError:
                print('No right to set photo. Try again in 10 seconds ...')
                time.sleep(10)

        while 1:
            try:
                self.deleteChatPhoto(chat_id)
                print('Delete photo successfully.')
                break
            except NotEnoughRightsError:
                print('No right to delete photo. Try again in 10 seconds ...')
                time.sleep(10)

        print('I am done. Remove me from the group.')

    @staticmethod
    def on_left_chat_member(msg, left_chat_member):
        print('I see that I have left.')


TOKEN = sys.argv[1]

bot = AdminBot(TOKEN)
bot.message_loop()
print('Send me a text message ...')

while 1:
    time.sleep(1)
