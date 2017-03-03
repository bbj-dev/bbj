from src import formatting
from uuid import uuid1
from src import schema
from time import time
from os import path
import json

PATH = "/home/desvox/bbj/"

if not path.isdir(PATH):
    path.os.mkdir(PATH, mode=0o744)

if not path.isdir(path.join(PATH, "threads")):
    path.os.mkdir(path.join(PATH, "threads"), mode=0o744)

try:
    with open(path.join(PATH, "userdb"), "r") as f:
        USERDB = json.loads(f.read())

except FileNotFoundError:
    USERDB = dict(namemap=dict())
    with open(path.join(PATH, "userdb"), "w") as f:
        f.write(json.dumps(USERDB))
    path.os.chmod(path.join(PATH, "userdb"), 0o600)


### THREAD MANAGEMENT ###

def thread_index(key="lastmod", markup=True):
    result = list()
    for ID in path.os.listdir(path.join(PATH, "threads")):
        thread = thread_load(ID, markup)
        thread.pop("replies")
        result.append(thread)
    return sorted(result, key=lambda i: i[key], reverse=True)


def thread_create(author, body, title, tags):
    ID = uuid1().hex
    if tags:
        tags = [tag.strip() for tag in tags.split(",")]
    else: # make sure None, False, and empty arrays are always repped consistently
        tags = []
    scheme = schema.thread(ID, author, body, title, tags)
    thread_dump(ID, scheme)
    return scheme


def thread_load(ID, markup=True):
    try:
        with open(path.join(PATH, "threads", ID), "r") as f:
            return json.loads(f.read())
    except FileNotFoundError:
        return False


def thread_dump(ID, obj):
    with open(path.join(PATH, "threads", ID), "w") as f:
        f.write(json.dumps(obj))


def thread_reply(ID, author, body):
    thread = thread_load(ID)
    if not thread:
        return schema.error(7, "Requested thread does not exist.")

    thread["reply_count"] += 1
    thread["lastmod"] = time()

    if thread["replies"]:
        lastpost = thread["replies"][-1]["post_id"]
    else:
        lastpost = 1

    reply = schema.reply(lastpost + 1, author, body)
    thread["replies"].append(reply)
    thread_dump(ID, thread)
    return reply


def index_reply(reply_list, post_id):
    for index, reply in enumerate(reply_list):
        if reply["post_id"] == post_id:
            return index
    else:
        raise IndexError


def edit_handler(json, thread=None):
    try:
        target_id = json["post_id"]
        if not thread:
            thread = thread_load(json["thread_id"])
            if not thread:
                return False, schema.error(7, "Requested thread does not exist.")


        if target_id == 1:
            target = thread
        else:
            target = thread["replies"][
                index_reply(thread["replies"], target_id)]

        if not user_is_admin(json["user"]):
            if json["user"] != target["author"]:
                return False, schema.error(10,
                    "non-admin attempt to edit another user's message")

            elif (time() - target["created"]) > 86400:
                return False, schema.error(9,
                    "message is too old to edit (24hr limit)")

        return True, target

    except IndexError:
        return False, schema.error(3, "post_id out of bounds for requested thread")


### USER MANAGEMENT ###

def user_dbdump(dictionary):
    with open(path.join(PATH, "userdb"), "w") as f:
        f.write(json.dumps(dictionary))


def user_resolve(name_or_id):
    check = USERDB.get(name_or_id)
    try:
        if check:
            return name_or_id
        else:
            return USERDB["namemap"][name_or_id]
    except KeyError:
        return False


def user_register(auth_hash, name, quip, bio):
    if USERDB["namemap"].get(name):
        return schema.error(4, "Username taken.")

    for ok, error in [
        user_namecheck(name),
        user_authcheck(auth_hash),
        user_quipcheck(quip),
        user_biocheck(bio)]:

        if not ok:
            return error

    ID = uuid1().hex
    scheme = schema.user_internal(ID, auth_hash, name, quip, bio, False)
    USERDB.update({ID: scheme})
    USERDB["namemap"].update({name: ID})
    user_dbdump(USERDB)
    return scheme


def user_get(ID):
    user = USERDB[ID]
    return schema.user_external(
        ID, user["name"], user["quip"],
        user["bio"], user["admin"])


def user_auth(ID, auth_hash):
    return auth_hash == USERDB[ID]["auth_hash"]


def user_is_admin(ID):
    return USERDB[ID]["admin"]


def user_update(ID, **params):
    USERDB[ID].update(params)
    return USERDB[ID]


### SANITY CHECKS ###

def contains_nonspaces(string):
    return any([char in string for char in "\t\n\r\x0b\x0c"])


def user_namecheck(name):
    if not name:
        return False, schema.error(4,
            "Username may not be empty.")

    elif contains_nonspaces(name):
        return False, schema.error(4,
            "Username cannot contain whitespace chars besides spaces.")

    elif len(username) > 24:
        return False, schema.error(4,
            "Username is too long (max 24 chars)")

    return True, True


def user_authcheck(auth_hash):
    if not auth_hash:
        return schema.error(3,
            "auth_hash may not be empty")

    elif len(auth_hash) != 64:
        return False, schema.error(4,
            "Client error: invalid SHA-256 hash.")

    return True, True


def user_quipcheck(quip):
    if not quip:
        return ""

    elif contains_nonspaces(quip):
        return False, schema.error(4,
            "Quip cannot contain whitespace chars besides spaces.")

    elif len(quip) > 120:
        return False, schema.error(4,
            "Quip is too long (max 120 chars)")

    return True, True


def user_biocheck(bio):
    if not bio:
        return ""

    elif len(bio) > 4096:
        return False, schema.error(4,
            "Bio is too long (max 4096 chars)")

    return True, True
