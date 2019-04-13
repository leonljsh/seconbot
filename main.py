# -*- coding: utf-8 -*-

import json
import logging
from functools import partial
from datetime import datetime

from telebot import types, TeleBot
from telebot.apihelper import ApiException

import data
import dbhelper

administration = {
    "direct_post": "рассылка по направлениям",
    "send_post": "массовая рассылка для тех кто подписан на новостные рассылки",
    "emergency_post": "массовая рассылка без учета подписки "
                      "(каждому, кто хотя бы раз запускал бота и записан в базе данных)",
    "add_admin": "добавить администратора",
    "remove_admin": "удалить администратора",
    "list_admin": "вывести id всех администраторов",
    "find_by_id": "найти в базе данных пользователя и вывести информацию  о нем"
}

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


def show_main_menu(chat_id, text, force=False):
    user = dbhelper.find_by_id(chat_id)

    if force or not user.last_menu_message_id:
        reply = bot.send_message(chat_id, text, reply_markup=markup_menu(user and user.is_admin))
        dbhelper.save_last_menu_message_id(chat_id, reply.message_id)
    else:
        try:
            show_menu(chat_id=chat_id, message_id=user.last_menu_message_id, text=text,
                      markup=markup_menu(user and user.is_admin))
        except ApiException:
            show_main_menu(chat_id, text, True)


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
        markup.row(types.InlineKeyboardButton("Администрирование", callback_data="menu"))

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


def keyboard_contact():
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    keyboard.row_width = 1
    keyboard.add(types.KeyboardButton(text="Отправить"), types.KeyboardButton(text="Отменить"))

    return keyboard


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
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    keyboard.add(types.KeyboardButton(text="Меню"))

    bot.send_message(chat_id=message.chat.id, text="Адрес: \nпр. Строителей, 168А, Пенза", reply_markup=keyboard)
    bot.send_location(chat_id=message.chat.id, latitude=53.220670, longitude=44.883901)


def action_contact(message):
    dbhelper.toggle_typing(message.chat.id, True)

    text = "Если у Вас возник какой-то вопрос или вы что-то потеряли и очень хотите найти" \
           ", напишите здесь и мы обязательно Вам ответим!"

    bot.send_message(chat_id=message.chat.id, text=text, reply_markup=keyboard_contact())


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
        "menu": show_menu_route
    }

    if call.data.startswith("action_subscribe_track_"):
        method = partial(action_subscribe_track, track_id=int(call.data.split("_")[-1]))
    elif call.data.startswith("action_schedule_track_"):
        track_id, day = call.data.split("_")[-2:]

        method = partial(action_schedule_track, track_id=int(track_id), day=int(day))
    elif call.data.startswith("action_schedule_hourly_"):
        day, time = call.data.split("_")[-2:]

        method = partial(action_schedule_hourly, day=int(day), time=time)
    elif call.data.startswith("menu_schedule_hourly_"):
        method = partial(menu_schedule_hourly, day=int(call.data.split("_")[-1]))
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
        dbhelper.insert(message.chat.id, message.from_user.username)
        show_main_menu(message.chat.id, "Здравствуйте, {} :)".format(username), force=True)


@bot.message_handler(func=lambda message: message.text.lower() in ["меню", "menu"])
@log
def menu(message):
    show_main_menu(message.chat.id, text="Меню взаимодействия:", force=True)


def typing_menu(message):
    return dbhelper.check_typing(message.chat.id)


@bot.message_handler(func=typing_menu)
@log
def support_request_typing(message):
    if message.text.lower() == 'отменить':
        dbhelper.toggle_typing(message.chat.id, False)
        show_main_menu(message.chat.id, text="Меню взаимодействия:", force=True)
    elif message.text.lower() == 'отправить':
        text = support_request_cache.get(message.chat.id, {})

        if text:
            dbhelper.create_support_request(message.chat.id, text)
            dbhelper.toggle_typing(message.chat.id, False)

            support_request_cache[message.chat.id] = {}

            bot.send_message(chat_id=message.chat.id, text="Сообщение организаторам успешно отправлено")
            show_main_menu(message.chat.id, text="Меню взаимодействия:", force=True)
        else:
            bot.send_message(chat_id=message.chat.id,
                             text="Сперва напишите сообщение, которое хотите отправить администрации",
                             reply_markup=keyboard_contact())
    else:
        if not support_request_cache.get(message.chat.id):
            support_request_cache[message.chat.id] = {}

        support_request_cache[message.chat.id].update({message.message_id: message.text})


@bot.edited_message_handler(func=typing_menu)
@log
def support_request_updating(message):
    if not support_request_cache.get(message.chat.id):
        pass

    support_request_cache[message.chat.id].update({message.message_id: message.text})


