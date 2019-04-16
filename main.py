# -*- coding: utf-8 -*-

import json
import logging
from functools import partial
from datetime import datetime
from random import choice

from telebot import types, TeleBot
from telebot.apihelper import ApiException

import data
import dbhelper

GREETING = "Я бот SECON'19. Здесь Вы можете посмотреть расписание конференции," \
           + "а также подписаться на рассылки, благодаря которым Вы не пропустите" \
           + "важную информацию.\n" \
           + "А еще я могу помочь связаться с организаторами, чтобы получить ответ " \
           + "на какой-то супер-важный вопрос."

botToken = data.token
bot = TeleBot(botToken)
logger = logging.getLogger()
support_request_cache = {}


def default_day():
    if datetime.now() <= datetime(2019, 4, 19):
        return 1
    else:
        return 2


def log(func):
    def _(message, *args, **kwargs):
        logger.info("================")
        logger.info(datetime.now())
        logger.info("From: " + str(message.from_user.first_name) +
                    "\nid: " + str(message.from_user.id) +
                    "\nText: " + str(message.text))
        logger.info("Function:", func.__name__)
        func(message, *args, *kwargs)

    return _


def show_main_menu(chat_id, text, force=False, markup=None, parse_mode="Markdown"):
    dbhelper.toggle_typing(chat_id, False, False)
    dbhelper.toggle_typing(chat_id, False, True)
    user = dbhelper.find_by_id(chat_id)

    reply_markup = markup(user and user.is_admin) if markup is not None else markup_menu(user and user.is_admin)

    if force or not user.last_menu_message_id:
        reply = bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
        dbhelper.save_last_menu_message_id(chat_id, reply.message_id)
    else:
        try:
            show_menu(chat_id=chat_id, message_id=user.last_menu_message_id, text=text,
                      markup=reply_markup)
        except ApiException:
            show_main_menu(chat_id, text, True, markup=reply_markup, parse_mode=parse_mode)


def show_menu(chat_id, text, markup, preview=True, message_id=None):
    if not message_id:
        message_id = dbhelper.find_by_id(chat_id).last_menu_message_id

    bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="Markdown",
                          disable_web_page_preview=(not preview))
    bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=markup)


def markup_menu(is_admin=False):
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(types.InlineKeyboardButton("Расписание", callback_data="menu_schedule"),
               types.InlineKeyboardButton("Подписка", callback_data="menu_subscribe"),
               types.InlineKeyboardButton("Место проведения", callback_data="action_location"),
               types.InlineKeyboardButton("Ссылки", callback_data="menu_links"),
               types.InlineKeyboardButton("Связь с организаторами", callback_data="action_contact"))

    if is_admin:
        markup.row(types.InlineKeyboardButton("Администрирование", callback_data="menu_admin"))

    return markup


def markup_admin_menu(*_, **__):
    count = dbhelper.count_support_requests()

    markup = types.InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(types.InlineKeyboardButton("Рассылка", callback_data="menu_admin_mailing"),
               types.InlineKeyboardButton("Пользователи", callback_data="menu_admin_users"),
               types.InlineKeyboardButton("Обращения ({})".format(count), callback_data="menu_admin_requests"))
    markup.row(types.InlineKeyboardButton("« Назад", callback_data="menu"))

    return markup


def markup_admin_users(_, page=1, users_len=11):
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 2

    if page > 1:
        markup.add(types.InlineKeyboardButton("«", callback_data="menu_admin_users_{}".format(page - 1)))
    if users_len == 11:
        markup.add(types.InlineKeyboardButton("»", callback_data="menu_admin_users_{}".format(page + 1)))
    markup.row(types.InlineKeyboardButton("« Назад", callback_data="menu_admin"))

    return markup


def markup_schedule():
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 2

    markup.row(types.InlineKeyboardButton("По часам", callback_data="menu_schedule_hourly"),
               types.InlineKeyboardButton("По направлениям", callback_data="menu_schedule_tracks"))
    markup.row(types.InlineKeyboardButton("« Назад", callback_data="menu"))

    return markup


