# -*- coding: utf-8 -*-

import json
from datetime import datetime
import telebot
import data
from telebot import apihelper, types
import dbhelper
from functools import partial

administration = {
    'direct_post': 'рассылка по направлениям',
    'send_post': 'массовая рассылка для тех кто подписан на новостные рассылки',
    'emergency_post': 'массовая рассылка без учета подписки '
                      '(каждому, кто хотя бы раз запускал бота и записан в базе данных)',
    'add_admin': 'добавить администратора',
    'remove_admin': 'удалить администратора',
    'list_admin': 'вывести id всех администраторов',
    'find_by_id': 'найти в базе данных пользователя и вывести информацию  о нем'
}

botToken = data.token
bot = telebot.TeleBot(botToken)
print(bot.get_me())


def log(func):
    def _(message, *args, **kwargs):
        print('================')
        print(datetime.now())
        print('From: ' + str(message.from_user.first_name) +
              '\nid: ' + str(message.from_user.id) +
              '\nText: ' + str(message.text))
        print("Function:", func.__name__)
        func(message, *args, *kwargs)

    return _


@bot.message_handler(commands=['start'])
@log
def command_start(message):
    res = dbhelper.exists(message.chat.id)
    if res:
        bot.send_message(message.chat.id, "Бот уже был запущен Вами :)", reply_markup=help_markup())
    else:
        dbhelper.insert(message.chat.id, message.from_user.username)
        bot.send_message(message.chat.id, "Здравствуйте, " + message.from_user.first_name, reply_markup=help_markup())


hideBoard = types.ReplyKeyboardRemove()


def help_markup():
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(types.InlineKeyboardButton("Настройки подписки", callback_data="subscribe_settings"),
               types.InlineKeyboardButton("Место проведения", callback_data="location"),
               types.InlineKeyboardButton("Ссылки", callback_data="links"))
    return markup


def sub_settings_markup():
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(types.InlineKeyboardButton('Новостная подписка', callback_data="news_settings"),
               types.InlineKeyboardButton('Подписка на направления', callback_data="direction_settings"))
    return markup


def news_settings_markup(subscribed):
    markup = types.InlineKeyboardMarkup(row_width=1)
    if not subscribed:
        button = types.InlineKeyboardButton(text="Подписаться на новости", callback_data="sub_to_news")
    else:
        button = types.InlineKeyboardButton(text="Отписаться от новостей", callback_data="unsub_from_news")

    markup.add(button)
    return markup


def direction_settings_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(text="Подписаться на направление", callback_data='sub_to_dir'),
               types.InlineKeyboardButton(text="Отписаться от направления", callback_data='unsub_from_dir'))
    return markup


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    routing = {
        'subscribe_settings': settings_subscribe,
        'links': command_links,
        'location': command_location,
        'direction_settings': settings_direction,
        'news_settings': settings_news,
        'sub_to_news': settings_subscribe_news,
        'unsub_from_news': settings_unsubscribe_news,
        'sub_to_dir': settings_subscribe_to_direction
    }

    method = routing.get(call.data)
    method(call.message)


def settings_subscribe(message):
    bot.send_message(chat_id=message.chat.id, text='Что вы хотите настроить?', reply_markup=sub_settings_markup())


def settings_news(message):
    result = dbhelper.check_sub(message.chat.id)
    status = 'активна' if result else 'неактивна'

    bot.send_message(message.chat.id, text='Подписка на новостную рассылку: {}.'.format(status),
                     reply_markup=news_settings_markup(result))


def settings_subscribe_news(message):
    dbhelper.subscribe(message.chat.id)
    bot.send_message(message.chat.id, 'Вы подписались на новостные рассылки! :)')
    command_menu(message)


def settings_unsubscribe_news(message):
    dbhelper.unsubscribe(message.chat.id)
    bot.send_message(message.chat.id, 'Вы отписались от новостных рассылок! :(')
    command_menu(message)


