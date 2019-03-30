from peewee import BooleanField, CharField, ForeignKeyField, IntegerField, Model, SqliteDatabase

import data

db = SqliteDatabase(data.storage_name)


class User(Model):
    telegram_id = IntegerField(unique=True)
    username = CharField(null=True)
    is_admin = BooleanField(default=False)
    is_subscribed = BooleanField(default=True)

    last_menu_message_id = IntegerField(null=True)

    class Meta:
        database = db


class Track(Model):
    title = CharField(max_length=64)

    class Meta:
        database = db


class TrackSubscription(Model):
    user = ForeignKeyField(User)
    track = ForeignKeyField(Track)

    class Meta:
        database = db
        indexes = (
            (("user_id", "track_id"), True),
        )


need_insert = not Track.table_exists()
db.create_tables([User, Track, TrackSubscription], safe=True)

if need_insert:
    for track in data.api.get_tracks(day=1):
        Track.create(id=track["id"], title=track["name"])