def markup_schedule_hourly(day):
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 2

    markup.add(
        *[types.InlineKeyboardButton(hour, callback_data="action_schedule_hourly_{}_{}".format(day, hour)) for hour in
          data.api.get_hours(day=day)])
    if day == 1:
        markup.row(types.InlineKeyboardButton("День 2 (20 апреля)", callback_data="menu_schedule_hourly_2"))
    else:
        markup.row(types.InlineKeyboardButton("День 1 (19 апреля)", callback_data="menu_schedule_hourly_1"))
    markup.row(types.InlineKeyboardButton("« Назад", callback_data="menu_schedule"))

    return markup


def markup_schedule_track():
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 1

    all_tracks = data.api.get_tracks(1)
    buttons = [types.InlineKeyboardButton(text="{}".format(track['name']),
                                          callback_data="action_schedule_track_{}_{}".format(track['id'],
                                                                                             default_day())) for track
               in
               all_tracks]

    markup.add(*buttons)
    markup.row(types.InlineKeyboardButton("« Назад", callback_data="menu_schedule"))

    return markup


def markup_subscribe():
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 2
    markup.row(types.InlineKeyboardButton("Новости", callback_data="menu_subscribe_news"),
               types.InlineKeyboardButton("Направления", callback_data="menu_subscribe_tracks"))
    markup.row(types.InlineKeyboardButton("« Назад", callback_data="menu"))
    return markup


def markup_subscribe_news(user):
    markup = types.InlineKeyboardMarkup()
    button = "Подписаться на новости" if not user.is_subscribed else "Отписаться от новостей"

    markup.row(types.InlineKeyboardButton(text=button, callback_data="action_subscribe_news"))
    markup.row(types.InlineKeyboardButton("« Назад", callback_data="menu_subscribe"))

    return markup


def markup_send_or_cancel(is_admin=False):
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        types.InlineKeyboardButton(text="Отправить",
                                   callback_data="action_send" if not is_admin else "action_admin_send"),
        types.InlineKeyboardButton(text="Отменить",
                                   callback_data="action_cancel" if not is_admin else "action_admin_cancel")
    )

    return markup


def keyboard_send_or_cancel():
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=False, resize_keyboard=True)
    keyboard.row_width = 1
    keyboard.add(types.KeyboardButton(text="Отправить"), types.KeyboardButton(text="Отменить"))

    return keyboard


def keyboard_menu():
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    keyboard.add(types.KeyboardButton(text="Меню"))

    return keyboard


def keyboard_admin_requests(has_requests=True):
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    keyboard.row_width = 1
    if has_requests:
        keyboard.add(types.KeyboardButton(text="Отметить все прочитанными"))
    keyboard.add(types.KeyboardButton(text="« Назад"))

    return keyboard


def menu_admin(message):
    show_menu(chat_id=message.chat.id, text="Управление ботом:", markup=markup_admin_menu())


def menu_admin_requests(message, page=1):
    dbhelper.toggle_typing(message.chat.id, True, True)
    count = dbhelper.count_support_requests()

    plural = [
        'ое' if str(count)[-1] == '1' and str(count)[-2:] != '11' else 'ых',
        'е' if str(count)[-1] == '1' and str(count)[-2:] != '11' else 'й',
        'я' if str(count)[-1] == '1' and str(count)[-2:] != '11' else 'ей',
    ]
    text = "Найдено {} непрочитанн{} обращени{} от пользовател{}".format(count, *plural)
    bot.send_message(chat_id=message.chat.id, text=text, reply_markup=keyboard_admin_requests(count > 0))

    for request in dbhelper.get_support_requests(page=page):
        request_message = "*{name}* [@{username}](tg://user?id={username}):\n".format(name=request.user.name,
                                                                                      username=request.user.username)
        request_message += "\n".join(json.loads(request.message).values())

        markup = types.InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(types.InlineKeyboardButton("Ответить", callback_data="action_admin_reply_{}".format(request.id)),
                   types.InlineKeyboardButton("Опубликовать",
                                              callback_data="action_admin_publish_{}".format(request.id)),
                   types.InlineKeyboardButton("Отметить прочитанным",
                                              callback_data="action_admin_mark_as_read_{}".format(request.id)))

        bot.send_message(chat_id=message.chat.id, text=request_message, reply_markup=markup, parse_mode="Markdown")


