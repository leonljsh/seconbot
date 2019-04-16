from peewee import BooleanField, CharField, ForeignKeyField, IntegerField, Model, SqliteDatabase, TextField

import data

db = SqliteDatabase(data.storage_name)


class User(Model):
    STATE_REGULAR = 0
    STATE_TYPING = 1
    STATE_ADMIN_TYPING = 2

    telegram_id = IntegerField(unique=True)
    name = CharField(null=True)
    username = CharField(null=True)
    is_admin = BooleanField(default=False)
    is_subscribed = BooleanField(default=True)
    state = IntegerField(default=STATE_REGULAR)

    last_menu_message_id = IntegerField(null=True)

    class Meta:
        database = db

    @property
    def is_typing(self):
        return self.state == self.STATE_TYPING


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


class Request(Model):
    user = ForeignKeyField(User)
    message = TextField()
    published = BooleanField(default=False)
    publisher = ForeignKeyField(User, null=True)

    class Meta:
        database = db


need_insert = not Track.table_exists()
db.create_tables([User, Track, TrackSubscription, Request], safe=True)

if need_insert:
    for track in data.api.get_tracks(day=1):
        Track.create(id=track["id"], title=track["name"])