def settings_direction(message):
    directions = dbhelper.get_sub_dir(message.chat.id)
    bot.send_message(message.chat.id, text='Направления, на которые Вы подписаны: ' + str(directions) +
                                           '\nЧто бы вы хотели сделать?')


def settings_subscribe_to_direction(message):
    directions_list = list(dict.fromkeys(data.directions + dbhelper.get_sub_dir(message.chat.id)))
    direction_markup = types.InlineKeyboardMarkup()
    for direction in directions_list:
        direction_markup.add(types.InlineKeyboardButton(text=direction))
    bot.send_message(message.chat.id,
                     text='Выберите направления, на которое вы хотите подписаться: ',
                     reply_markup=direction_markup)


def command_links(message):
    keyboard = types.InlineKeyboardMarkup()
    vk_link = types.InlineKeyboardButton(text="Вконтакте", url="https://vk.com/secon2019")
    inst_link = types.InlineKeyboardButton(text="Instagram", url="https://www.instagram.com/secon_ru/")
    fb_link = types.InlineKeyboardButton(text="Facebook", url="https://www.facebook.com/events/259607524716333")
    site_link = types.InlineKeyboardButton(text="Сайт", url="https://2019.secon.ru/")
    keyboard.add(vk_link, inst_link, fb_link, site_link)
    bot.send_message(chat_id=message.chat.id,
                     text="Наши ссылки :)",
                     reply_markup=keyboard)


def command_location(message):
    bot.send_message(chat_id=message.chat.id, text='Адрес: \nпр. Строителей, 168А, Пенза')
    bot.send_location(chat_id=message.chat.id, latitude=53.220670, longitude=44.883901)
    # 53.220670, 44.883901


@bot.message_handler(commands=['menu'])
@log
def command_menu(message):
    bot.send_message(message.chat.id, text='Меню взаимодействия:', reply_markup=help_markup())


# ==============Команды администратора=================
@bot.message_handler(commands=['admin'], func=lambda message: dbhelper.check_adm(message.chat.id))
@log
def command_admin_help(message):
    cid = message.chat.id
    help_admin = "Список доступных команд для администратора: \n"
    for key in administration:
        help_admin += "/" + key + ": "
        help_admin += administration[key] + "\n"
    bot.send_message(cid, help_admin)


# новостная рассылка (без учета подписки)
@bot.message_handler(commands=['emergency_post'], func=lambda message: dbhelper.check_adm(message.chat.id))
@log
def command_send(message):
    sent = bot.send_message(message.chat.id, 'Напишите пост. Его увидят все пользователи без исключения.'
                                             '\nБудьте внимательны, его нельзя будет редактировать!'
                                             '\nДля отмены написания используйте команду /cancel')
    bot.register_next_step_handler(sent, sending)


@log
def sending(message: telebot.types.Message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, 'рассылка была отменена')

    else:
        users_data = json.load(open(data.storage_name))
        for user in users_data['_default']:
            uid = users_data['_default'][user]['id']
            if message.content_type == "text":
                bot.send_message(uid, str(message.text))

            elif message.content_type == "photo":
                # print("\x1b[32;1m==== NEW PHOTO ====\x1b[0m")
                photo = message.photo[-1].file_id
                bot.send_photo(uid, photo, message.caption)

            else:
                bot.send_message(message.chat.id, 'Вы отправили сообщение не поддерживаемого типа. '
                                                  'Пожалуйста, попробуйте снова после команды /send')


# новостная рассылка (с учетом подписки)
@bot.message_handler(commands=['send_post'], func=lambda message: dbhelper.check_adm(message.chat.id))
@log
def command_send(message):
    sent = bot.send_message(message.chat.id, 'Напишите пост. Его увидят все пользователи, '
                                             'подписанные на новостную рассылку.'
                                             '\nБудьте внимательны, его нельзя будет редактировать!'
                                             '\nДля отмены написания используйте команду /cancel')
    bot.register_next_step_handler(sent, sending)