def menu_admin_users(message, page=1):
    users = dbhelper.get_all_users(page=page)

    text = "Список пользователей:\n"

    for user in (users[:-1] if len(users) == 11 else users):
        text += "\n• <b>{name}</b> @{username}".format(name=user.name, username=user.username)
        text += "(А)" if user.is_admin else ""
        text += "\nПодписка: <i>{}активна</i>".format("" if user.is_subscribed else "не")
        text += "\nНаправления: {}".format(", ".join([t.title for t in dbhelper.get_user_tracks(user.telegram_id)]))
        text += "\nДействия: " + (
            "/give_admin_{id}".format(id=user.id) if not user.is_admin else "/revoke_admin_{}".format(user.id))
        text += "\n"

    show_main_menu(chat_id=message.chat.id, text=text, force=True, parse_mode="html",
                   markup=partial(markup_admin_users, page=page, users_len=len(users)))


def menu_admin_mailing(message):
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(types.InlineKeyboardButton("ВСЕМ пользователям", callback_data="action_mailing_all"),
               types.InlineKeyboardButton("По подписке", callback_data="action_mailing_subscribed"),
               types.InlineKeyboardButton("По направлению", callback_data="action_mailing_track"))
    markup.row(types.InlineKeyboardButton("« Назад", callback_data="menu_admin"))

    show_menu(chat_id=message.chat.id, text="Выберите тип рассылки", markup=markup)


def menu_schedule(message):
    text = "Здесь вы можете посмотреть программу и выбрать, на какой доклад хотите сходить"

    show_menu(chat_id=message.chat.id, text=text, markup=markup_schedule())


def menu_schedule_hourly(message, day=None):
    if not day:
        day = default_day()

    text = "Вы просматриваете расписание на " + ("*19 апреля*" if day == 1 else "*20 апреля*") \
           + "\n\nВыберите время, чтобы получить список докладов и залы, в которых они проходят"

    show_menu(chat_id=message.chat.id, text=text, markup=markup_schedule_hourly(day=day))


def menu_schedule_tracks(message):
    text = "Выберите направление, чтобы получить список докладов и залы, в которых они проходят"

    show_menu(chat_id=message.chat.id, text=text, markup=markup_schedule_track())


def menu_subscribe(message):
    user = dbhelper.find_by_id(message.chat.id)
    user_tracks = dbhelper.get_user_tracks(message.chat.id)

    status = "активна" if user.is_subscribed else "неактивна"
    text = "Подписка на новостную рассылку: *{}*.".format(status)

    if user_tracks:
        text += "\nВы подписаны на следующие направления:\n" \
                + "\n".join(["• {}".format(track.title) for track in user_tracks])
    else:
        text += "\nВы не подписаны ни на одно направление."

    text += "\n\nКакую подписку вы хотите настроить?"

    show_menu(chat_id=message.chat.id, text=text, markup=markup_subscribe())


def menu_subscribe_news(message):
    user = dbhelper.find_by_id(message.chat.id)
    status = "активна" if user.is_subscribed else "неактивна"

    show_menu(message.chat.id, text="Подписка на новостную рассылку: *{}*.".format(status),
              markup=markup_subscribe_news(user))


def menu_subscribe_tracks(message):
    all_tracks = dbhelper.get_all_tracks()
    user_tracks = dbhelper.get_user_tracks(message.chat.id)

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    buttons = [types.InlineKeyboardButton(
        text="{}{}".format("[x] " if track.id in map(lambda track: track.id, user_tracks) else "", track.title),
        callback_data="action_subscribe_track_{}".format(track.id)) for track in all_tracks]

    keyboard.add(*buttons)
    keyboard.row(types.InlineKeyboardButton("« Назад", callback_data="menu_subscribe"))

    if not user_tracks:
        text = "Вы не подписаны ни на одно направление.\n\nВыберите направления, на которые хотите подписаться."

    else:
        text = "Направления, на которые вы подписаны:\n" \
               + "\n".join(["• {}".format(track.title) for track in user_tracks]) \
               + "\n\nНажмите на направление чтобы подписаться на новости или отписаться от него."

    show_menu(chat_id=message.chat.id, text=text, markup=keyboard)


