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
    USERDB = dict(mapname=dict())
    with open(path.join(PATH, "userdb"), "w") as f:
        f.write(json.dumps(USERDB))
    path.os.chmod(path.join(PATH, "userdb"), 0o600)

### THREAD MANAGEMENT ###

def thread_index(key="lastmod"):
    result = list()
    for ID in path.os.listdir(path.join(PATH, "threads")):
        thread = thread_load(ID)
        thread.pop("replies")
        result.append(thread)
    return sorted(result, key=lambda i: i[key])


def thread_create(author, body, title, tags):
    ID = uuid1().hex
    # make sure None, False, and empty arrays are always repped consistently
    tags = tags if tags else []
    scheme = schema.thread(ID, author, body, title, tags)
    thread_dump(ID, scheme)
    return scheme


def thread_load(ID):
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
    reply = schema.reply(thread["reply_count"], author, body)
    thread["replies"].append(reply)
    thread_dump(ID, thread)
    return reply


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
            return USERDB["mapname"][name_or_id]
    except KeyError:
        return False


def user_register(auth_hash, name, quip, bio):
    if USERDB["mapname"].get(name):
        return schema.error(4, "Username taken.")

    ID = uuid1().hex
    scheme = schema.user_internal(ID, auth_hash, name, quip, bio, False)
    USERDB.update({ID: scheme})
    USERDB["mapname"].update({name: ID})
    user_dbdump(USERDB)
    return scheme


def user_get(ID):
    user = USERDB[ID]
    return schema.user_external(
        ID, user["name"], user["quip"],
        user["bio"], user["admin"])


def user_auth(ID, auth_hash):
    return auth_hash == USERDB[ID]["auth_hash"]


def user_update(ID, **params):
    USERDB[ID].update(params)
    return USERDB[ID]
