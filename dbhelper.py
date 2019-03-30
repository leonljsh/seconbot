from tinydb import TinyDB, Query
import data


def insert(user_id, username):
    with TinyDB(data.storage_name) as db:
        user = Query()
        if not db.contains(user.id == user_id):
            db.insert({"id": user_id,
                       "username": username,
                       "subscription": True,
                       "administrator": False,
                       "directions": []})
        else:
            db.update({"username": username}, user.id == user_id)


def get_sub_dir(user_id):
    with TinyDB(data.storage_name) as db:
        user = db.get(Query()['id'] == user_id)
        return user.get('directions')


def update_sub_dir(user_id, direction):
    with TinyDB(data.storage_name) as db:
        user = Query()
        db.update({"directions": direction}, user.id == user_id)


def find_by_id(user_id):
    with TinyDB(data.storage_name) as db:
        user = db.get(Query()['id'] == user_id)
        return user


def check_sub(user_id):
    with TinyDB(data.storage_name) as db:
        user = db.get(Query()['id'] == user_id)

        if not user:
            return False

        return user.get('subscription')


def check_adm(user_id):
    with TinyDB(data.storage_name) as db:
        user = db.get(Query()['id'] == user_id) or {}
        return user.get('administrator')


def update(user_id, username):
    with TinyDB(data.storage_name) as db:
        user = Query()
        db.update({"username": username}, user.id == user_id)


def subscribe(user_id):
    with TinyDB(data.storage_name) as db:
        user = Query()
        try:
            db.update({"subscription": True}, user.id == int(user_id))
            return True
        except ValueError:
            return False


def unsubscribe(user_id):
    with TinyDB(data.storage_name) as db:
        user = Query()
        try:
            db.update({"subscription": False}, user.id == int(user_id))
            return True
        except ValueError:
            return False


def add_admin(user_id):
    with TinyDB(data.storage_name) as db:
        user = Query()
        db.update({"administrator": True}, user.id == user_id)


def remove_admin(user_id):
    with TinyDB(data.storage_name) as db:
        user = Query()
        db.update({"administrator": False}, user.id == user_id)


def remove(user_id):
    with TinyDB(data.storage_name) as db:
        user = Query()
        try:
            db.remove(user.id == int(user_id))
            return True
        except ValueError:
            return False


def exists(user_id):
    user = Query()
    with TinyDB(data.storage_name) as db:
        return db.contains(user.id == user_id)


def get_all_admin():
    user = Query()
    with TinyDB(data.storage_name) as db:
        return db.search(user.administrator == True)


def find_all_by_dir(direction):
    user = Query()
    with TinyDB(data.storage_name) as db:
        return db.search(user.directions.any(direction))


def find_all_subs():
    user = Query()
    with TinyDB(data.storage_name) as db:
        return db.search(user.subscription == True)