def menu_links(message):
    keyboard = types.InlineKeyboardMarkup()

    keyboard.add(*[types.InlineKeyboardButton(**link) for link in data.links])
    keyboard.row(types.InlineKeyboardButton("« Назад", callback_data="menu"))

    show_menu(chat_id=message.chat.id, text="Подписывайся на наши социальные сети 🐴", markup=keyboard)


def action_schedule_hourly(message, day, time):
    day_formatted = "19 апреля" if day == 1 else "20 апреля"
    schedule = data.api.get_schedule_by_hour(day, time)

    text = "Список докладов, которые пройдут *{}* в *{}*:\n".format(day_formatted, time)
    url = 'https://2019.secon.ru/reports/'

    if isinstance(schedule, list):
        for item in schedule:
            if 'report' not in item:
                continue

            text += "\n• [{}]({})".format(item['report']['name'], url + item['report']['slug'])
            text += "\n*Спикер*: {}".format(", ".join(
                ["{name} ({job})".format(**s) for s in item['report']['speakers']]))
            text += "\n*Место проведения*: {}\n".format(data.api.get_room(item['room_id']))
    else:
        if 'report' not in schedule:
            text += "\n• *{}*".format(schedule['title'])
            if 'room' in schedule:
                text += "\n*Место проведения*: {}\n".format(data.api.get_room(schedule['room']['id']))
        else:
            text += "\n• [{}]({})".format(schedule['report']['name'], url + schedule['report']['slug'])
            text += "\n*Спикер*: {}".format(", ".join(
                ["{name} ({job})".format(**s) for s in schedule['report']['speakers']]))
            text += "\n*Место проведения*: {}\n".format(data.api.get_room(schedule['room']['id']))

    show_menu(chat_id=message.chat.id, text=text, markup=markup_schedule_hourly(day), preview=False)


def action_schedule_track(message, track_id, day=None):
    if not day:
        day = default_day()

    day_formatted = "19 апреля" if day == 1 else "20 апреля"
    url = 'https://2019.secon.ru/reports/'

    text = "Расписание по направлению *{}* на *{}*:\n".format(data.api.get_track(track_id), day_formatted)

    for item in data.api.get_schedule_by_track(track_id, day):
        if 'report' not in item:
            text += "\n• *{}*".format(item['title'])
            text += "\n*Время проведения*: {}".format(item['time'])
            if 'room' in item:
                text += "\n*Место проведения*: {}\n".format(data.api.get_room(item['room']['id']))
            else:
                text += '\n'
        else:
            text += "\n• [{}]({})".format(item['report']['name'], url + item['report']['slug'])
            text += "\n*Спикер*: {}".format(", ".join(
                ["{name} ({job})".format(**s) for s in item['report']['speakers']]))
            text += "\n*Время проведения*: {}".format(item['time'])
            text += "\n*Место проведения*: {}\n".format(data.api.get_room(item['room_id']))
    else:
        text += "\nДокладов по этому направлению нет."

    markup = types.InlineKeyboardMarkup()
    markup.row_width = 1

    if day == 1:
        markup.row(types.InlineKeyboardButton("День 2 (20 апреля)",
                                              callback_data="action_schedule_track_{}_2".format(track_id)))
    else:
        markup.row(types.InlineKeyboardButton("День 1 (19 апреля)",
                                              callback_data="action_schedule_track_{}_1".format(track_id)))
    markup.row(types.InlineKeyboardButton("« Назад", callback_data="menu_schedule_tracks"))

    show_menu(chat_id=message.chat.id, text=text, markup=markup, preview=False)


def action_subscribe_news(message):
    user = dbhelper.find_by_id(message.chat.id)
    should_be_subscribed = not user.is_subscribed

    dbhelper.toggle_subscription(message.chat.id, subscribed=should_be_subscribed)

    if should_be_subscribed:
        result_message = "Вы подписались на новостные рассылки! :)"
    else:
        result_message = "Вы отписались от новостных рассылок! :("

    user = dbhelper.find_by_id(message.chat.id)
    show_menu(chat_id=message.chat.id, text=result_message, markup=markup_subscribe_news(user))


