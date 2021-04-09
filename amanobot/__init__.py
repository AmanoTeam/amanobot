import bisect
import collections
import inspect
import io
import json
import queue
import threading
import time
import logging
import traceback
from typing import Union

from . import exception

__version__ = '2.1.0'


def flavor(msg):
    """
    Return flavor of message or event.

    A message's flavor may be one of these:

    - ``chat``
    - ``callback_query``
    - ``inline_query``
    - ``chosen_inline_result``
    - ``shipping_query``
    - ``pre_checkout_query``

    An event's flavor is determined by the single top-level key.
    """
    if 'message_id' in msg:
        return 'chat'
    if 'id' in msg and 'chat_instance' in msg:
        return 'callback_query'
    if 'id' in msg and 'query' in msg:
        return 'inline_query'
    if 'result_id' in msg:
        return 'chosen_inline_result'
    if 'id' in msg and 'shipping_address' in msg:
        return 'shipping_query'
    if 'id' in msg and 'total_amount' in msg:
        return 'pre_checkout_query'
    top_keys = list(msg.keys())
    if len(top_keys) == 1:
        return top_keys[0]

    raise exception.BadFlavor(msg)


chat_flavors = ['chat']
inline_flavors = ['inline_query', 'chosen_inline_result']


def _find_first_key(d, keys):
    for k in keys:
        if k in d:
            return k
    logging.error('No suggested keys %s in %s', str(keys), str(d))
    # Gets the first key after the update_id one.
    return list(d.keys())[1]


all_content_types = [
    'text', 'audio', 'animation', 'document', 'game', 'photo', 'sticker', 'video', 'voice',
    'video_note', 'contact', 'poll', 'location', 'venue', 'new_chat_member', 'left_chat_member',
    'new_chat_title', 'new_chat_photo', 'delete_chat_photo', 'group_chat_created', 'supergroup_chat_created',
    'channel_chat_created', 'migrate_to_chat_id', 'migrate_from_chat_id', 'pinned_message',
    'new_chat_members', 'invoice', 'successful_payment'
]


def glance(msg, flavor='chat', long=False):
    """
    Extract "headline" info about a message.
    Use parameter ``long`` to control whether a short or long tuple is returned.

    When ``flavor`` is ``chat``
    (``msg`` being a `Message <https://core.telegram.org/bots/api#message>`_ object):

    - short: (content_type, ``msg['chat']['type']``, ``msg['chat']['id']``)
    - long: (content_type, ``msg['chat']['type']``, ``msg['chat']['id']``, ``msg['date']``, ``msg['message_id']``)

    *content_type* can be: ``text``, ``audio``, ``document``, ``game``, ``photo``, ``sticker``, ``video``, ``voice``,
    ``video_note``, ``contact``, ``location``, ``venue``, ``new_chat_member``, ``left_chat_member``, ``new_chat_title``,
    ``new_chat_photo``, ``delete_chat_photo``, ``group_chat_created``, ``supergroup_chat_created``,
    ``channel_chat_created``, ``migrate_to_chat_id``, ``migrate_from_chat_id``, ``pinned_message``,
    ``new_chat_members``, ``invoice``, ``successful_payment``.

    When ``flavor`` is ``callback_query``
    (``msg`` being a `CallbackQuery <https://core.telegram.org/bots/api#callbackquery>`_ object):

    - regardless: (``msg['id']``, ``msg['from']['id']``, ``msg['data']``)

    When ``flavor`` is ``inline_query``
    (``msg`` being a `InlineQuery <https://core.telegram.org/bots/api#inlinequery>`_ object):

    - short: (``msg['id']``, ``msg['from']['id']``, ``msg['query']``)
    - long: (``msg['id']``, ``msg['from']['id']``, ``msg['query']``, ``msg['offset']``)

    When ``flavor`` is ``chosen_inline_result``
    (``msg`` being a `ChosenInlineResult <https://core.telegram.org/bots/api#choseninlineresult>`_ object):

    - regardless: (``msg['result_id']``, ``msg['from']['id']``, ``msg['query']``)

    When ``flavor`` is ``shipping_query``
    (``msg`` being a `ShippingQuery <https://core.telegram.org/bots/api#shippingquery>`_ object):

    - regardless: (``msg['id']``, ``msg['from']['id']``, ``msg['invoice_payload']``)

    When ``flavor`` is ``pre_checkout_query``
    (``msg`` being a `PreCheckoutQuery <https://core.telegram.org/bots/api#precheckoutquery>`_ object):

    - short: (``msg['id']``, ``msg['from']['id']``, ``msg['invoice_payload']``)
    - long: (``msg['id']``, ``msg['from']['id']``, ``msg['invoice_payload']``, ``msg['currency']``, ``msg['total_amount']``)
    """

    def gl_chat():
        content_type = _find_first_key(msg, all_content_types)

        if long:
            return content_type, msg['chat']['type'], msg['chat']['id'], msg['date'], msg['message_id']
        return content_type, msg['chat']['type'], msg['chat']['id']

    def gl_callback_query():
        return msg['id'], msg['from']['id'], msg['data']

    def gl_inline_query():
        if long:
            return msg['id'], msg['from']['id'], msg['query'], msg['offset']
        return msg['id'], msg['from']['id'], msg['query']

    def gl_chosen_inline_result():
        return msg['result_id'], msg['from']['id'], msg['query']

    def gl_shipping_query():
        return msg['id'], msg['from']['id'], msg['invoice_payload']

    def gl_pre_checkout_query():
        if long:
            return msg['id'], msg['from']['id'], msg['invoice_payload'], msg['currency'], msg['total_amount']
        return msg['id'], msg['from']['id'], msg['invoice_payload']

    try:
        fn = {'chat': gl_chat,
              'callback_query': gl_callback_query,
              'inline_query': gl_inline_query,
              'chosen_inline_result': gl_chosen_inline_result,
              'shipping_query': gl_shipping_query,
              'pre_checkout_query': gl_pre_checkout_query}[flavor]
    except KeyError:
        raise exception.BadFlavor(flavor)

    return fn()


def flance(msg, long=False):
    """
    A combination of :meth:`amanobot.flavor` and :meth:`amanobot.glance`,
    return a 2-tuple (flavor, headline_info), where *headline_info* is whatever extracted by
    :meth:`amanobot.glance` depending on the message flavor and the ``long`` parameter.
    """
    f = flavor(msg)
    g = glance(msg, flavor=f, long=long)
    return f, g


def peel(event):
    """
    Remove an event's top-level skin (where its flavor is determined), and return
    the core content.
    """
    return list(event.values())[0]


def fleece(event):
    """
    A combination of :meth:`amanobot.flavor` and :meth:`amanobot.peel`,
    return a 2-tuple (flavor, content) of an event.
    """
    return flavor(event), peel(event)


def is_event(msg):
    """
    Return whether the message looks like an event. That is, whether it has a flavor
    that starts with an underscore.
    """
    return flavor(msg).startswith('_')