@log
def sending(message: telebot.types.Message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, 'рассылка была отменена')

    else:
        list_of_users = dbhelper.find_all_subs()
        for user in list_of_users:
            if message.content_type == "text":
                bot.send_message(user['id'], str(message.text))

            elif message.content_type == "photo":
                # print("\x1b[32;1m==== NEW PHOTO ====\x1b[0m")
                photo = message.photo[-1].file_id
                bot.send_photo(user['id'], photo, message.caption)

            else:
                bot.send_message(message.chat.id, 'Вы отправили сообщение не поддерживаемого типа. '
                                                  'Пожалуйста, попробуйте снова после команды /send')


# массовая рассылка по направлениям
@bot.message_handler(commands=['direct_post'], func=lambda message: dbhelper.check_adm(message.chat.id))
@log
def command_directly(message):
    sent = bot.send_message(message.chat.id, 'Выбор направления для рассылки',
                            '\nДля отмены написания используйте команду /cancel')
    bot.register_next_step_handler(sent, direction_choose)


# выбор направления для рассылки
def direction_choose(message):
    bot.send_message(message.chat.id, text='mobile == Мобильная разработка\n'
                                           'quality == Контроль качества\n'
                                           'database == Базы данных\n'
                                           'design == Дизайн и компьютерная графика\n'
                                           'frontend == Frontend программирование\n'
                                           'leading == Управление проектами (управление распределенными командами)\n'
                                           'IoT == Интернет вещей (IoT)\n'
                                           'data_science == AI, ML, BigData\n'
                                           'start_up == Start ups\n'
                                           'vr == VR/AR\n'
                                           'gamedev == GameDev\n'
                                           'devops == DevOps\n'
                                           'java == Java-программирование\n'
                                           'master == Мастер-классы')
    if message.text == '/cancel':
        bot.send_message(message.chat.id, 'Рассылка была отменена')

    elif message.text in data.directions:
        print(message.text)
        direction_data = partial(direction_send, message.text)
        sent = bot.send_message(message.chat.id, 'Направление: ' + message.text + '\nВведите текст')
        bot.register_next_step_handler(sent, direction_data)

    else:
        bot.send_message(message.chat.id, 'Несуществующее направление')


# рассылка по выбранному направлению
def direction_send(direction, message):
    list_of_users = dbhelper.find_all_by_dir(direction)
    print(direction)
    print(list_of_users)
    for user in list_of_users:
        if message.content_type == "text":
            bot.send_message(user['id'], str(message.text))

        elif message.content_type == "photo":
            # print("\x1b[32;1m==== NEW PHOTO ====\x1b[0m")
            photo = message.photo[-1].file_id
            bot.send_photo(user['id'], photo, message.caption)

        else:
            bot.send_message(message.chat.id, 'Вы отправили сообщение не поддерживаемого типа. '
                                              'Пожалуйста, попробуйте снова после команды /send')


# добавление администратора
@bot.message_handler(commands=['add_admin'], func=lambda message: dbhelper.check_adm(message.chat.id))
@log
def command_add_admin(message):
    sent = bot.send_message(message.chat.id, "Введите id пользователя, которому вы хотите дать права администратора"
                                             "\nПредставлен набором чисел. "
                                             "\nЧтобы узнать свой id - воспользуйтесь @userinfobot."
                                             "\nДля отмены действия воспользуйтесь командой /cancel")
    bot.register_next_step_handler(sent, adding)


@log
def adding(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, 'Действие отменено')

    else:
        try:
            id_to_add = int(message.text)
            res = dbhelper.exists(id_to_add)
            if res:
                is_admin = dbhelper.check_adm(id_to_add)
                print(is_admin)

                if is_admin:
                    bot.send_message(message.chat.id, 'Пользователь уже является администратором')

                else:
                    dbhelper.add_admin(id_to_add)
                    bot.send_message(message.chat.id, "Администратор успешно добавлен!")
                    bot.send_message(id_to_add, 'Поздравляю с получением прав администратора!\n'
                                                'Чтобы ознакомиться с полным набором доступных Вам комманд, \n'
                                                'воспользуйтесь /admin')
            else:
                bot.send_message(message.chat.id, 'Пользователь не найден!')

        except ValueError:
            bot.send_message(message.chat.id, 'Возникла ошибка типа. '
                                              'Возможно вводимый id состоял не только из чисел или содержал пробелы')


