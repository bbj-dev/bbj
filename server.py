from src.exceptions import BBJException, BBJParameterError
from src import db, schema, endpoints
from functools import wraps
import cherrypy
import sqlite3
import json

dbname = "data.sqlite"

with sqlite3.connect(dbname) as _c:
    if not db.user_resolve(_c, "anonymous"):
        db.user_register(_c, *db.anonymous)


# creates a database connection for each thread
def connect(_):
    cherrypy.thread_data.db = sqlite3.connect(dbname)
cherrypy.engine.subscribe('start_thread', connect)


def bbjapi(function):
    """
    A wrapper that handles encoding of objects and errors to a
    standard format for the API, resolves and authorizes users
    from header data, and prepares thread data to handle the
    request.

    In addition, all BBJException's will return their attached
    schema, and unhandled exceptions return a code 1 error schema.
    """
    @wraps(function)
    def wrapper(*args, **kwargs):
        headers = cherrypy.request.headers
        username = headers.get("User")
        auth = headers.get("Auth")
        anon = False

        if not username and not auth:
            user = db.user_resolve(cherrypy.thread_data.db, "anonymous")
            anon = True
        elif not username or not auth:
            return json.dumps(schema.error(5,
                "User or Auth was given without the other."))

        if not anon:
            user = db.user_resolve(cherrypy.thread_data.db, username)
            if not user:
                return json.dumps(schema.error(4,
                    "Username is not registered."))

            elif auth != user["auth_hash"]:
                return json.dumps(schema.error(5,
                    "Invalid authorization key for user."))

        cherrypy.thread_data.user = user
        cherrypy.thread_data.anon = anon

        try:
            value = function(*args, **kwargs)

        except BBJException as e:
            value = e.schema

        except Exception as e:
            value = schema.error(1, str(e))

        return json.dumps(value)
    return wrapper


def create_usermap(connection, obj):
    """
    Creates a mapping of all the user_ids that occur in OBJ to
    their full user objects (names, profile info, etc). Can
    be a thread_index or a messages object from one.
    """

    if isinstance(obj, dict):
        # this is a message object for a thread, unravel it
        obj = [value for key, value in obj.items()]

    return {
        user_id: db.user_resolve(
            connection,
            user_id,
            externalize=True,
            return_false=False)
        for user_id in {
                item["author"] for item in obj
        }
    }



def validate(json, args):
    """
    Ensure the json object contains all the keys needed to satisfy
    its endpoint.
    """
    for arg in args:
        if arg not in json.keys():
            raise BBJParameterError(
                "Required parameter %s is "
                "absent from the request." % arg)


APICONFIG = {
    "/": {
        "tools.response_headers.on": True,
        "tools.response_headers.headers": [
            ("Content-Type", "application/json")
        ],
    }
}

class API(object):
    @bbjapi
    @cherrypy.expose
    def thread_index(self):
        threads = db.thread_index(cherrypy.thread_data.db)
        usermap = create_usermap(cherrypy.thread_data.db, threads)
        return schema.response({
            "data": threads,
            "usermap": usermap
        })


    @bbjapi
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def thread_create(self):
        args = cherrypy.request.json
        validate(args, ["body", "title"])

        thread = db.thread_create(
            cherrypy.thread_data.db,
            cherrypy.thread_data.user["user_id"],
            args["body"], args["title"])

        usermap = {
            cherrypy.thread_data.user["user_id"]:
              cherrypy.thread_data.user
        }

        return schema.response({
            "data": thread,
            "usermap": usermap
        })


    @bbjapi
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def thread_reply(self):
        args = cherrypy.request.json
        validate(args, ["thread_id", "body"])
        return schema.response({
            "data": db.thread_reply(
                cherrypy.thread_data.db,
                cherrypy.thread_data.user["user_id"],
                args["thread_id"], args["body"])
        })


    @bbjapi
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def thread_load(self):
        args = cherrypy.request.json
        validate(args, ["thread_id"])

        thread = db.thread_get(
            cherrypy.thread_data.db,
            args["thread_id"])

        usermap = create_usermap(
            cherrypy.thread_data.db,
            thread["messages"])

        return schema.response({
            "data": thread,
            "usermap": usermap
        })


    @bbjapi
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def user_register(self):
        args = cherrypy.request.json
        validate(args, ["user_name", "auth_hash"])
        return schema.response({
            "data": db.user_register(
                cherrypy.thread_data.db,
                args["user_name"], args["auth_hash"])
        })


    @bbjapi
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def edit_query(self):
        args = cherrypy.request.json
        validate(args, ["thread_id", "post_id"])
        return schema.response({
            "data": message_edit_query(
                cherrypy.thread_data.db,
                cherrypy.thread_data.user["user_id"],
                args["thread_id"],
                args["post_id"])
        })



def run():
    cherrypy.quickstart(API(), "/api")


if __name__ == "__main__":
    print("wew")