def action_subscribe_track(message, track_id):
    dbhelper.toggle_track_subscription(message.chat.id, int(track_id))
    menu_subscribe_tracks(message)


def action_location(message):
    bot.send_message(chat_id=message.chat.id, text="Адрес: \nпр. Строителей, 168А, Пенза", reply_markup=keyboard_menu())
    bot.send_location(chat_id=message.chat.id, latitude=53.220670, longitude=44.883901)


def action_contact(message):
    dbhelper.toggle_typing(message.chat.id, True)

    text = "Если у Вас возник какой-то вопрос или Вы что-то потеряли и очень хотите найти" \
           ", напишите здесь и мы обязательно Вам ответим!"

    bot.send_message(chat_id=message.chat.id, text=text, reply_markup=keyboard_send_or_cancel())


def action_send(message):
    text = support_request_cache.get(message.chat.id, {})

    if text:
        dbhelper.create_support_request(message.chat.id, text)
        dbhelper.toggle_typing(message.chat.id, False)

        support_request_cache[message.chat.id] = {}

        bot.send_message(chat_id=message.chat.id, text="Сообщение организаторам успешно отправлено",
                         reply_markup=keyboard_menu())
        show_main_menu(message.chat.id, text="Меню взаимодействия:", force=True)

        user = dbhelper.find_by_id(message.chat.id)

        text = "Получено новое сообщение от пользователя [@{username}](tg://user?id={username})".format(
            username=user.username)

        for admin in dbhelper.get_all_admins():
            bot.send_message(chat_id=admin.telegram_id, text=text, parse_mode="Markdown")
    else:
        bot.send_message(chat_id=message.chat.id,
                         text="Сперва напишите сообщение, которое хотите отправить администрации",
                         reply_markup=markup_send_or_cancel())


def action_admin_send(message):
    dbhelper.toggle_typing(message.chat.id, False, True)
    if message.chat.id not in support_request_cache:
        menu_admin_requests(message)
        return

    request = dbhelper.get_support_request(support_request_cache[message.chat.id]["id"])

    if support_request_cache[message.chat.id].get("type", "forward") == "forward":
        for user in dbhelper.get_all_users():
            if user.telegram_id == message.chat.id:
                continue

            messages = json.loads(request.message)
            for id in messages.keys():
                bot.forward_message(chat_id=user.telegram_id, from_chat_id=request.user.telegram_id, message_id=id)
    else:
        message_id = list(json.loads(request.message).keys())[-1]

        bot.send_message(chat_id=request.user.telegram_id, reply_to_message_id=message_id,
                         text=support_request_cache[message.chat.id]["text"])

    dbhelper.mark_support_request_as_read(request.id)
    support_request_cache[message.chat.id] = {}

    menu_admin_requests(message)


def action_admin_cancel(message):
    dbhelper.toggle_typing(message.chat.id, False, True)
    support_request_cache[message.chat.id] = {}

    bot.send_message(chat_id=message.chat.id, text="Действие отменено")
    menu_admin_requests(message)


def action_cancel(message):
    dbhelper.toggle_typing(message.chat.id, False)
    support_request_cache[message.chat.id] = {}

    bot.send_message(chat_id=message.chat.id, text="Действие отменено", reply_markup=keyboard_menu())
    show_main_menu(message.chat.id, text="Меню взаимодействия:", force=True)


def action_admin_publish(message, id):
    dbhelper.toggle_typing(message.chat.id, True, True)
    request = dbhelper.get_support_request(id)

    support_request_cache[message.chat.id] = {"id": id, "type": "forward"}

    text = "Вы действительно хотите отправить всем сообщение от пользователя {} с текстом:```{}```?".format(
        "[@{username}](tg://user?id={username})".format(username=request.user.username),
        "\n".join(json.loads(request.message).values()))
    bot.send_message(chat_id=message.chat.id, text=text, reply_markup=markup_send_or_cancel(True),
                     parse_mode="Markdown")


