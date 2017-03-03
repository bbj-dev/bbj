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
            "description": description,
            "code": code
        }
    })
    return result


def user_internal(ID, auth_hash, name, quip, bio, admin):
    return {
        "user_id":   ID,
        "quip":      quip,
        "name":      name,
        "bio":       bio,
        "admin":     admin,
        "auth_hash": auth_hash
    }


def user_external(ID, name, quip, bio, admin):
    return {
        "user_id":   ID,
        "quip":      quip,
        "name":      name,
        "bio":       bio,
        "admin":     admin
    }


def thread(ID, author, body, title, tags):
    body = formatting.parse(body, doquotes=False)
    now = time()
    return {
        "thread_id":   ID,
        "post_id":     1,
        "author":      author,
        "body":        body,
        "title":       title,
        "tags":        tags,
        "replies":     list(),
        "reply_count": 0,
        "lastmod":     now,
        "edited":      False,
        "created":     now
    }


def reply(ID, author, body):
    body = formatting.parse(body)
    now = time()
    return {
        "post_id":  ID,
        "author":   author,
        "body":     body,
        "lastmod":  now,
        "edited":   False,
        "created":  now
    }