@bot.message_handler(func=lambda message: True, content_types=["text"])
@log
def default(message):
    show_main_menu(message.chat.id, "Я еще не научился отвечать на такие запросы :)"
                                    "\nДавайте ограничимся меню взаимодействия?", force=True)


# ==============Команды администратора=================
@bot.message_handler(commands=["admin"], func=lambda message: dbhelper.check_adm(message.chat.id))
@log
def command_admin_help(message):
    cid = message.chat.id
    help_admin = "Список доступных команд для администратора: \n"
    for key in administration:
        help_admin += "/" + key + ": "
        help_admin += administration[key] + "\n"
    bot.send_message(cid, help_admin)


# новостная рассылка (без учета подписки)
@bot.message_handler(commands=["emergency_post"], func=lambda message: dbhelper.check_adm(message.chat.id))
@log
def command_send(message):
    sent = bot.send_message(message.chat.id, "Напишите пост. Его увидят все пользователи без исключения."
                                             "\nБудьте внимательны, его нельзя будет редактировать!"
                                             "\nДля отмены написания используйте команду /cancel")
    bot.register_next_step_handler(sent, sending)


@log
def sending(message: types.Message):
    if message.text == "/cancel":
        bot.send_message(message.chat.id, "рассылка была отменена")

    else:
        users_data = json.load(open(data.storage_name))
        for user in users_data["_default"]:
            uid = users_data["_default"][user]["id"]
            if message.content_type == "text":
                bot.send_message(uid, str(message.text))

            elif message.content_type == "photo":
                photo = message.photo[-1].file_id
                bot.send_photo(uid, photo, message.caption)

            else:
                bot.send_message(message.chat.id, "Вы отправили сообщение не поддерживаемого типа. "
                                                  "Пожалуйста, попробуйте снова после команды /send")


# новостная рассылка (с учетом подписки)
@bot.message_handler(commands=["send_post"], func=lambda message: dbhelper.check_adm(message.chat.id))
@log
def command_send(message):
    sent = bot.send_message(message.chat.id, "Напишите пост. Его увидят все пользователи, "
                                             "подписанные на новостную рассылку."
                                             "\nБудьте внимательны, его нельзя будет редактировать!"
                                             "\nДля отмены написания используйте команду /cancel")
    bot.register_next_step_handler(sent, sending)


@log
def sending(message: types.Message):
    if message.text == "/cancel":
        bot.send_message(message.chat.id, "рассылка была отменена")

    else:
        list_of_users = dbhelper.find_all_subs()
        for user in list_of_users:
            if message.content_type == "text":
                bot.send_message(user["id"], str(message.text))

            elif message.content_type == "photo":
                photo = message.photo[-1].file_id
                bot.send_photo(user["id"], photo, message.caption)

            else:
                bot.send_message(message.chat.id, "Вы отправили сообщение не поддерживаемого типа. "
                                                  "Пожалуйста, попробуйте снова после команды /send")


# массовая рассылка по направлениям
@bot.message_handler(commands=["direct_post"], func=lambda message: dbhelper.check_adm(message.chat.id))
@log
def command_directly(message):
    sent = bot.send_message(message.chat.id, "Выбор направления для рассылки",
                            "\nДля отмены написания используйте команду /cancel")
    bot.register_next_step_handler(sent, direction_choose)


# выбор направления для рассылки
def direction_choose(message):
    bot.send_message(message.chat.id, text="mobile == Мобильная разработка\n"
                                           "quality == Контроль качества\n"
                                           "database == Базы данных\n"
                                           "design == Дизайн и компьютерная графика\n"
                                           "frontend == Frontend программирование\n"
                                           "leading == Управление проектами (управление распределенными командами)\n"
                                           "IoT == Интернет вещей (IoT)\n"
                                           "data_science == AI, ML, BigData\n"
                                           "start_up == Start ups\n"
                                           "vr == VR/AR\n"
                                           "gamedev == GameDev\n"
                                           "devops == DevOps\n"
                                           "java == Java-программирование\n"
                                           "master == Мастер-классы")
    if message.text == "/cancel":
        bot.send_message(message.chat.id, "Рассылка была отменена")

    elif message.text in data.tracks:
        logger.debug(message.text)
        direction_data = partial(direction_send, message.text)
        sent = bot.send_message(message.chat.id, "Направление: " + message.text + "\nВведите текст")
        bot.register_next_step_handler(sent, direction_data)

    else:
        bot.send_message(message.chat.id, "Несуществующее направление")


# рассылка по выбранному направлению
def direction_send(direction, message):
    list_of_users = dbhelper.find_all_by_dir(direction)
    logger.debug(direction)
    logger.debug(list_of_users)
    for user in list_of_users:
        if message.content_type == "text":
            bot.send_message(user["id"], str(message.text))

        elif message.content_type == "photo":
            photo = message.photo[-1].file_id
            bot.send_photo(user["id"], photo, message.caption)

        else:
            bot.send_message(message.chat.id, "Вы отправили сообщение не поддерживаемого типа. "
                                              "Пожалуйста, попробуйте снова после команды /send")


