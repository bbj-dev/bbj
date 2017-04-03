"""
This module provides functions that return API objects in
a clearly defined, consistent manner. Schmea representing
data types mirror the column order used by the sqlite
database. An sql object can be unpacked by using star
expansion as an argument, such as thread(*sql_thread_obj)

Each response has a base layout as follows:

{
  "error":   false, // boolean false or error object
  "data":    null,  // null or the requested data from endpoint.
  "usermap": {}     // a potentially empty object mapping user_ids to their objects
}

If "error" is true, it looks like this:

{
  "error": {
      "code": an integer from 0 to 5,
      "description": a string describing the error in detail.
  }
  "data": null   // ALWAYS null if error is not false
  "usermap": {}  // ALWAYS empty if error is not false
}

"data" can be anything. It could be a boolean, it could be a string,
object, anything. The return value for an endpoint is described clearly
in its documentation. However, no endpoint will EVER return null. If
"data" is null, then "error" is filled.

"usermap" is filled with objects whenever users are present in
"data". its keys are all the user_ids that occur in the "data"
object. Use this to get information about users, as follows:
usermap[id]["user_name"]
"""

def base():
    return {
        "error": False,
        "data": None,
        "usermap": dict()
    }


def response(data, usermap={}):
    result = base()
    result["data"] = data
    result["usermap"].update(usermap)
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


def user_internal(
        user_id,   # string (uuid1)
        user_name, # string
        auth_hash, # string (sha256 hash)
        quip,      # string (possibly empty)
        bio,       # string (possibly empty)
        color,     # int from 0 to 8
        is_admin,  # bool (supply as either False/True or 0/1)
        created):  # floating point unix timestamp (when user registered)

    if not quip:
        quip = ""

    if not bio:
        bio = ""

    if not color:
        color = 0

    return {
        "user_id":   user_id,
        "user_name": user_name,
        "auth_hash": auth_hash,
        "quip":      quip,
        "bio":       bio,
        "color":     color,
        "is_admin":  bool(is_admin),
        "created":   created
    }


def user_external(
        user_id,   # string (uuid1)
        user_name, # string
        quip,      # string (possibly empty)
        bio,       # string (possibly empty)
        color,     # int from 0 to 8
        admin,     # bool (can be supplied as False/True or 0/1)
        created):  # floating point unix timestamp (when user registered)

    if not quip:
        quip = ""

    if not bio:
        bio = ""

    if not color:
        color = 0

    return {
        "user_id":   user_id,
        "user_name": user_name,
        "quip":      quip,
        "bio":       bio,
        "color":     color,
        "is_admin":  admin,
        "created":   created
    }


def thread(
        thread_id,    # uuid string
        author,       # string (uuid1, user.user_id)
        title,        # string
        last_mod,     # floating point unix timestamp (of last post or post edit)
        created,      # floating point unix timestamp (when thread was made)
        reply_count): # integer (incremental, starting with 0)

    return {
        "thread_id":   thread_id,
        "author":      author,
        "title":       title,
        "last_mod":    last_mod,
        "created":     created,
        "reply_count": reply_count,
    }


def message(
        thread_id, # string (uuid1 of parent thread)
        post_id,   # integer (incrementing from 1)
        author,    # string (uuid1, user.user_id)
        created,   # floating point unix timestamp (when reply was posted)
        edited,    # bool
        body):     # string

    return {
        "thread_id": thread_id,
        "post_id":   post_id,
        "author":    author,
        "created":   created,
        "edited":    bool(edited),
        "body":      body
    }
