from time import time

def base():
    return {
        "usermap": {},
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


def user_internal(ID, auth_hash, name, avatar, bio, admin):
    return {
        "user_id":   ID,
        "avatar":    avatar,
        "name":      name,
        "bio":       bio,
        "admin":     admin,
        "auth_hash": auth_hash
    }


def user_external(ID, name, avatar, bio, admin):
    return {
        "user_id":   ID,
        "avatar":    avatar,
        "name":      name,
        "bio":       bio,
        "admin":     admin
    }


def thread(ID, author, body, title, tags):
    now = time()
    return {
        "thread_id":   ID,
        "author":      author,
        "body":        body,
        "entities":    list(),
        "title":       title,
        "tags":        tags,
        "replies":     list(),
        "reply_count": 0,
        "lastmod":     now,
        "edited":      False,
        "created":     now
    }


def reply(ID, author, body):
    now = time()
    return {
        "post_id":  ID,
        "author":   author,
        "body":     body,
        "entities": list(),
        "lastmod":  now,
        "edited":   False,
        "created":  now
    }
