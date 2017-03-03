from src import formatting
from src import schema
from time import time
from src import db


endpoints = {
    "check_auth":      ["user", "auth_hash"],
    "is_registered":   ["target_user"],
    "is_admin":        ["target_user"],
    "thread_index":    [],
    "thread_load":     ["thread_id"],
    "thread_create":   ["title", "body", "tags"],
    "thread_reply":    ["thread_id", "body"],
    "edit_post":       ["thread_id", "post_id", "body"],
    "edit_query":      ["thread_id", "post_id"],
    "can_edit":        ["thread_id", "post_id"],
    "user_register":   ["user", "auth_hash", "quip", "bio"],
    "user_get":        ["target_user"],
    "user_name_to_id": ["target_user"]
}


authless = [
    "is_registered",
    "user_register"
]


# this is not actually an endpoint, but produces a required
# element of thread responses.
def create_usermap(thread, index=False):
    if index:
        return {user: db.user_get(user) for user in
                  {i["author"] for i in thread}}

    result = {reply["author"] for reply in thread["replies"]}
    result.add(thread["author"])
    return {x: db.user_get(x) for x in result}


def user_name_to_id(json):
    """
    Returns a string of the target_user's ID when it is
    part of the database: a non-existent user will return
    a boolean false.
    """
    return db.user_resolve(json["target_user"])


def is_registered(json):
    """
    Returns true or false whether target_user is registered
    in the system. This function only takes usernames: not
    user IDs.
    """
    return bool(db.USERDB["namemap"].get(json["target_user"]))


def check_auth(json):
    "Returns true or false whether auth_hashes matches user."
    return bool(db.user_auth(json["user"], json["auth_hash"]))


def is_admin(json):
    """
    Returns true or false whether target_user is a system
    administrator. Takes a username or user ID. Nonexistent
    users return false.
    """
    user = db.user_resolve(json["target_user"])
    if user:
        return db.user_is_admin(user)
    return False


def user_register(json):
    """
    Registers a new user into the system. Returns the new internal user
    object on success, or an error response.

    auth_hash should be a hexadecimal SHA-256 string, produced from a
      UTF-8 password string.

    user should be a string containing no newlines and
      under 24 characters in length.

    quip is a string, up to 120 characters, provided by the user
      the acts as small bio, suitable for display next to posts
      if the client wants to. Whitespace characters besides space
      are not allowed. The string may be empty.

    bio is a string, up to 4096 chars, provided by the user that
      can be shown on profiles. There are no character type limits
      for this entry. The string may be empty.

    All errors for this endpoint with code 4 should show the
    description direcrtly to the user.

    """

    return schema.response(
        db.user_register(
            json["auth_hash"],
            json["user"],
            json["quip"],
            json["bio"]))


def user_get(json):
    """
    On success, returns an external user object for target_user (ID or name).
    If the user isn't in the system, returns false.
    """
    user = db.user_resolve(json["target_user"])
    if not user:
        return False
    return db.user_get(user)


def thread_index(json):
    index = db.thread_index(markup=not json.get("nomarkup"))
    return schema.response({"threads": index}, create_usermap(index, True))


def thread_load(json):
    thread = db.thread_load(json["thread_id"], not json.get("nomarkup"))
    if not thread:
        return schema.error(7, "Requested thread does not exist")
    return schema.response(thread, create_usermap(thread))


def thread_create(json):
    thread = db.thread_create(
        json["user"],
        json["body"],
        json["title"],
        json["tags"])
    if json.get("nomarkup"):
        thread["body"] = formatting.cleanse(thread["body"])
    return schema.response(thread)


def thread_reply(json):
    reply = db.thread_reply(
        json["thread_id"],
        json["user"],
        json["body"])
    if json.get("nomarkup"):
        reply["body"] = formatting.cleanse(reply["body"])
    return schema.response(reply)


def edit_query(json):
    return db.edit_handler(json)[1]


def can_edit(json):
    return db.edit_handler(json)[0]


def edit_post(json):
    thread = db.thread_load(json["thread_id"])
    admin = db.user_is_admin(json["user"])
    target_id = json["post_id"]
    ok, obj = db.edit_handler(json, thread)

    if ok:
        obj["body"] = json["body"]
        obj["lastmod"] = time()
        obj["edited"] = True
        db.thread_dump(json["thread_id"], thread)
    return obj
