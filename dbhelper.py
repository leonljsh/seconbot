import json

from models import *


def insert(telegram_id, username, name):
    user, created = User.get_or_create(telegram_id=telegram_id, defaults={'username': username, 'name': name})

    if not created:
        user.username = username
        user.name = name
        user.save()


def get_all_users(page=None):
    if page is None:
        return [u for u in User.select()]
    else:
        return [u for u in User.select().limit(11).offset((page - 1))]


def get_all_tracks():
    return [t for t in Track.select()]


def get_user_tracks(telegram_id):
    tracks = (Track
              .select()
              .join(TrackSubscription)
              .join(User)
              .where(User.telegram_id == telegram_id))

    return [t for t in tracks]


def find(id):
    return User.get_or_none(User.id == int(id))


def find_by_id(telegram_id):
    return User.get_or_none(User.telegram_id == int(telegram_id))


def toggle_typing(telegram_id, state=None, admin=False):
    user = find_by_id(telegram_id)

    if state is None:
        user.state = User.STATE_TYPING if not user.is_typing else User.STATE_REGULAR
    else:
        target_state = User.STATE_ADMIN_TYPING if admin else User.STATE_TYPING
        user.state = target_state if state else User.STATE_REGULAR

    user.save()


def check_typing(telegram_id, admin=False):
    user = find_by_id(telegram_id)

    if not user:
        return False

    return user.state == User.STATE_TYPING and not admin or user.state == User.STATE_ADMIN_TYPING and admin


def check_adm(telegram_id):
    user = find_by_id(telegram_id)

    return user and user.is_admin


def toggle_admin(id, is_admin):
    user = find(id)

    user.is_admin = is_admin
    user.save()


def toggle_subscription(telegram_id, subscribed=True):
    user = find_by_id(telegram_id)

    if not user:
        return False

    user.is_subscribed = subscribed
    return bool(user.save())


def toggle_track_subscription(telegram_id, track_id):
    user = find_by_id(telegram_id)
    track_subscription, created = TrackSubscription.get_or_create(user=user, track_id=track_id,
                                                                  defaults={'user': user, 'track_id': track_id})

    if not created:
        track_subscription.delete_instance()


def save_last_menu_message_id(telegram_id, message_id):
    user = find_by_id(telegram_id)

    if not user:
        return

    user.last_menu_message_id = message_id
    user.save()


def create_support_request(telegram_id, message):
    user = find_by_id(telegram_id)

    Request.create(user=user, message=json.dumps(message))


def get_support_request(id):
    return Request.get_or_none(Request.id == id)


def get_support_requests(page=1):
    return Request.select().where(Request.published == False).order_by(Request.id).paginate(page, 5)


def count_support_requests():
    return Request.select().where(Request.published == False).count()


def mark_support_request_as_read(id):
    Request.update(published=True).where(Request.id == id).execute()


def mark_all_support_requests_as_read():
    Request.update(published=True).where(Request.published == False).execute()


def add_admin(user_id):
    pass
    # with TinyDB(data.storage_name) as db:
    #     user = Query()
    #     db.update({"administrator": True}, user.id == user_id)


def remove_admin(user_id):
    pass
    # with TinyDB(data.storage_name) as db:
    #     user = Query()
    #     db.update({"administrator": False}, user.id == user_id)


def get_all_admins():
    return [user for user in User.select().where(User.is_admin == True)]


def find_all_by_dir(direction):
    pass
    # user = Query()
    # with TinyDB(data.storage_name) as db:
    #     return db.search(user.directions.any(direction))


def find_all_subs():
    return [user for user in User.select().where(User.is_subscribed == True)]
