"""
This module contains all of the interaction with the SQLite database. It
doesnt hold a connection itself, rather, a connection is passed in as
an argument to all the functions and is maintained by CherryPy's threading
system. This is clunky but fuck it, it works (for now at least).

(foreword: formatting is not currently implemented but its an important
  feature needed in the final version)

All post and thread data are stored in the database without formatting.
This is questionable, as it causes formatting to be reapplied with each
pull for the database. Im debating whether posts should be stored in all
4 formats, or if maybe a caching system should be used.

The database, nor ANY part of the server, DOES NOT HANDLE PASSWORD HASHING!
Clients are responsible for creation of hashes and passwords should never
be sent unhashed. User registration and update endpoints will not accept
hashes that != 64 characters in length, as a basic measure to enforce the
use of sha256.
"""

from src.exceptions import BBJParameterError, BBJUserError
from src.utils import ordered_keys, schema_values
from src import schema
from uuid import uuid1
from time import time
import pickle
import json
import os

anon = None

### THREADS ###

def thread_get(connection, thread_id, messages=True):
    """
    Fetch the thread_id from the database. Formatting is be handled
    elsewhere.

    MESSAGES, if False, will omit the inclusion of a thread's messages
    and only get its metadata, such as title, author, etc.
    """
    c = connection.cursor()
    thread = c.execute(
        "SELECT * FROM threads WHERE thread_id = ?",
        (thread_id,)).fetchone()

    if not thread:
        raise BBJParameterError("Thread does not exist.")
    thread = schema.thread(*thread)

    if messages:
        c.execute("""
        SELECT * FROM messages WHERE thread_id = ?
          ORDER BY post_id""", (thread_id,))
        # create a list where each post_id matches its list[index]
        thread["messages"] = [schema.message(*values) for values in c.fetchall()]

    return thread


def thread_index(connection):
    """
    Return a list with each thread, ordered by the date they
    were last modifed (which could be when it was submitted
    or its last reply)

    Please note that thred["messages"] is omitted.
    """
    c = connection.execute("""
        SELECT thread_id FROM threads
          ORDER BY last_mod DESC""")

    threads = [
        thread_get(connection, obj[0], messages=False)
            for obj in c.fetchall()
    ]
    return threads


def thread_set_pin(connection, thread_id, pin_bool):
    """
    Set the pinned status of thread_id to pin_bool.
    """
    # can never be too sure :^)
    pin_bool = bool(pin_bool)
    connection.execute("""
        UPDATE threads SET
        pinned = ?
        WHERE thread_id = ?
    """, (pin_bool, thread_id))
    connection.commit()
    return pin_bool


def thread_create(connection, author_id, body, title):
    """
    Create a new thread and return it.
    """
    validate([
        ("body",  body),
        ("title", title)
    ])

    now = time()
    thread_id = uuid1().hex
    scheme = schema.thread(
        thread_id, author_id, title,
        now, now, -1, False) # see below for why i set -1 instead of 0

    connection.execute("""
        INSERT INTO threads
        VALUES (?,?,?,?,?,?,?)
    """, schema_values("thread", scheme))
    connection.commit()
    # the thread is initially commited with reply_count -1 so that i can
    # just pass the message to the reply method, instead of duplicating
    # its code here. It then increments to 0.
    thread_reply(connection, author_id, thread_id, body, time_override=now)
    # fetch the new thread out of the database instead of reusing the returned
    # objects, just to be 100% sure what is returned is what was committed
    return thread_get(connection, thread_id)


def thread_reply(connection, author_id, thread_id, body, time_override=None):
    """
    Submit a new reply for thread_id. Return the new reply object.

    time_overide can be time() value to set as the new message time.
    This is to keep post_id 0 in exact parity with its parent thread.
    """
    validate([("body", body)])

    now = time_override or time()
    thread = thread_get(connection, thread_id, messages=False)
    count = thread["reply_count"] + 1
    scheme = schema.message(
        thread_id, count, author_id,
        now, False, body)

    connection.execute("""
        INSERT INTO messages
        VALUES (?,?,?,?,?,?)
    """, schema_values("message", scheme))

    connection.execute("""
        UPDATE threads SET
        reply_count = ?,
        last_mod = ?
        WHERE thread_id = ?
    """, (count, now, thread_id))

    connection.commit()
    return scheme


def message_edit_query(connection, author, thread_id, post_id):
    """
    Perform all the neccesary sanity checks required to edit a post
    and then return the requested message object without any changes.
    """
    user = user_resolve(connection, author)
    thread = thread_get(connection, thread_id)

    try: message = thread["messages"][post_id]
    except IndexError:
        raise BBJParameterError("post_id out of bounds for requested thread")

    if not user["is_admin"]:
        if not user["user_id"] == message["author"]:
            raise BBJUserError(
                "non-admin attempt to edit another user's message")

        elif (time() - message["created"]) > 86400:
            raise BBJUserError(
                "message is too old to edit (24hr limit)")

    return message