# добавление администратора
@bot.message_handler(commands=["add_admin"], func=lambda message: dbhelper.check_adm(message.chat.id))
@log
def command_add_admin(message):
    sent = bot.send_message(message.chat.id, "Введите id пользователя, которому вы хотите дать права администратора"
                                             "\nПредставлен набором чисел. "
                                             "\nЧтобы узнать свой id - воспользуйтесь @userinfobot."
                                             "\nДля отмены действия воспользуйтесь командой /cancel")
    bot.register_next_step_handler(sent, adding)


@log
def adding(message):
    if message.text == "/cancel":
        bot.send_message(message.chat.id, "Действие отменено")

    else:
        try:
            id_to_add = int(message.text)
            user = dbhelper.find_by_id(id_to_add)

            if user:
                if user.is_admin:
                    bot.send_message(message.chat.id, "Пользователь уже является администратором")

                else:
                    dbhelper.add_admin(id_to_add)
                    bot.send_message(message.chat.id, "Администратор успешно добавлен!")
                    bot.send_message(id_to_add, "Поздравляю с получением прав администратора!\n"
                                                "Чтобы ознакомиться с полным набором доступных Вам комманд, \n"
                                                "воспользуйтесь /admin")
            else:
                bot.send_message(message.chat.id, "Пользователь не найден!")

        except ValueError:
            bot.send_message(message.chat.id, "Возникла ошибка типа. "
                                              "Возможно вводимый id состоял не только из чисел или содержал пробелы")


# вывод всех существующих администраторов
@bot.message_handler(commands=["list_admin"], func=lambda message: dbhelper.check_adm(message.chat.id))
@log
def command_list_admin(message):
    res = dbhelper.get_all_admin()
    count = 0
    for i in res:
        count = count + 1
        bot.send_message(message.chat.id,
                         "Администратор №" + str(count) +
                         "\nИмя пользователя: " + str(i["username"]) +
                         "\nID пользователя: " + str(i["id"]))

    bot.send_message(message.chat.id, "Всего администраторов: " + str(count))


# удаление выбранного администратора
@bot.message_handler(commands=["remove_admin"], func=lambda message: dbhelper.check_adm(message.chat.id))
@log
def command_remove_admin(message):
    sent = bot.send_message(message.chat.id, "Введите id пользователя, которого вы хотите лишить прав администратора"
                                             "\nПредставлен набором чисел. "
                                             "\nЧтобы узнать свой id - воспользуйтесь @userinfobot."
                                             "\nДля отмены действия воспользуйтесь командой /cancel")
    bot.register_next_step_handler(sent, removing)


@log
def removing(message):
    if message.text == "/cancel":
        bot.send_message(message.chat.id, "Действие отменено")
    else:
        try:
            id_to_remove = int(message.text)
            user = dbhelper.find_by_id(id_to_remove)

            if not user:
                bot.send_message(message.chat.id, "Пользователь не найден!")
                return

            if user.is_admin:
                dbhelper.remove_admin(id_to_remove)
                bot.send_message(message.chat.id, "Администратор успешно удален!")

            else:
                bot.send_message(message.chat.id, "Пользователь не является администратором")

        except ValueError:
            bot.send_message(message.chat.id, "Возникла ошибка типа. "
                                              "Возможно вводимый id состоял не только из чисел или содержал пробелы")


# поиск пользователя по id
@bot.message_handler(commands=["find_by_id"], func=lambda message: dbhelper.check_adm(message.chat.id))
@log
def command_find_by_id(message):
    sent = bot.send_message(message.chat.id, "Введите id пользователя, данные о котором вы ходите получить"
                                             "\nПредставлен набором чисел. "
                                             "\nЧтобы узнать свой id - воспользуйтесь @userinfobot."
                                             "\nДля отмены действия воспользуйтесь командой /cancel")
    bot.register_next_step_handler(sent, find_by_id)


@log
def find_by_id(message):
    if message.text == "/cancel":
        bot.send_message(message.chat.id, "Действие отменено")

    else:
        try:
            id_to_find = int(message.text)
            user = dbhelper.find_by_id(id_to_find)

            if user:
                bot.send_message(message.chat.id,
                                 "ID пользователя: " + str(user["id"]) +
                                 "\nИмя пользователя: " + str(user["username"]) +
                                 "\nПодписка на новости с глобальной рассылки: " + str(user["subscription"]) +
                                 "\nНаправления, на которые оформлена подписка: " + str(user["directions"]))
            else:
                bot.send_message(message.chat.id, "Пользователь не найден!")

        except ValueError:
            bot.send_message(message.chat.id, "Возникла ошибка типа. "
                                              "Возможно вводимый id состоял не только из чисел или содержал пробелы")


bot.polling(none_stop=True)