# вывод всех существующих администраторов
@bot.message_handler(commands=['list_admin'], func=lambda message: dbhelper.check_adm(message.chat.id))
@log
def command_list_admin(message):
    res = dbhelper.get_all_admin()
    count = 0
    for i in res:
        count = count + 1
        bot.send_message(message.chat.id,
                         'Администратор №' + str(count) +
                         '\nИмя пользователя: ' + str(i['username']) +
                         '\nID пользователя: ' + str(i['id']))

    bot.send_message(message.chat.id, "Всего администраторов: " + str(count))


# удаление выбранного администратора
@bot.message_handler(commands=['remove_admin'], func=lambda message: dbhelper.check_adm(message.chat.id))
@log
def command_remove_admin(message):
    sent = bot.send_message(message.chat.id, "Введите id пользователя, которого вы хотите лишить прав администратора"
                                             "\nПредставлен набором чисел. "
                                             "\nЧтобы узнать свой id - воспользуйтесь @userinfobot."
                                             "\nДля отмены действия воспользуйтесь командой /cancel")
    bot.register_next_step_handler(sent, removing)


@log
def removing(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, 'Действие отменено')

    else:
        try:
            id_to_remove = int(message.text)
            res = dbhelper.exists(id_to_remove)
            if res:
                is_admin = dbhelper.check_adm(id_to_remove)

                if is_admin:
                    dbhelper.remove_admin(id_to_remove)
                    bot.send_message(message.chat.id, "Администратор успешно удален!")

                else:
                    bot.send_message(message.chat.id, "Пользователь не является администратором")

            else:
                bot.send_message(message.chat.id, 'Пользователь не найден!')

        except ValueError:
            bot.send_message(message.chat.id, 'Возникла ошибка типа. '
                                              'Возможно вводимый id состоял не только из чисел или содержал пробелы')


# поиск пользователя по id
@bot.message_handler(commands=['find_by_id'], func=lambda message: dbhelper.check_adm(message.chat.id))
@log
def command_find_by_id(message):
    sent = bot.send_message(message.chat.id, "Введите id пользователя, данные о котором вы ходите получить"
                                             "\nПредставлен набором чисел. "
                                             "\nЧтобы узнать свой id - воспользуйтесь @userinfobot."
                                             "\nДля отмены действия воспользуйтесь командой /cancel")
    bot.register_next_step_handler(sent, find_by_id)


@log
def find_by_id(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, 'Действие отменено')

    else:
        try:
            id_to_find = int(message.text)
            res = dbhelper.exists(id_to_find)
            if res:
                user = dbhelper.find_by_id(id_to_find)
                bot.send_message(message.chat.id,
                                 'ID пользователя: ' + str(user['id']) +
                                 '\nИмя пользователя: ' + str(user['username']) +
                                 '\nПодписка на новости с глобальной рассылки: ' + str(user['subscription']) +
                                 '\nНаправления, на которые оформлена подписка: ' + str(user['directions']))
            else:
                bot.send_message(message.chat.id, 'Пользователь не найден!')

        except ValueError:
            bot.send_message(message.chat.id, 'Возникла ошибка типа. '
                                              'Возможно вводимый id состоял не только из чисел или содержал пробелы')


# обработка булщита
@bot.message_handler(func=lambda message: True, content_types=['text'])
@log
def command_default(message):
    bot.send_message(message.chat.id, "Я еще не научился отвечать на такие запросы :)"
                                      "\nДавайте ограничимся меню взаимодействия?",
                     reply_markup=help_markup())


bot.polling(none_stop=True)