def action_admin_reply(message, id):
    dbhelper.toggle_typing(message.chat.id, True, True)
    request = dbhelper.get_support_request(id)

    support_request_cache[message.chat.id] = {"id": id, "type": "reply"}

    text = "Напишите сообщение, которое хотите отправить пользователю {} в ответ:\n{}.".format(
        "[@{username}](tg://user?id={username})".format(username=request.user.username),
        "\n".join(json.loads(request.message).values()))

    bot.send_message(chat_id=message.chat.id, text=text, reply_markup=keyboard_send_or_cancel(), parse_mode="Markdown")


@bot.message_handler(func=lambda message: message.text and message.text.lower().strip().startswith('/give_admin_'))
def give_admin(message):
    user = dbhelper.find(int(message.text.split('_')[-1]))
    dbhelper.toggle_admin(user.id, True)

    bot.send_message(chat_id=message.chat.id, text="Пользователь {} теперь администратор".format(user.username))
    menu_admin_users(message)


@bot.message_handler(func=lambda message: message.text and message.text.lower().strip().startswith('/revoke_admin_'))
def revoke_admin(message):
    user = dbhelper.find(int(message.text.split('_')[-1]))
    dbhelper.toggle_admin(user.id, False)

    bot.send_message(chat_id=message.chat.id, text="Пользователь {} больше не администратор".format(user.username))
    menu_admin_users(message)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    def show_menu_route(message):
        show_main_menu(message.chat.id, text="Меню взаимодействия:")

    routing = {
        "menu_schedule": menu_schedule,
        "menu_schedule_hourly": menu_schedule_hourly,
        "menu_schedule_tracks": menu_schedule_tracks,
        "menu_subscribe": menu_subscribe,
        "menu_links": menu_links,
        "action_location": action_location,
        "menu_subscribe_tracks": menu_subscribe_tracks,
        "menu_subscribe_news": menu_subscribe_news,
        "action_subscribe_news": action_subscribe_news,
        "action_contact": action_contact,
        "action_send": action_send,
        "action_admin_send": action_admin_send,
        "action_cancel": action_cancel,
        "action_admin_cancel": action_admin_cancel,
        "menu": show_menu_route,
        "menu_admin": menu_admin,
        "menu_admin_requests": menu_admin_requests,
        "menu_admin_users": menu_admin_users,
        "menu_admin_mailing": menu_admin_mailing
    }

    if call.data.startswith("action_subscribe_track_"):
        method = partial(action_subscribe_track, track_id=int(call.data.split("_")[-1]))
    elif call.data.startswith("action_schedule_track_"):
        track_id, day = call.data.split("_")[-2:]

        method = partial(action_schedule_track, track_id=int(track_id), day=int(day))
    elif call.data.startswith("action_schedule_hourly_"):
        day, time = call.data.split("_")[-2:]

        method = partial(action_schedule_hourly, day=int(day), time=time)
    elif call.data.startswith("action_admin_publish_"):
        id = int(call.data.split("_")[-1])

        method = partial(action_admin_publish, id=id)
    elif call.data.startswith("action_admin_reply_"):
        id = int(call.data.split("_")[-1])

        method = partial(action_admin_reply, id=id)
    elif call.data.startswith("menu_schedule_hourly_"):
        method = partial(menu_schedule_hourly, day=int(call.data.split("_")[-1]))
    elif call.data.startswith("menu_admin_requests_"):
        method = partial(menu_admin_requests, page=int(call.data.split("_")[-1]))
    elif call.data.startswith("menu_admin_users_"):
        method = partial(menu_admin_users, page=int(call.data.split("_")[-1]))
    else:
        method = routing.get(call.data, show_menu_route)

    method(call.message)


@bot.message_handler(commands=["start"])
@log
def start(message):
    user = dbhelper.find_by_id(int(message.chat.id))
    username = (message.from_user.first_name or message.from_user.username)

    if user:
        show_main_menu(message.chat.id, "С возвращением, {} :)".format(username), force=True)
    else:
        dbhelper.insert(message.chat.id, message.from_user.username,
                        " ".join(
                            filter(lambda x: bool(x), [message.from_user.first_name, message.from_user.last_name])))
        show_main_menu(message.chat.id, "Здравствуйте, {} :)\n\n".format(username) + GREETING, force=True)