def origin_identifier(msg):
    """
    Extract the message identifier of a callback query's origin. Returned value
    is guaranteed to be a tuple.

    ``msg`` is expected to be ``callback_query``.
    """
    if 'message' in msg:
        return msg['message']['chat']['id'], msg['message']['message_id']
    if 'inline_message_id' in msg:
        return msg['inline_message_id'],
    raise ValueError()


def message_identifier(msg):
    """
    Extract an identifier for message editing. Useful with :meth:`amanobot.Bot.editMessageText`
    and similar methods. Returned value is guaranteed to be a tuple.

    ``msg`` is expected to be ``chat`` or ``choson_inline_result``.
    """
    if 'chat' in msg and 'message_id' in msg:
        return msg['chat']['id'], msg['message_id']
    if 'inline_message_id' in msg:
        return msg['inline_message_id'],
    raise ValueError()


def _dismantle_message_identifier(f):
    if isinstance(f, tuple):
        if len(f) == 2:
            return {'chat_id': f[0], 'message_id': f[1]}
        if len(f) == 1:
            return {'inline_message_id': f[0]}
        raise ValueError()
    return {'inline_message_id': f}


def _split_input_media_array(media_array):
    def ensure_dict(input_media):
        if isinstance(input_media, tuple) and hasattr(input_media, '_asdict'):
            return input_media._asdict()
        if isinstance(input_media, dict):
            return input_media
        raise ValueError()

    def given_attach_name(input_media):
        if isinstance(input_media['media'], tuple):
            return input_media['media'][0]
        return None

    def attach_name_generator(used_names):
        x = 0
        while 1:
            x += 1
            name = 'media' + str(x)
            if name in used_names:
                continue
            yield name

    def split_media(input_media, name_generator):
        file_spec = input_media['media']

        # file_id, URL
        if _isstring(file_spec):
            return input_media, None

        # file-object
        # (attach-name, file-object)
        # (attach-name, (filename, file-object))
        if isinstance(file_spec, tuple):
            name, f = file_spec
        else:
            name, f = next(name_generator), file_spec

        m = input_media.copy()
        m['media'] = 'attach://' + name

        return (m, (name, f))

    ms = [ensure_dict(m) for m in media_array]

    used_names = [given_attach_name(m) for m in ms if given_attach_name(m) is not None]
    name_generator = attach_name_generator(used_names)

    splitted = [split_media(m, name_generator) for m in ms]

    legal_media, attachments = map(list, zip(*splitted))
    files_to_attach = dict([a for a in attachments if a is not None])

    return legal_media, files_to_attach


def _isstring(s):
    return isinstance(s, str)


def _isfile(f):
    return isinstance(f, io.IOBase)


from . import helper


def flavor_router(routing_table):
    router = helper.Router(flavor, routing_table)
    return router.route


class _BotBase:
    def __init__(self, token: str, raise_errors: bool, api_endpoint: str):
        self._token = token
        self._raise_errors = raise_errors
        self._base_url = api_endpoint
        self._file_chunk_size = 65536


def _strip(params, more=None):
    if more is None:
        more = []
    return {key: value for key, value in params.items() if key not in ['self'] + more}


def _rectify(params):
    def make_jsonable(value):
        if isinstance(value, list):
            return [make_jsonable(v) for v in value]
        if isinstance(value, dict):
            return {k: make_jsonable(v) for k, v in value.items() if v is not None}
        if isinstance(value, tuple) and hasattr(value, '_asdict'):
            return {k: make_jsonable(v) for k, v in value._asdict().items() if v is not None}
        return value

    def flatten(value):
        v = make_jsonable(value)

        if isinstance(v, (dict, list)):
            return json.dumps(v, separators=(',', ':'))
        return v

    # remove None, then json-serialize if needed
    return {k: flatten(v) for k, v in params.items() if v is not None}


from . import api


