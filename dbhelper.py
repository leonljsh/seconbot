from models import *


def insert(telegram_id, username):
    user, created = User.get_or_create(telegram_id=telegram_id, defaults={'username': username})

    if not created:
        user.username = username
        user.save()


def get_all_tracks():
    return [t for t in Track.select()]


def get_user_tracks(telegram_id):
    tracks = (Track
              .select()
              .join(TrackSubscription)
              .join(User)
              .where(User.telegram_id == telegram_id))

    return [t for t in tracks]


def find_by_id(telegram_id):
    return User.get_or_none(User.telegram_id == telegram_id)


def check_adm(telegram_id):
    user = find_by_id(telegram_id)

    return user.is_admin


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


def get_all_admin():
    return [user for user in User.select().where(User.is_admin == True)]


def find_all_by_dir(direction):
    pass
    # user = Query()
    # with TinyDB(data.storage_name) as db:
    #     return db.search(user.directions.any(direction))


def find_all_subs():
    return [user for user in User.select().where(User.is_subscribed == True)]