@bot.message_handler(func=lambda message: message.text and message.text.lower().strip() in ["меню", "menu"])
@log
def menu(message):
    show_main_menu(message.chat.id, text=GREETING, force=True)


def typing_admin_menu(message):
    return dbhelper.check_typing(message.chat.id, admin=True)


def typing_menu(message):
    return dbhelper.check_typing(message.chat.id)


@bot.message_handler(func=typing_menu)
@log
def support_request_typing(message):
    if not message.text:
        return

    if message.text.lower().strip() == 'отменить':
        action_cancel(message)
    elif message.text.lower().strip() == 'отправить':
        action_send(message)
    else:
        if not support_request_cache.get(message.chat.id):
            support_request_cache[message.chat.id] = {}

        support_request_cache[message.chat.id].update({message.message_id: message.text})

        texts = [
            "Отлично, теперь нажмите *Отправить*, чтобы мы получили Ваше сообщение или напишите еще одно.",
            "Окей, Вы можете написать еще одно сообщение или нажать *Отправить*, чтобы мы получили Ваше сообщение."
        ]

        bot.send_message(chat_id=message.chat.id, text=choice(texts), reply_markup=markup_send_or_cancel(),
                         parse_mode="Markdown")


@bot.message_handler(func=typing_admin_menu)
@log
def admin_typing(message):
    if not message.text:
        return

    if message.text.lower().strip() == 'отметить все прочитанными':
        dbhelper.mark_all_support_requests_as_read()

        bot.send_message(chat_id=message.chat.id, text="Все обращения отмечены как прочитанные",
                         reply_markup=keyboard_admin_requests(False))
    elif message.text.lower().strip() == '« назад':
        dbhelper.toggle_typing(message.chat.id, False, True)
        bot.send_message(chat_id=message.chat.id, text="Работа с обращениями завершена", reply_markup=keyboard_menu())

        show_main_menu(message.chat.id, text="Управление ботом:", force=True, markup=markup_admin_menu)
    elif message.text.lower().strip() == 'отправить':
        action_admin_send(message)
    elif message.text.lower().strip() == 'отменить':
        action_admin_cancel(message)
    else:
        if message.chat.id not in support_request_cache:
            bot.send_message(chat_id=message.chat.id, text="Произошла ошибка. Попробуйте ответить еще раз.",
                             reply_markup=keyboard_menu(), parse_mode="Markdown")
            menu_admin_requests(message)
            return

        if 'text' in support_request_cache[message.chat.id]:
            support_request_cache[message.chat.id].update(
                {'text': support_request_cache[message.chat.id]['text'] + "\n" + message.text})
        else:
            support_request_cache[message.chat.id].update({'text': message.text})

        text = "*Вы написали:*\n{}\nОтправляем?".format(message.text)

        bot.send_message(chat_id=message.chat.id, text=text, reply_markup=markup_send_or_cancel(True),
                         parse_mode="Markdown")


@bot.edited_message_handler(func=typing_admin_menu)
@log
def reply_updating(message):
    if message.chat.id not in support_request_cache:
        return

    support_request_cache[message.chat.id].update({message.message_id: message.text})

    text = "Вы изменили сообщение: {}\nОтправляем?".format(message.text)

    bot.send_message(chat_id=message.chat.id, text=text, reply_markup=markup_send_or_cancel(True),
                     parse_mode="Markdown")


@bot.edited_message_handler(func=typing_menu)
@log
def support_request_updating(message):
    if message.chat.id not in support_request_cache:
        return

    support_request_cache[message.chat.id].update({message.message_id: message.text})


@bot.message_handler(func=lambda message: True, content_types=["text"])
@log
def default(message):
    show_main_menu(message.chat.id, "Я еще не научился отвечать на такие запросы :)"
                                    "\nДавайте ограничимся меню взаимодействия?", force=True)


# while True:
#     try:
bot.polling(none_stop=True)
    # except:
    #     print("Something wrong")