class Bot(_BotBase):
    class Scheduler(threading.Thread):
        # A class that is sorted by timestamp. Use `bisect` module to ensure order in event queue.
        Event = collections.namedtuple('Event', ['timestamp', 'data'])
        Event.__eq__ = lambda self, other: self.timestamp == other.timestamp
        Event.__ne__ = lambda self, other: self.timestamp != other.timestamp
        Event.__gt__ = lambda self, other: self.timestamp > other.timestamp
        Event.__ge__ = lambda self, other: self.timestamp >= other.timestamp
        Event.__lt__ = lambda self, other: self.timestamp < other.timestamp
        Event.__le__ = lambda self, other: self.timestamp <= other.timestamp

        def __init__(self):
            super(Bot.Scheduler, self).__init__()
            self._eventq = []
            self._lock = threading.RLock()  # reentrant lock to allow locked method calling locked method
            self._event_handler = None

        def _locked(fn):
            def k(self, *args, **kwargs):
                with self._lock:
                    return fn(self, *args, **kwargs)

            return k

        @_locked
        def _insert_event(self, data, when):
            ev = self.Event(when, data)
            bisect.insort(self._eventq, ev)
            return ev

        @_locked
        def _remove_event(self, event):
            # Find event according to its timestamp.
            # Index returned should be one behind.
            i = bisect.bisect(self._eventq, event)

            # Having two events with identical timestamp is unlikely but possible.
            # I am going to move forward and compare timestamp AND object address
            # to make sure the correct object is found.

            while i > 0:
                i -= 1
                e = self._eventq[i]

                if e.timestamp != event.timestamp:
                    raise exception.EventNotFound(event)
                if id(e) == id(event):
                    self._eventq.pop(i)
                    return

            raise exception.EventNotFound(event)

        @_locked
        def _pop_expired_event(self):
            if not self._eventq:
                return None

            if self._eventq[0].timestamp <= time.time():
                return self._eventq.pop(0)
            return None

        def event_at(self, when, data):
            """
            Schedule some data to emit at an absolute timestamp.

            :type when: int or float
            :type data: dictionary
            :return: an internal Event object
            """
            return self._insert_event(data, when)

        def event_later(self, delay, data):
            """
            Schedule some data to emit after a number of seconds.

            :type delay: int or float
            :type data: dictionary
            :return: an internal Event object
            """
            return self._insert_event(data, time.time() + delay)

        def event_now(self, data):
            """
            Emit some data as soon as possible.

            :type data: dictionary
            :return: an internal Event object
            """
            return self._insert_event(data, time.time())

        def cancel(self, event):
            """
            Cancel an event.

            :type event: an internal Event object
            """
            self._remove_event(event)

        def run(self):
            while 1:
                e = self._pop_expired_event()
                while e:
                    if callable(e.data):
                        d = e.data()  # call the data-producing function
                        if d is not None:
                            self._event_handler(d)
                    else:
                        self._event_handler(e.data)

                    e = self._pop_expired_event()
                time.sleep(0.1)

        def run_as_thread(self):
            self.daemon = True
            self.start()

        def on_event(self, fn):
            self._event_handler = fn

    def __init__(self, token: str, raise_errors: bool = True, api_endpoint: str = "https://api.telegram.org"):
        super(Bot, self).__init__(token, raise_errors, api_endpoint)

        self._scheduler = self.Scheduler()

        self._router = helper.Router(flavor, {'chat': lambda msg: self.on_chat_message(msg),
                                              'callback_query': lambda msg: self.on_callback_query(msg),
                                              'inline_query': lambda msg: self.on_inline_query(msg),
                                              'chosen_inline_result': lambda msg: self.on_chosen_inline_result(msg)})
        # use lambda to delay evaluation of self.on_ZZZ to runtime because
        # I don't want to require defining all methods right here.

    @property
    def scheduler(self):
        return self._scheduler

    @property
    def router(self):
        return self._router

    def handle(self, msg):
        self._router.route(msg)

    def _api_request(self, method, params=None, files=None, raise_errors=None, **kwargs):
        return api.request((self._base_url, self._token, method, params, files),
                           raise_errors=raise_errors if raise_errors is not None else self._raise_errors, **kwargs)

    def _api_request_with_file(self, method, params, files, **kwargs):
        params.update({
            k: v for k, v in files.items() if _isstring(v)})

        files = {
            k: v for k, v in files.items() if v is not None and not _isstring(v)}

        return self._api_request(method, _rectify(params), files, **kwargs)

    def getMe(self):
        """ See: https://core.telegram.org/bots/api#getme """
        return self._api_request('getMe')

    def logOut(self):
        """ See: https://core.telegram.org/bots/api#logout """
        return self._api_request('logOut')

    def close(self):
        """ See: https://core.telegram.org/bots/api#close """
        return self._api_request('close')

    def sendMessage(self, chat_id: Union[int, str], text: str,
                    parse_mode: str = None,
                    entities=None,
                    disable_web_page_preview: bool = None,
                    disable_notification: bool = None,
                    reply_to_message_id: int = None,
                    allow_sending_without_reply: bool = None,
                    reply_markup=None):
        """ See: https://core.telegram.org/bots/api#sendmessage """
        p = _strip(locals())
        return self._api_request('sendMessage', _rectify(p))

    def forwardMessage(self, chat_id: Union[int, str], from_chat_id: Union[int, str], message_id: int,
                       disable_notification: bool = None):
        """ See: https://core.telegram.org/bots/api#forwardmessage """
        p = _strip(locals())
        return self._api_request('forwardMessage', _rectify(p))

    def copyMessage(self, chat_id: Union[int, str], from_chat_id: Union[int, str], message_id: int,
                    caption: str = None,
                    parse_mode: str = None,
                    caption_entities=None,
                    disable_notification: bool = None,
                    reply_to_message_id: int = None,
                    allow_sending_without_reply: bool = None,
                    reply_markup=None):
        """ See: https://core.telegram.org/bots/api#copymessage """
        p = _strip(locals())
        return self._api_request('copyMessage', _rectify(p))

    def sendPhoto(self, chat_id: Union[int, str], photo,
                  caption: str = None,
                  parse_mode: str = None,
                  caption_entities=None,
                  disable_notification: bool = None,
                  reply_to_message_id: int = None,
                  allow_sending_without_reply: bool = None,
                  reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#sendphoto

        :param photo:
            - string: ``file_id`` for a photo existing on Telegram servers
            - string: HTTP URL of a photo from the Internet
            - file-like object: obtained by ``open(path, 'rb')``
            - tuple: (filename, file-like object).
        """
        p = _strip(locals(), more=['photo'])
        return self._api_request_with_file('sendPhoto', _rectify(p), {'photo': photo})

    def sendAudio(self, chat_id: Union[int, str], audio,
                  caption: str = None,
                  parse_mode: str = None,
                  caption_entities=None,
                  duration=None,
                  performer=None,
                  title=None,
                  thumb=None,
                  disable_notification: bool = None,
                  reply_to_message_id: int = None,
                  allow_sending_without_reply: bool = None,
                  reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#sendaudio

        :param audio: Same as ``photo`` in :meth:`amanobot.Bot.sendPhoto`
        """
        p = _strip(locals(), more=['audio', 'thumb'])
        return self._api_request_with_file('sendAudio', _rectify(p), {'audio': audio, 'thumb': thumb})

    def sendDocument(self, chat_id: Union[int, str], document,
                     thumb=None,
                     caption: str = None,
                     parse_mode: str = None,
                     caption_entities=None,
                     disable_content_type_detection=None,
                     disable_notification: bool = None,
                     reply_to_message_id: int = None,
                     allow_sending_without_reply: bool = None,
                     reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#senddocument

        :param document: Same as ``photo`` in :meth:`amanobot.Bot.sendPhoto`
        """
        p = _strip(locals(), more=['document', 'thumb'])
        return self._api_request_with_file('sendDocument', _rectify(p), {'document': document, 'thumb': thumb})

    def sendVideo(self, chat_id: Union[int, str], video,
                  duration=None,
                  width=None,
                  height=None,
                  thumb=None,
                  caption: str = None,
                  parse_mode: str = None,
                  caption_entities=None,
                  supports_streaming=None,
                  disable_notification: bool = None,
                  reply_to_message_id: int = None,
                  allow_sending_without_reply: bool = None,
                  reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#sendvideo

        :param video: Same as ``photo`` in :meth:`amanobot.Bot.sendPhoto`
        """
        p = _strip(locals(), more=['video', 'thumb'])
        return self._api_request_with_file('sendVideo', _rectify(p), {'video': video, 'thumb': thumb})

    def sendAnimation(self, chat_id: Union[int, str], animation,
                      duration=None,
                      width=None,
                      height=None,
                      thumb=None,
                      caption: str = None,
                      parse_mode: str = None,
                      caption_entities=None,
                      disable_notification: bool = None,
                      reply_to_message_id: int = None,
                      allow_sending_without_reply: bool = None,
                      reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#sendanimation

        :param animation: Same as ``photo`` in :meth:`amanobot.Bot.sendPhoto`
        """
        p = _strip(locals(), more=['animation', 'thumb'])
        return self._api_request_with_file('sendAnimation', _rectify(p), {'animation': animation, 'thumb': thumb})

    def sendVoice(self, chat_id: Union[int, str], voice,
                  caption: str = None,
                  parse_mode: str = None,
                  caption_entities=None,
                  duration=None,
                  disable_notification: bool = None,
                  reply_to_message_id: int = None,
                  allow_sending_without_reply: bool = None,
                  reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#sendvoice

        :param voice: Same as ``photo`` in :meth:`amanobot.Bot.sendPhoto`
        """
        p = _strip(locals(), more=['voice'])
        return self._api_request_with_file('sendVoice', _rectify(p), {'voice': voice})

    def sendVideoNote(self, chat_id: Union[int, str], video_note,
                      duration=None,
                      length=None,
                      thumb=None,
                      disable_notification: bool = None,
                      reply_to_message_id: int = None,
                      allow_sending_without_reply: bool = None,
                      reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#sendvideonote

        :param video_note: Same as ``photo`` in :meth:`amanobot.Bot.sendPhoto`

        :param length:
            Although marked as optional, this method does not seem to work without
            it being specified. Supply any integer you want. It seems to have no effect
            on the video note's display size.
        """
        p = _strip(locals(), more=['video_note', 'thumb'])
        return self._api_request_with_file('sendVideoNote', _rectify(p), {'video_note': video_note, 'thumb': thumb})

    def sendMediaGroup(self, chat_id: Union[int, str], media,
                       disable_notification: bool = None,
                       reply_to_message_id: int = None,
                       allow_sending_without_reply: bool = None):
        """
        See: https://core.telegram.org/bots/api#sendmediagroup

        :type media: array of `InputMedia <https://core.telegram.org/bots/api#inputmedia>`_ objects
        :param media:
            To indicate media locations, each InputMedia object's ``media`` field
            should be one of these:

            - string: ``file_id`` for a file existing on Telegram servers
            - string: HTTP URL of a file from the Internet
            - file-like object: obtained by ``open(path, 'rb')``
            - tuple: (form-data name, file-like object)
            - tuple: (form-data name, (filename, file-like object))

            In case of uploading, you may supply customized multipart/form-data
            names for each uploaded file (as in last 2 options above). Otherwise,
            amanobot assigns unique names to each uploaded file. Names assigned by
            amanobot will not collide with user-supplied names, if any.
        """
        p = _strip(locals(), more=['media'])
        legal_media, files_to_attach = _split_input_media_array(media)

        p['media'] = legal_media
        return self._api_request('sendMediaGroup', _rectify(p), files_to_attach)

    def sendLocation(self, chat_id: Union[int, str], latitude, longitude,
                     horizontal_accuracy=None,
                     live_period=None,
                     heading=None,
                     proximity_alert_radius=None,
                     disable_notification: bool = None,
                     reply_to_message_id: int = None,
                     allow_sending_without_reply: bool = None,
                     reply_markup=None):
        """ See: https://core.telegram.org/bots/api#sendlocation """
        p = _strip(locals())
        return self._api_request('sendLocation', _rectify(p))

    def editMessageLiveLocation(self, msg_identifier, latitude, longitude,
                                horizontal_accuracy=None,
                                heading=None,
                                proximity_alert_radius=None,
                                reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#editmessagelivelocation

        :param msg_identifier: Same as in :meth:`.Bot.editMessageText`
        """
        p = _strip(locals(), more=['msg_identifier'])
        p.update(_dismantle_message_identifier(msg_identifier))
        return self._api_request('editMessageLiveLocation', _rectify(p))

    def stopMessageLiveLocation(self, msg_identifier,
                                reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#stopmessagelivelocation

        :param msg_identifier: Same as in :meth:`.Bot.editMessageText`
        """
        p = _strip(locals(), more=['msg_identifier'])
        p.update(_dismantle_message_identifier(msg_identifier))
        return self._api_request('stopMessageLiveLocation', _rectify(p))

    def sendVenue(self, chat_id: Union[int, str], latitude, longitude, title, address,
                  foursquare_id=None,
                  foursquare_type=None,
                  disable_notification: bool = None,
                  reply_to_message_id: int = None,
                  allow_sending_without_reply: bool = None,
                  reply_markup=None):
        """ See: https://core.telegram.org/bots/api#sendvenue """
        p = _strip(locals())
        return self._api_request('sendVenue', _rectify(p))

    def sendContact(self, chat_id: Union[int, str], phone_number, first_name,
                    last_name=None,
                    vcard=None,
                    disable_notification: bool = None,
                    reply_to_message_id: int = None,
                    allow_sending_without_reply: bool = None,
                    reply_markup=None):
        """ See: https://core.telegram.org/bots/api#sendcontact """
        p = _strip(locals())
        return self._api_request('sendContact', _rectify(p))

    def sendPoll(self, chat_id: Union[int, str], question, options,
                 is_anonymous=None,
                 type=None,
                 allows_multiple_answers=None,
                 correct_option_id=None,
                 explanation=None,
                 explanation_parse_mode: str = None,
                 open_period=None,
                 is_closed=None,
                 disable_notification: bool = None,
                 reply_to_message_id: int = None,
                 allow_sending_without_reply: bool = None,
                 reply_markup=None):
        """ See: https://core.telegram.org/bots/api#sendpoll """
        p = _strip(locals())
        return self._api_request('sendPoll', _rectify(p))

    def sendDice(self, chat_id: Union[int, str],
                 emoji=None,
                 disable_notification: bool = None,
                 reply_to_message_id: int = None,
                 allow_sending_without_reply: bool = None,
                 reply_markup=None):
        """ See: https://core.telegram.org/bots/api#senddice """
        p = _strip(locals())
        return self._api_request('sendDice', _rectify(p))

    def sendGame(self, chat_id: Union[int, str], game_short_name,
                 disable_notification: bool = None,
                 reply_to_message_id: int = None,
                 allow_sending_without_reply: bool = None,
                 reply_markup=None):
        """ See: https://core.telegram.org/bots/api#sendgame """
        p = _strip(locals())
        return self._api_request('sendGame', _rectify(p))

    def sendInvoice(self, chat_id: Union[int, str], title, description, payload,
                    provider_token, start_parameter, currency, prices,
                    provider_data=None,
                    photo_url=None,
                    photo_size=None,
                    photo_width=None,
                    photo_height=None,
                    need_name=None,
                    need_phone_number=None,
                    need_email=None,
                    need_shipping_address=None,
                    is_flexible=None,
                    disable_notification: bool = None,
                    reply_to_message_id: int = None,
                    allow_sending_without_reply: bool = None,
                    reply_markup=None):
        """ See: https://core.telegram.org/bots/api#sendinvoice """
        p = _strip(locals())
        return self._api_request('sendInvoice', _rectify(p))

    def sendChatAction(self, chat_id: Union[int, str], action):
        """ See: https://core.telegram.org/bots/api#sendchataction """
        p = _strip(locals())
        return self._api_request('sendChatAction', _rectify(p))

    def getUserProfilePhotos(self, user_id,
                             offset=None,
                             limit=None):
        """ See: https://core.telegram.org/bots/api#getuserprofilephotos """
        p = _strip(locals())
        return self._api_request('getUserProfilePhotos', _rectify(p))

    def getFile(self, file_id):
        """ See: https://core.telegram.org/bots/api#getfile """
        p = _strip(locals())
        return self._api_request('getFile', _rectify(p))

    def kickChatMember(self, chat_id: Union[int, str], user_id,
                       until_date: int = None,
                       revoke_messages: bool = None):
        """ See: https://core.telegram.org/bots/api#kickchatmember """
        p = _strip(locals())
        return self._api_request('kickChatMember', _rectify(p))

    def unbanChatMember(self, chat_id: Union[int, str], user_id,
                        only_if_banned=None):
        """ See: https://core.telegram.org/bots/api#unbanchatmember """
        p = _strip(locals())
        return self._api_request('unbanChatMember', _rectify(p))

    def restrictChatMember(self, chat_id: Union[int, str], user_id,
                           until_date=None,
                           can_send_messages=None,
                           can_send_media_messages=None,
                           can_send_polls=None,
                           can_send_other_messages=None,
                           can_add_web_page_previews=None,
                           can_change_info=None,
                           can_invite_users=None,
                           can_pin_messages=None,
                           permissions=None):
        """ See: https://core.telegram.org/bots/api#restrictchatmember """
        if not isinstance(permissions, dict):
            permissions = dict(can_send_messages=can_send_messages,
                               can_send_media_messages=can_send_media_messages,
                               can_send_polls=can_send_polls,
                               can_send_other_messages=can_send_other_messages,
                               can_add_web_page_previews=can_add_web_page_previews,
                               can_change_info=can_change_info,
                               can_invite_users=can_invite_users,
                               can_pin_messages=can_pin_messages)
        p = _strip(locals())
        return self._api_request('restrictChatMember', _rectify(p))

    def promoteChatMember(self, chat_id: Union[int, str], user_id,
                          is_anonymous=None,
                          can_manage_chat=None,
                          can_post_messages=None,
                          can_edit_messages=None,
                          can_delete_messages=None,
                          can_manage_voice_chats=None,
                          can_restrict_members=None,
                          can_promote_members=None,
                          can_change_info=None,
                          can_invite_users=None,
                          can_pin_messages=None):
        """ See: https://core.telegram.org/bots/api#promotechatmember """
        p = _strip(locals())
        return self._api_request('promoteChatMember', _rectify(p))

    def setChatAdministratorCustomTitle(self, chat_id: Union[int, str], user_id,
                                        custom_title):
        """ See: https://core.telegram.org/bots/api#setchatadministratorcustomtitle """
        p = _strip(locals())
        return self._api_request('setChatAdministratorCustomTitle', _rectify(p))

    def setChatPermissions(self, chat_id: Union[int, str],
                           can_send_messages=None,
                           can_send_media_messages=None,
                           can_send_polls=None,
                           can_send_other_messages=None,
                           can_add_web_page_previews=None,
                           can_change_info=None,
                           can_invite_users=None,
                           can_pin_messages=None,
                           permissions=None):
        """ See: https://core.telegram.org/bots/api#setchatpermissions """
        if not isinstance(permissions, dict):
            permissions = dict(can_send_messages=can_send_messages,
                               can_send_media_messages=can_send_media_messages,
                               can_send_polls=can_send_polls,
                               can_send_other_messages=can_send_other_messages,
                               can_add_web_page_previews=can_add_web_page_previews,
                               can_change_info=can_change_info,
                               can_invite_users=can_invite_users,
                               can_pin_messages=can_pin_messages)
        p = _strip(locals())
        return self._api_request('setChatPermissions', _rectify(p))

    def exportChatInviteLink(self, chat_id):
        """ See: https://core.telegram.org/bots/api#exportchatinvitelink """
        p = _strip(locals())
        return self._api_request('exportChatInviteLink', _rectify(p))

    def createChatInviteLink(self, chat_id,
                             expire_date: int = None,
                             member_limit: int = None):
        """ See: https://core.telegram.org/bots/api#createchatinvitelink """
        p = _strip(locals())
        return self._api_request('createChatInviteLink', _rectify(p))

    def editChatInviteLink(self, chat_id,
                           invite_link: str,
                           expire_date: int = None,
                           member_limit: int = None):
        """ See: https://core.telegram.org/bots/api#editchatinvitelink """
        p = _strip(locals())
        return self._api_request('editChatInviteLink', _rectify(p))

    def revokeChatInviteLink(self, chat_id, invite_link: str):
        """ See: https://core.telegram.org/bots/api#revokechatinvitelink """
        p = _strip(locals())
        return self._api_request('revokeChatInviteLink', _rectify(p))

    def setChatPhoto(self, chat_id: Union[int, str], photo):
        """ See: https://core.telegram.org/bots/api#setchatphoto """
        p = _strip(locals(), more=['photo'])
        return self._api_request_with_file('setChatPhoto', _rectify(p), {'photo': photo})

    def deleteChatPhoto(self, chat_id):
        """ See: https://core.telegram.org/bots/api#deletechatphoto """
        p = _strip(locals())
        return self._api_request('deleteChatPhoto', _rectify(p))

    def setChatTitle(self, chat_id: Union[int, str], title):
        """ See: https://core.telegram.org/bots/api#setchattitle """
        p = _strip(locals())
        return self._api_request('setChatTitle', _rectify(p))

    def setChatDescription(self, chat_id: Union[int, str],
                           description=None):
        """ See: https://core.telegram.org/bots/api#setchatdescription """
        p = _strip(locals())
        return self._api_request('setChatDescription', _rectify(p))

    def pinChatMessage(self, chat_id: Union[int, str], message_id: int,
                       disable_notification: bool = None):
        """ See: https://core.telegram.org/bots/api#pinchatmessage """
        p = _strip(locals())
        return self._api_request('pinChatMessage', _rectify(p))

    def unpinChatMessage(self, chat_id: Union[int, str],
                         message_id=None):
        """ See: https://core.telegram.org/bots/api#unpinchatmessage """
        p = _strip(locals())
        return self._api_request('unpinChatMessage', _rectify(p))

    def unpinAllChatMessages(self, chat_id):
        """ See: https://core.telegram.org/bots/api#unpinallchatmessages """
        p = _strip(locals())
        return self._api_request('unpinAllChatMessages', _rectify(p))

    def leaveChat(self, chat_id):
        """ See: https://core.telegram.org/bots/api#leavechat """
        p = _strip(locals())
        return self._api_request('leaveChat', _rectify(p))

    def getChat(self, chat_id):
        """ See: https://core.telegram.org/bots/api#getchat """
        p = _strip(locals())
        return self._api_request('getChat', _rectify(p))

    def getChatAdministrators(self, chat_id):
        """ See: https://core.telegram.org/bots/api#getchatadministrators """
        p = _strip(locals())
        return self._api_request('getChatAdministrators', _rectify(p))

    def getChatMembersCount(self, chat_id):
        """ See: https://core.telegram.org/bots/api#getchatmemberscount """
        p = _strip(locals())
        return self._api_request('getChatMembersCount', _rectify(p))

    def getChatMember(self, chat_id: Union[int, str], user_id):
        """ See: https://core.telegram.org/bots/api#getchatmember """
        p = _strip(locals())
        return self._api_request('getChatMember', _rectify(p))

    def setChatStickerSet(self, chat_id: Union[int, str], sticker_set_name):
        """ See: https://core.telegram.org/bots/api#setchatstickerset """
        p = _strip(locals())
        return self._api_request('setChatStickerSet', _rectify(p))

    def deleteChatStickerSet(self, chat_id):
        """ See: https://core.telegram.org/bots/api#deletechatstickerset """
        p = _strip(locals())
        return self._api_request('deleteChatStickerSet', _rectify(p))

    def answerCallbackQuery(self, callback_query_id,
                            text=None,
                            show_alert=None,
                            url=None,
                            cache_time=None):
        """ See: https://core.telegram.org/bots/api#answercallbackquery """
        p = _strip(locals())
        return self._api_request('answerCallbackQuery', _rectify(p))

    def setMyCommands(self, commands=None):
        """ See: https://core.telegram.org/bots/api#setmycommands """
        if commands is None:
            commands = []
        p = _strip(locals())
        return self._api_request('setMyCommands', _rectify(p))

    def getMyCommands(self):
        """ See: https://core.telegram.org/bots/api#getmycommands """
        return self._api_request('getMyCommands')

    def setPassportDataErrors(self, user_id, errors):
        """ See: https://core.telegram.org/bots/api#setpassportdataerrors """
        p = _strip(locals())
        return self._api_request('setPassportDataErrors', _rectify(p))

    def answerShippingQuery(self, shipping_query_id, ok,
                            shipping_options=None,
                            error_message=None):
        """ See: https://core.telegram.org/bots/api#answershippingquery """
        p = _strip(locals())
        return self._api_request('answerShippingQuery', _rectify(p))

    def answerPreCheckoutQuery(self, pre_checkout_query_id, ok,
                               error_message=None):
        """ See: https://core.telegram.org/bots/api#answerprecheckoutquery """
        p = _strip(locals())
        return self._api_request('answerPreCheckoutQuery', _rectify(p))

    def editMessageText(self, msg_identifier, text: str,
                        parse_mode: str = None,
                        entities=None,
                        disable_web_page_preview: bool = None,
                        reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#editmessagetext

        :param msg_identifier:
            a 2-tuple (``chat_id``, ``message_id``),
            a 1-tuple (``inline_message_id``),
            or simply ``inline_message_id``.
            You may extract this value easily with :meth:`amanobot.message_identifier`
        """
        p = _strip(locals(), more=['msg_identifier'])
        p.update(_dismantle_message_identifier(msg_identifier))
        return self._api_request('editMessageText', _rectify(p))

    def editMessageCaption(self, msg_identifier,
                           caption: str = None,
                           parse_mode: str = None,
                           caption_entities=None,
                           reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#editmessagecaption

        :param msg_identifier: Same as ``msg_identifier`` in :meth:`amanobot.Bot.editMessageText`
        """
        p = _strip(locals(), more=['msg_identifier'])
        p.update(_dismantle_message_identifier(msg_identifier))
        return self._api_request('editMessageCaption', _rectify(p))

    def editMessageMedia(self, msg_identifier, media,
                         reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#editmessagemedia

        :param msg_identifier: Same as ``msg_identifier`` in :meth:`amanobot.Bot.editMessageText`
        """
        p = _strip(locals(), more=['msg_identifier', 'media'])
        p.update(_dismantle_message_identifier(msg_identifier))

        legal_media, files_to_attach = _split_input_media_array([media])
        p['media'] = legal_media[0]

        return self._api_request('editMessageMedia', _rectify(p), files_to_attach)

    def editMessageReplyMarkup(self, msg_identifier,
                               reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#editmessagereplymarkup

        :param msg_identifier: Same as ``msg_identifier`` in :meth:`amanobot.Bot.editMessageText`
        """
        p = _strip(locals(), more=['msg_identifier'])
        p.update(_dismantle_message_identifier(msg_identifier))
        return self._api_request('editMessageReplyMarkup', _rectify(p))

    def stopPoll(self, msg_identifier,
                 reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#stoppoll

        :param msg_identifier:
            a 2-tuple (``chat_id``, ``message_id``).
            You may extract this value easily with :meth:`amanobot.message_identifier`
        """
        p = _strip(locals(), more=['msg_identifier'])
        p.update(_dismantle_message_identifier(msg_identifier))
        return self._api_request('stopPoll', _rectify(p))

    def deleteMessage(self, msg_identifier):
        """
        See: https://core.telegram.org/bots/api#deletemessage

        :param msg_identifier:
            Same as ``msg_identifier`` in :meth:`amanobot.Bot.editMessageText`,
            except this method does not work on inline messages.
        """
        p = _strip(locals(), more=['msg_identifier'])
        p.update(_dismantle_message_identifier(msg_identifier))
        return self._api_request('deleteMessage', _rectify(p))

    def sendSticker(self, chat_id: Union[int, str], sticker,
                    disable_notification: bool = None,
                    reply_to_message_id: int = None,
                    allow_sending_without_reply: bool = None,
                    reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#sendsticker

        :param sticker: Same as ``photo`` in :meth:`amanobot.Bot.sendPhoto`
        """
        p = _strip(locals(), more=['sticker'])
        return self._api_request_with_file('sendSticker', _rectify(p), {'sticker': sticker})

    def getStickerSet(self, name):
        """
        See: https://core.telegram.org/bots/api#getstickerset
        """
        p = _strip(locals())
        return self._api_request('getStickerSet', _rectify(p))

    def uploadStickerFile(self, user_id, png_sticker):
        """
        See: https://core.telegram.org/bots/api#uploadstickerfile
        """
        p = _strip(locals(), more=['png_sticker'])
        return self._api_request_with_file('uploadStickerFile', _rectify(p), {'png_sticker': png_sticker})

    def createNewStickerSet(self, user_id, name, title, emojis,
                            png_sticker=None,
                            tgs_sticker=None,
                            contains_masks=None,
                            mask_position=None):
        """
        See: https://core.telegram.org/bots/api#createnewstickerset
        """
        p = _strip(locals(), more=['png_sticker', 'tgs_sticker'])
        return self._api_request_with_file('createNewStickerSet', _rectify(p),
                                           {'png_sticker': png_sticker, 'tgs_sticker': tgs_sticker})

    def addStickerToSet(self, user_id, name, emojis,
                        png_sticker=None,
                        tgs_sticker=None,
                        mask_position=None):
        """
        See: https://core.telegram.org/bots/api#addstickertoset
        """
        p = _strip(locals(), more=['png_sticker', 'tgs_sticker'])
        return self._api_request_with_file('addStickerToSet', _rectify(p),
                                           {'png_sticker': png_sticker, 'tgs_sticker': tgs_sticker})

    def setStickerPositionInSet(self, sticker, position):
        """
        See: https://core.telegram.org/bots/api#setstickerpositioninset
        """
        p = _strip(locals())
        return self._api_request('setStickerPositionInSet', _rectify(p))

    def deleteStickerFromSet(self, sticker):
        """
        See: https://core.telegram.org/bots/api#deletestickerfromset
        """
        p = _strip(locals())
        return self._api_request('deleteStickerFromSet', _rectify(p))

    def setStickerSetThumb(self, name, user_id,
                           thumb=None):
        """
        See: https://core.telegram.org/bots/api#setstickersetthumb
        """
        p = _strip(locals(), more=['thumb'])
        return self._api_request_with_file('setStickerSetThumb', _rectify(p), {'thumb': thumb})

    def answerInlineQuery(self, inline_query_id, results,
                          cache_time=None,
                          is_personal=None,
                          next_offset=None,
                          switch_pm_text=None,
                          switch_pm_parameter=None):
        """ See: https://core.telegram.org/bots/api#answerinlinequery """
        p = _strip(locals())
        return self._api_request('answerInlineQuery', _rectify(p))

    def getUpdates(self,
                   offset=None,
                   limit=None,
                   timeout=None,
                   allowed_updates=None,
                   _raise_errors=None):
        """ See: https://core.telegram.org/bots/api#getupdates """
        if _raise_errors is None:
            _raise_errors = self._raise_errors
        p = _strip(locals())
        return self._api_request('getUpdates', _rectify(p), raise_errors=_raise_errors)

    def setWebhook(self,
                   url=None,
                   certificate=None,
                   ip_address=None,
                   max_connections=None,
                   allowed_updates=None,
                   drop_pending_updates=None):
        """ See: https://core.telegram.org/bots/api#setwebhook """
        p = _strip(locals(), more=['certificate'])

        if certificate:
            files = {'certificate': certificate}
            return self._api_request('setWebhook', _rectify(p), files)
        return self._api_request('setWebhook', _rectify(p))

    def deleteWebhook(self,
                      drop_pending_updates=None):
        p = _strip(locals())
        """ See: https://core.telegram.org/bots/api#deletewebhook """
        return self._api_request('deleteWebhook', _rectify(p))

    def getWebhookInfo(self):
        """ See: https://core.telegram.org/bots/api#getwebhookinfo """
        return self._api_request('getWebhookInfo')

    def setGameScore(self, user_id, score, game_message_identifier,
                     force=None,
                     disable_edit_message=None):
        """
        See: https://core.telegram.org/bots/api#setgamescore

        :param game_message_identifier: Same as ``msg_identifier`` in :meth:`amanobot.Bot.editMessageText`
        """
        p = _strip(locals(), more=['game_message_identifier'])
        p.update(_dismantle_message_identifier(game_message_identifier))
        return self._api_request('setGameScore', _rectify(p))

    def getGameHighScores(self, user_id, game_message_identifier):
        """
        See: https://core.telegram.org/bots/api#getgamehighscores

        :param game_message_identifier: Same as ``msg_identifier`` in :meth:`amanobot.Bot.editMessageText`
        """
        p = _strip(locals(), more=['game_message_identifier'])
        p.update(_dismantle_message_identifier(game_message_identifier))
        return self._api_request('getGameHighScores', _rectify(p))

    def download_file(self, file_id, dest):
        """
        Download a file to local disk.

        :param dest: a path or a ``file`` object
        """
        f = self.getFile(file_id)
        try:
            d = dest if _isfile(dest) else open(dest, 'wb')

            r = api.download((self._base_url, self._token, f['file_path']), preload_content=False)

            while 1:
                data = r.read(self._file_chunk_size)
                if not data:
                    break
                d.write(data)
        finally:
            if not _isfile(dest) and 'd' in locals():
                d.close()

            if 'r' in locals():
                r.release_conn()

    def message_loop(self, callback=None, relax=0.1,
                     timeout=20, allowed_updates=None,
                     source=None, ordered=True, maxhold=3,
                     run_forever=False):
        """
        :deprecated: will be removed in future. Use :class:`.MessageLoop` instead.

        Spawn a thread to constantly ``getUpdates`` or pull updates from a queue.
        Apply ``callback`` to every message received. Also starts the scheduler thread
        for internal events.

        :param callback:
            a function that takes one argument (the message), or a routing table.
            If ``None``, the bot's ``handle`` method is used.

        A *routing table* is a dictionary of ``{flavor: function}``, mapping messages to appropriate
        handler functions according to their flavors. It allows you to define functions specifically
        to handle one flavor of messages. It usually looks like this: ``{'chat': fn1,
        'callback_query': fn2, 'inline_query': fn3, ...}``. Each handler function should take
        one argument (the message).



        :param source:
            Source of updates.
            If ``None``, ``getUpdates`` is used to obtain new messages from Telegram servers.
            If it is a synchronized queue, new messages are pulled from the queue.
            A web application implementing a webhook can dump updates into the queue,
            while the bot pulls from it. This is how amanobot can be integrated with webhooks.

        Acceptable contents in queue:

        - ``str`` or ``bytes`` (decoded using UTF-8)
          representing a JSON-serialized `Update <https://core.telegram.org/bots/api#update>`_ object.
        - a ``dict`` representing an Update object.

        When ``source`` is ``None``, these parameters are meaningful:

        :type relax: float
        :param relax: seconds between each ``getUpdates``

        :type timeout: int
        :param timeout:
            ``timeout`` parameter supplied to :meth:`amanobot.Bot.getUpdates`,
            controlling how long to poll.

        :type allowed_updates: array of string
        :param allowed_updates:
            ``allowed_updates`` parameter supplied to :meth:`amanobot.Bot.getUpdates`,
            controlling which types of updates to receive.

        When ``source`` is a queue, these parameters are meaningful:

        :type ordered: bool
        :param ordered:
            If ``True``, ensure in-order delivery of messages to ``callback``
            (i.e. updates with a smaller ``update_id`` always come before those with
            a larger ``update_id``).
            If ``False``, no re-ordering is done. ``callback`` is applied to messages
            as soon as they are pulled from queue.

        :type maxhold: float
        :param maxhold:
            Applied only when ``ordered`` is ``True``. The maximum number of seconds
            an update is held waiting for a not-yet-arrived smaller ``update_id``.
            When this number of seconds is up, the update is delivered to ``callback``
            even if some smaller ``update_id``\s have not yet arrived. If those smaller
            ``update_id``\s arrive at some later time, they are discarded.

        Finally, there is this parameter, meaningful always:

        :type run_forever: bool or str
        :param run_forever:
            If ``True`` or any non-empty string, append an infinite loop at the end of
            this method, so it never returns. Useful as the very last line in a program.
            A non-empty string will also be printed, useful as an indication that the
            program is listening.
        """
        if callback is None:
            callback = self.handle
        elif isinstance(callback, dict):
            callback = flavor_router(callback)

        collect_queue = queue.Queue()

        def collector():
            while 1:
                try:
                    item = collect_queue.get(block=True)
                    callback(item)
                except:
                    # Localize error so thread can keep going.
                    traceback.print_exc()

        def relay_to_collector(update):
            key = _find_first_key(update, ['message',
                                           'edited_message',
                                           'channel_post',
                                           'edited_channel_post',
                                           'inline_query',
                                           'chosen_inline_result',
                                           'callback_query',
                                           'shipping_query',
                                           'pre_checkout_query',
                                           'poll',
                                           'poll_answer',
                                           'my_chat_member',
                                           'chat_member'])
            collect_queue.put(update[key])
            return update['update_id']

        def get_from_telegram_server():
            offset = None  # running offset
            allowed_upd = allowed_updates
            while 1:
                try:
                    result = self.getUpdates(offset=offset,
                                             timeout=timeout,
                                             allowed_updates=allowed_upd,
                                             _raise_errors=True)

                    # Once passed, this parameter is no longer needed.
                    allowed_upd = None

                    if len(result) > 0:
                        # No sort. Trust server to give messages in correct order.
                        # Update offset to max(update_id) + 1
                        offset = max([relay_to_collector(update) for update in result]) + 1

                except exception.BadHTTPResponse as e:
                    traceback.print_exc()

                    # Servers probably down. Wait longer.
                    if e.status == 502:
                        time.sleep(30)
                except:
                    traceback.print_exc()
                finally:
                    time.sleep(relax)

        def dictify(data):
            if type(data) is bytes:
                return json.loads(data.decode('utf-8'))
            if type(data) is str:
                return json.loads(data)
            if type(data) is dict:
                return data
            raise ValueError()

        def get_from_queue_unordered(qu):
            while 1:
                try:
                    data = qu.get(block=True)
                    update = dictify(data)
                    relay_to_collector(update)
                except:
                    traceback.print_exc()

        def get_from_queue(qu):
            # Here is the re-ordering mechanism, ensuring in-order delivery of updates.
            max_id = None  # max update_id passed to callback
            buffer = collections.deque()  # keep those updates which skip some update_id
            qwait = None  # how long to wait for updates,
            # because buffer's content has to be returned in time.

            while 1:
                try:
                    data = qu.get(block=True, timeout=qwait)
                    update = dictify(data)

                    if max_id is None:
                        # First message received, handle regardless.
                        max_id = relay_to_collector(update)

                    elif update['update_id'] == max_id + 1:
                        # No update_id skipped, handle naturally.
                        max_id = relay_to_collector(update)

                        # clear contagious updates in buffer
                        if len(buffer) > 0:
                            buffer.popleft()  # first element belongs to update just received, useless now.
                            while 1:
                                try:
                                    if type(buffer[0]) is dict:
                                        max_id = relay_to_collector(
                                            buffer.popleft())  # updates that arrived earlier, handle them.
                                    else:
                                        break  # gap, no more contagious updates
                                except IndexError:
                                    break  # buffer empty

                    elif update['update_id'] > max_id + 1:
                        # Update arrives pre-maturely, insert to buffer.
                        nbuf = len(buffer)
                        if update['update_id'] <= max_id + nbuf:
                            # buffer long enough, put update at position
                            buffer[update['update_id'] - max_id - 1] = update
                        else:
                            # buffer too short, lengthen it
                            expire = time.time() + maxhold
                            for a in range(nbuf, update['update_id'] - max_id - 1):
                                buffer.append(expire)  # put expiry time in gaps
                            buffer.append(update)

                    else:
                        pass  # discard

                except queue.Empty:
                    # debug message
                    # print('Timeout')

                    # some buffer contents have to be handled
                    # flush buffer until a non-expired time is encountered
                    while 1:
                        try:
                            if type(buffer[0]) is dict:
                                max_id = relay_to_collector(buffer.popleft())
                            else:
                                expire = buffer[0]
                                if expire <= time.time():
                                    max_id += 1
                                    buffer.popleft()
                                else:
                                    break  # non-expired
                        except IndexError:
                            break  # buffer empty
                except:
                    traceback.print_exc()
                finally:
                    try:
                        # don't wait longer than next expiry time
                        qwait = buffer[0] - time.time()
                        qwait = max(qwait, 0)
                    except IndexError:
                        # buffer empty, can wait forever
                        qwait = None

                    # debug message
                    # print ('Buffer:', str(buffer), ', To Wait:', qwait, ', Max ID:', max_id)

        collector_thread = threading.Thread(target=collector)
        collector_thread.daemon = True
        collector_thread.start()

        if source is None:
            message_thread = threading.Thread(target=get_from_telegram_server)
        elif isinstance(source, queue.Queue):
            if ordered:
                message_thread = threading.Thread(target=get_from_queue, args=(source,))
            else:
                message_thread = threading.Thread(target=get_from_queue_unordered, args=(source,))
        else:
            raise ValueError('Invalid source')

        message_thread.daemon = True  # need this for main thread to be killable by Ctrl-C
        message_thread.start()

        self._scheduler.on_event(collect_queue.put)
        self._scheduler.run_as_thread()

        if run_forever:
            if _isstring(run_forever):
                print(run_forever)
            while 1:
                time.sleep(10)


class SpeakerBot(Bot):
    def __init__(self, token):
        super(SpeakerBot, self).__init__(token)
        self._mic = helper.Microphone()

    @property
    def mic(self):
        return self._mic

    def create_listener(self):
        q = queue.Queue()
        self._mic.add(q)
        ln = helper.Listener(self._mic, q)
        return ln


class DelegatorBot(SpeakerBot):
    def __init__(self, token, delegation_patterns):
        """
        :param delegation_patterns: a list of (seeder, delegator) tuples.
        """
        super(DelegatorBot, self).__init__(token)
        self._delegate_records = [p + ({},) for p in delegation_patterns]

    @staticmethod
    def _startable(delegate):
        return ((hasattr(delegate, 'start') and inspect.ismethod(delegate.start)) and
                (hasattr(delegate, 'is_alive') and inspect.ismethod(delegate.is_alive)))

    @staticmethod
    def _tuple_is_valid(t):
        return len(t) == 3 and callable(t[0]) and type(t[1]) in [list, tuple] and type(t[2]) is dict

    def _ensure_startable(self, delegate):
        if self._startable(delegate):
            return delegate
        if callable(delegate):
            return threading.Thread(target=delegate)
        if type(delegate) is tuple and self._tuple_is_valid(delegate):
            func, args, kwargs = delegate
            return threading.Thread(target=func, args=args, kwargs=kwargs)
        raise RuntimeError(
            'Delegate does not have the required methods, is not callable, and is not a valid tuple.')

    def handle(self, msg):
        self._mic.send(msg)

        for calculate_seed, make_delegate, dict in self._delegate_records:
            id = calculate_seed(msg)

            if id is None:
                continue
            elif isinstance(id, collections.Hashable):
                if id not in dict or not dict[id].is_alive():
                    d = make_delegate((self, msg, id))
                    d = self._ensure_startable(d)

                    dict[id] = d
                    dict[id].start()
            else:
                d = make_delegate((self, msg, id))
                d = self._ensure_startable(d)
                d.start()
