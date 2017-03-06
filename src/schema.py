from src import formatting
from time import time


def base():
    return {
        "error": False
    }


def response(dictionary, usermap=None):
    result = base()
    result.update(dictionary)
    if usermap:
        result["usermap"] = usermap
    return result


def error(code, description):
    result = base()
    result.update({
        "error": {
            "description": description, # string
            "code": code                # integer
        }
    })
    return result


def user_internal(ID, auth_hash, name, quip, bio, admin):
    if not quip:
        quip = ""

    if not bio:
        bio = ""

    return {
        "user_id":   ID,       # string
        "quip":      quip,     # (possibly empty) string
        "bio":       bio,      # (possibly empty) string
        "name":      name,     # string
        "admin":     admin,    # boolean
        "auth_hash": auth_hash # SHA256 string
    }


def user_external(ID, name, quip, bio, admin):
    if not quip:
        quip = ""

    if not bio:
        bio = ""

    return {
        "user_id":   ID,   # string
        "quip":      quip, # (possibly empty) string
        "name":      name, # string
        "bio":       bio,  # string
        "admin":     admin # boolean
    }


def thread(ID, author, body, title, tags):
    if not tags:
        tags = list()

    body = formatting.parse(body, doquotes=False)
    now = time()

    return {
        "thread_id":   ID,     # string
        "post_id":     1,      # integer
        "author":      author, # string
        "body":        body,   # string
        "title":       title,  # string
        "tags":        tags,   # (possibly empty) list of strings
        "replies":     list(), # (possibly empty) list of reply objects
        "reply_count": 0,      # integer
        "edited":      False,  # boolean
        "lastmod":     now,    # floating point unix timestamp
        "created":     now     # floating point unix timestamp
    }


def reply(ID, author, body):

    body = formatting.parse(body)
    now = time()

    return {
        "post_id":  ID,     # integer
        "author":   author, # string
        "body":     body,   # string
        "edited":   False,  # boolean
        "lastmod":  now,    # floating point unix timestamp
        "created":  now     # floating point unix timestamp
    }
