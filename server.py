from src.exceptions import BBJException, BBJParameterError
from src import db, schema, endpoints
from functools import wraps
import cherrypy
import sqlite3
import json


dbname = "data.sqlite"
with sqlite3.connect(dbname) as _c:
    db.anon_object = db.user_resolve(_c, "anonymous")
    if not db.anon_object:
        db.anon_object = db.user_register(_c, *db.anon_credentials)


# creates a database connection for each thread
def db_connect(_):
    cherrypy.thread_data.db = sqlite3.connect(dbname)
cherrypy.engine.subscribe('start_thread', db_connect)


def api_method(function):
    """
    A wrapper that handles encoding of objects and errors to a
    standard format for the API, resolves and authorizes users
    from header data, and prepares cherrypy.thread_data so other
    funtions can handle the request.

    In the body of each api method and all the functions
    they utilize, BBJExceptions are caught and their attached
    schema is dispatched to the client. All other unhandled
    exceptions will throw a code 1 back at the client and log
    it for inspection.
    """
    @wraps(function)
    def wrapper(*args, **kwargs):
        response = None
        try:
            username = cherrypy.request.headers.get("User")
            auth = cherrypy.request.headers.get("Auth")
            anon = False

            if not username and not auth:
                user = db.anon_object
                anon = True
            elif not username or not auth:
                return json.dumps(schema.error(5,
                    "User or Auth was given without the other."))

            if not anon:
                user = db.user_resolve(cherrypy.thread_data.db, username)
                if auth != user["auth_hash"]:
                    return json.dumps(schema.error(5,
                        "Invalid authorization key for user."))

            cherrypy.thread_data.user = user
            cherrypy.thread_data.anon = anon
            response = function(*args, **kwargs)

        except BBJException as e:
            response = e.schema

        except Exception as e:
            response = schema.error(1, repr(e))
            # TODO: use a logging file or module or something
            # repr() in this case is more verbose than just passing it in
            print(repr(e))

        finally:
            return json.dumps(response)

    return wrapper


def create_usermap(connection, obj):
    """
    Creates a mapping of all the user_ids that occur in OBJ to
    their full user objects (names, profile info, etc). Can
    be a thread_index or a messages object from one.
    """

    if isinstance(obj, dict):
        # this is a message object for a thread, ditch the keys
        obj = obj.values()

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
    @api_method
    @cherrypy.expose
    def get_me(self):
        """
        Requires no arguments. Returns your internal user object,
        including your authorization hash.
        """
        return schema.response(cherrypy.thread_data.user)

    @api_method
    @cherrypy.expose
    def user_get(self):
        """
        Retreive an external user object for the given `user`.
        Can be a user_id or user_name.
        """
        args = cherrypy.request.json
        validate(["user"])
        return schema.response(db.user_resolve(
            cherrypy.thread_data.db,
            args["user"],
            return_false=False,
            externalize=True))


    @api_method
    @cherrypy.expose
    def thread_index(self):
        threads = db.thread_index(cherrypy.thread_data.db)
        usermap = create_usermap(cherrypy.thread_data.db, threads)
        return schema.response(threads, usermap)


    @api_method
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

        return schema.response(thread, usermap)


    @api_method
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def thread_reply(self):
        args = cherrypy.request.json
        validate(args, ["thread_id", "body"])
        return schema.response(db.thread_reply(
            cherrypy.thread_data.db,
            cherrypy.thread_data.user["user_id"],
            args["thread_id"], args["body"]))


    @api_method
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

        return schema.response(thread, usermap)


    @api_method
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def user_register(self):
        args = cherrypy.request.json
        validate(args, ["user_name", "auth_hash"])
        return schema.response(db.user_register(
            cherrypy.thread_data.db,
            args["user_name"],
            args["auth_hash"]))


    @api_method
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def edit_query(self):
        args = cherrypy.request.json
        validate(args, ["thread_id", "post_id"])
        return schema.response(message_edit_query(
            cherrypy.thread_data.db,
            cherrypy.thread_data.user["user_id"],
            args["thread_id"],
            args["post_id"]))



def run():
    cherrypy.quickstart(API(), "/api")


if __name__ == "__main__":
    print("wew")