def message_edit_commit(connection, author_id, thread_id, post_id, new_body):
    """
    Attempt to commit new_body to the existing message. Touches base with
    message_edit_query first. Returns the newly updated message object.
    """
    validate([("body", new_body)])
    message = message_edit_query(connection, author_id, thread_id, post_id)
    message["body"] = new_body
    message["edited"] = True

    connection.execute("""
        UPDATE messages SET
        body = ?,
        edited = ?
        WHERE thread_id = ?
          AND post_id = ?
    """, (new_body, True, thread_id, post_id))

    connection.commit()
    return message


### USERS ####


def user_register(connection, user_name, auth_hash):
    """
    Registers a new user into the system. Ensures the user
    is not already registered, and that the hash and name
    meet the requirements of their respective sanity checks
    """
    validate([
        ("user_name", user_name),
        ("auth_hash", auth_hash)
    ])

    if user_resolve(connection, user_name):
        raise BBJUserError("Username already registered")

    scheme = schema.user_internal(
        uuid1().hex, user_name, auth_hash,
        "", "", 0, False, time())

    connection.execute("""
         INSERT INTO users
         VALUES (?,?,?,?,?,?,?,?)
    """, schema_values("user", scheme))

    connection.commit()
    return scheme


def user_resolve(connection, name_or_id, externalize=False, return_false=True):
    """
    Accepts a name or id and returns the full user object for it.

    EXTERNALIZE determines whether to strip the object of private data.

    RETURN_FALSE determines whether to raise an exception or just
    return bool False if the user doesn't exist
    """
    user = connection.execute("""
         SELECT * FROM users
         WHERE user_name = ?
            OR user_id = ? """,
        (name_or_id, name_or_id)).fetchone()

    if user:
        user = schema.user_internal(*user)
        if externalize:
            return user_externalize(user)
        return user

    if return_false:
        return False
    raise BBJParameterError(
        "Requested user element ({})"
        " is not registered".format(name_or_id))


def user_update(connection, user_object, parameters):
    """
    Accepts new parameters for a user object and then
    commits the changes to the database. Parameters
    that are not suitable for editing (like user_id
    and anything undefined) are ignored completely.
    """
    user_id = user_object["user_id"]
    for key in ("user_name", "auth_hash", "quip", "bio", "color"):
        value = parameters.get(key)
        # bool(0) == False hur hur hurrrrrr ::drools::
        if value == 0 or value:
            validate([(key, value)])
            user_object[key] = value

    values = ordered_keys(user_object,
        "user_name", "quip", "auth_hash",
        "bio", "color", "user_id")

    connection.execute("""
        UPDATE users SET
        user_name = ?, quip = ?,
        auth_hash = ?, bio = ?,
        color = ? WHERE user_id = ?
        """, values)

    connection.commit()
    return user_resolve(connection, user_id)


def user_externalize(user_object):
    """
    Cleanse private/internal data from a user object
    and make it suitable to serve.
    """
    # only secret value right now is the auth_hash,
    # but this may change in the future
    for key in ("auth_hash",):
        user_object.pop(key)
    return user_object


### SANITY CHECKS ###

def contains_nonspaces(string):
    return any([char in string for char in "\t\n\r\x0b\x0c"])


def validate(keys_and_values):
    """
    The line of defense against garbage user input.

    Recieves an iterable containing iterables, where [0]
    is a string representing the value type, and [1]
    is the value to compare against a set of rules for
    it's type. The function returns the boolean value
    True when everything is okay, or raises a BBJException
    to be handled by higher levels of the program if something
    is wrong (immediately stopping execution at the db level)
    """
    for key, value in keys_and_values:

        if key == "user_name":
            if not value:
                raise BBJUserError(
                    "Username may not be empty.")

            elif contains_nonspaces(value):
                raise BBJUserError(
                    "Username cannot contain whitespace characters besides spaces.")

            elif not value.strip():
                raise BBJUserError(
                    "Username must contain at least one non-space character")

            elif len(value) > 24:
                raise BBJUserError(
                    "Username is too long (max 24 chars)")

        elif key == "auth_hash":
            if not value:
                raise BBJParameterError(
                    "auth_hash may not be empty")

            elif len(value) != 64:
                raise BBJParameterError(
                    "Client error: invalid SHA-256 hash.")

        elif key == "quip":
            if contains_nonspaces(value):
                raise BBJUserError(
                    "Quip cannot contain whitespace characters besides spaces.")

            elif len(value) > 120:
                raise BBJUserError(
                    "Quip is too long (max 120 chars)")

        elif key == "bio":
            if len(value) > 4096:
                raise BBJUserError(
                    "Bio is too long (max 4096 chars)")

        elif key == "title":
            if not value:
                raise BBJUserError(
                    "Title cannot be empty")

            elif contains_nonspaces(value):
                raise BBJUserError(
                    "Titles cannot contain whitespace characters besides spaces.")

            elif not value.strip():
                raise BBJUserError(
                    "Title must contain at least one non-space character")

            elif len(value) > 120:
                raise BBJUserError(
                    "Title is too long (max 120 chars)")

        elif key == "body":
            if not value:
                raise BBJUserError(
                    "Post body cannot be empty")


        elif key == "color":
            if value in range(0, 7):
                continue
            raise BBJParameterError(
                "Color specification out of range (int 0-6)")

    return True
