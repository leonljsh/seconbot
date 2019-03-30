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
        reply = bot.send_message(chat_id, text, reply_markup=help_markup())
        dbhelper.save_last_menu_message_id(chat_id, reply.message_id)
    else:
        try:
            show_menu(chat_id=chat_id, message_id=user.last_menu_message_id, text=text, markup=help_markup())
        except ApiException:
            show_main_menu(chat_id, text, True)


def show_menu(chat_id, text, markup, message_id=None):
    if not message_id:
        message_id = dbhelper.find_by_id(chat_id).last_menu_message_id

    bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="Markdown")
    bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=markup)


def help_markup():
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(types.InlineKeyboardButton("Расписание", callback_data="menu"),
               types.InlineKeyboardButton("Подписка", callback_data="subscribe_settings"),
               types.InlineKeyboardButton("Место проведения", callback_data="location"),
               types.InlineKeyboardButton("Ссылки", callback_data="links"))
    return markup


def sub_settings_markup():
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(types.InlineKeyboardButton("Новости", callback_data="news_settings"),
               types.InlineKeyboardButton("Направления", callback_data="direction_settings"))
    markup.row(types.InlineKeyboardButton("« Назад", callback_data="menu"))
    return markup


def news_settings_markup(user):
    markup = types.InlineKeyboardMarkup()
    button = "Подписаться на новости" if not user.is_subscribed else "Отписаться от новостей"

    markup.row(types.InlineKeyboardButton(text=button, callback_data="toggle_news"))
    markup.row(types.InlineKeyboardButton("« Назад", callback_data="subscribe_settings"))

    return markup


def settings_subscribe(message):
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

    show_menu(chat_id=message.chat.id, text=text, markup=sub_settings_markup())


def settings_news(message):
    user = dbhelper.find_by_id(message.chat.id)
    status = "активна" if user.is_subscribed else "неактивна"

    show_menu(message.chat.id, text="Подписка на новостную рассылку: *{}*.".format(status),
              markup=news_settings_markup(user))


def subscription_toggle(message):
    user = dbhelper.find_by_id(message.chat.id)
    should_be_subscribed = not user.is_subscribed

    dbhelper.toggle_subscription(message.chat.id, subscribed=should_be_subscribed)

    if should_be_subscribed:
        result_message = "Вы подписались на новостные рассылки! :)"
    else:
        result_message = "Вы отписались от новостных рассылок! :("

    user = dbhelper.find_by_id(message.chat.id)
    show_menu(chat_id=message.chat.id, text=result_message, markup=news_settings_markup(user))


def tracks_list(message):
    all_tracks = dbhelper.get_all_tracks()
    user_tracks = dbhelper.get_user_tracks(message.chat.id)

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    buttons = [types.InlineKeyboardButton(
        text="{}{}".format("[x] " if track.id in map(lambda track: track.id, user_tracks) else "", track.title),
        callback_data="subscribe_track_{}".format(track.id)) for track in all_tracks]

    keyboard.add(*buttons)
    keyboard.row(types.InlineKeyboardButton("« Назад", callback_data="subscribe_settings"))

    if not user_tracks:
        text = "Вы не подписаны ни на одно направление.\n\nВыберите направления, на которые хотите подписаться."

    else:
        text = "Направления, на которые вы подписаны:\n" \
               + "\n".join(["• {}".format(track.title) for track in user_tracks]) \
               + "\n\nНажмите на направление чтобы подписаться на новости или отписаться от него."

    show_menu(chat_id=message.chat.id, text=text, markup=keyboard)


def toggle_track_subscription(message, track_id):
    dbhelper.toggle_track_subscription(message.chat.id, int(track_id))
    tracks_list(message)


def send_links(message):
    keyboard = types.InlineKeyboardMarkup()

    keyboard.add(*[types.InlineKeyboardButton(**link) for link in data.links])
    keyboard.row(types.InlineKeyboardButton("« Назад", callback_data="menu"))

    show_menu(chat_id=message.chat.id, text="Подписывайся на наши социальные сети 🐴", markup=keyboard)


def send_location(message):
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    keyboard.add(types.KeyboardButton(text="Меню"))

    bot.send_message(chat_id=message.chat.id, text="Адрес: \nпр. Строителей, 168А, Пенза", reply_markup=keyboard)
    bot.send_location(chat_id=message.chat.id, latitude=53.220670, longitude=44.883901)


@bot.message_handler(commands=["start"])
@log
def command_start(message):
    user = dbhelper.find_by_id(int(message.chat.id))
    username = (message.from_user.first_name or message.from_user.username)

    if user:
        show_main_menu(message.chat.id, "С возвращением, {} :)".format(username), force=True)
    else:
        dbhelper.insert(message.chat.id, message.from_user.username)
        show_main_menu(message.chat.id, "Здравствуйте, {} :)".format(username), force=True)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    def show_menu_route(message):
        show_main_menu(message.chat.id, text="Меню взаимодействия:")

    routing = {
        "subscribe_settings": settings_subscribe,
        "links": send_links,
        "location": send_location,
        "direction_settings": tracks_list,
        "news_settings": settings_news,
        "toggle_news": subscription_toggle,
        "menu": show_menu_route
    }

    if call.data.startswith("subscribe_track_"):
        method = partial(toggle_track_subscription, track_id=call.data.split("_")[-1])
    else:
        method = routing.get(call.data, show_menu_route)

    method(call.message)


@bot.message_handler(func=lambda message: message.text.lower() in ["меню", "menu"])
@log
def new_menu(message):
    show_main_menu(message.chat.id, text="Меню взаимодействия:", force=True)


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


# обработка булщита
@bot.message_handler(func=lambda message: True, content_types=["text"])
@log
def command_default(message):
    show_main_menu(message.chat.id, "Я еще не научился отвечать на такие запросы :)"
                                    "\nДавайте ограничимся меню взаимодействия?", force=True)


bot.polling(none_stop=True)
