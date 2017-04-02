from src.exceptions import BBJException, BBJParameterError, BBJUserError
from src import db, schema
from functools import wraps
from uuid import uuid1
import traceback
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
    it for inspection. Errors related to JSON decoding are
    caught as well and returned to the client as code 0.
    """
    @wraps(function)
    def wrapper(*args, **kwargs):
        response = None
        try:
            # read in the body from the request to a string...
            body = str(cherrypy.request.body.read(), "utf8")
            # is it empty? not all methods require an input
            if body:
                # if this fucks up, we throw code 0 instead of code 1
                body = json.loads(body)
                if isinstance(body, dict):
                    # lowercase all of its keys
                    body = {str(key).lower(): value for key, value
                              in body.items()}
                cherrypy.request.json = body

            else:
                cherrypy.request.json = None

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
                if not user:
                    raise BBJUserError("User %s is not registered" % username)

                if auth != user["auth_hash"]:
                    return json.dumps(schema.error(5,
                        "Invalid authorization key for user."))

            cherrypy.thread_data.user = user
            cherrypy.thread_data.anon = anon
            response = function(*args, **kwargs)

        except json.JSONDecodeError as e:
            response = schema.error(0, str(e))

        except BBJException as e:
            response = e.schema

        except Exception as e:
            error_id = uuid1().hex
            response = schema.error(1,
                "Internal server error: code {}. Tell ~desvox (the code too)"
                .format(error_id))
            with open("logs/exceptions/" + error_id, "a") as log:
                traceback.print_tb(e.__traceback__, file=log)
                log.write(repr(e))

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
    its endpoint (and isnt empty)
    """
    if not json:
        raise BBJParameterError(
            "JSON input is empty. This method requires the following "
            "arguments: {}".format(", ".join(args)))

    for arg in args:
        if arg not in json.keys():
            raise BBJParameterError(
                "Required parameter {} is absent from the request. "
                "This method requires the following arguments: {}"
                .format(arg, ", ".join(args)))


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
    def get_me(self, *args, **kwargs):
        """
        Requires no arguments. Returns your internal user object,
        including your authorization hash.
        """
        return schema.response(cherrypy.thread_data.user)

    @api_method
    @cherrypy.expose
    def user_get(self, *args, **kwargs):
        """
        Retreive an external user object for the given `user`.
        Can be a user_id or user_name.
        """
        args = cherrypy.request.json
        validate(args, ["user"])
        return schema.response(db.user_resolve(
            cherrypy.thread_data.db,
            args["user"],
            return_false=False,
            externalize=True))


    @api_method
    @cherrypy.expose
    def thread_index(self, *args, **kwargs):
        threads = db.thread_index(cherrypy.thread_data.db)
        usermap = create_usermap(cherrypy.thread_data.db, threads)
        return schema.response(threads, usermap)


    @api_method
    @cherrypy.expose
    def thread_create(self, *args, **kwargs):
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
    def thread_reply(self, *args, **kwargs):
        args = cherrypy.request.json
        validate(args, ["thread_id", "body"])
        return schema.response(db.thread_reply(
            cherrypy.thread_data.db,
            cherrypy.thread_data.user["user_id"],
            args["thread_id"], args["body"]))


    @api_method
    @cherrypy.expose
    def thread_load(self, *args, **kwargs):
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
    def user_register(self, *args, **kwargs):
        args = cherrypy.request.json
        validate(args, ["user_name", "auth_hash"])
        return schema.response(db.user_register(
            cherrypy.thread_data.db,
            args["user_name"],
            args["auth_hash"]))


    @api_method
    @cherrypy.expose
    def edit_query(self, *args, **kwargs):
        args = cherrypy.request.json
        validate(args, ["thread_id", "post_id"])
        return schema.response(message_edit_query(
            cherrypy.thread_data.db,
            cherrypy.thread_data.user["user_id"],
            args["thread_id"],
            args["post_id"]))


    @cherrypy.expose
    def test(self, *args, **kwargs):
        print(cherrypy.request.body.read())
        return "{\"wow\": \"good job!\"}"



def run():
    cherrypy.quickstart(API(), "/api")


if __name__ == "__main__":
    print("wew")
