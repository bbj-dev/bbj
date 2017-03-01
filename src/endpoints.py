from src import schema
from src import db
from json import dumps

endpoints = {
    "check_auth": ["user", "auth_hash"],
    "is_registered": ["target_user"],
    "thread_load": ["thread_id"],
    "thread_index": [],
    "thread_create": ["title", "body", "tags"],
    "thread_reply": ["thread_id", "body"],
    "user_register": ["user", "auth_hash", "avatar", "bio"],
    "user_get": ["target_user"],
}


authless = [
    "is_registered",
    "user_register"
]


def create_usermap(thread, index=False):
    if index:
        return {user: db.user_get(user) for user in
                  {i["author"] for i in thread}}

    result = {reply["author"] for reply in thread["replies"]}
    result.add(thread["author"])
    return {x: db.user_get(x) for x in result}


def is_registered(json):
    return dumps(bool(db.USERDB["mapname"].get(json["target_user"])))


def check_auth(json):
    return dumps(bool(db.user_auth(json["user"], json["auth_hash"])))


def user_register(json):
    return schema.response(
        db.user_register(
            json["auth_hash"],
            json["user"],
            json["avatar"],
            json["bio"]))


def thread_index(json):
    index = db.thread_index()
    return schema.response(
        {"threads": index}, create_usermap(index, True))


def thread_load(json):
    thread = db.thread_load(json["thread_id"])
    if not thread:
        return schema.error(7, "Requested thread does not exist")
    return schema.response(thread, create_usermap(thread))


def thread_create(json):
    thread = db.thread_create(
        json["user"],
        json["body"],
        json["title"],
        json["tags"])
    return schema.response(thread, create_usermap(thread))


def thread_reply(json):
    thread = db.thread_reply(
        json["thread_id"],
        json["user"],
        json["body"])
    return schema.response(thread)
