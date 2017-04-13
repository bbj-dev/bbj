from src.exceptions import BBJException, BBJParameterError, BBJUserError
from src import db, schema, formatting
from functools import wraps
from uuid import uuid1
from sys import argv
import traceback
import cherrypy
import sqlite3
import json

dbname = "data.sqlite"

def api_method(function):
    """
    A wrapper that handles encoding of objects and errors to a
    standard format for the API, resolves and authorizes users
    from header data, and prepares the arguments for each method.

    In the body of each api method and all the functions
    they utilize, BBJExceptions are caught and their attached
    schema is dispatched to the client. All other unhandled
    exceptions will throw a code 1 back at the client and log
    it for inspection. Errors related to JSON decoding are
    caught as well and returned to the client as code 0.
    """
    function.exposed = True
    @wraps(function)
    def wrapper(self, *args, **kwargs):
        response = None
        try:
            connection = sqlite3.connect(dbname)
            # read in the body from the request to a string...
            if cherrypy.request.method == "POST":
                body = str(cherrypy.request.body.read(), "utf8")
            else:
                body = ""
            # the body may be empty, not all methods require input
            if body:
                body = json.loads(body)
                if isinstance(body, dict):
                    # lowercase all of its top-level keys
                    body = {key.lower(): value for key, value in body.items()}

            username = cherrypy.request.headers.get("User")
            auth = cherrypy.request.headers.get("Auth")

            if (username and not auth) or (auth and not username):
                raise BBJParameterError("User or Auth was given without the other.")

            elif not username and not auth:
                user = db.anon

            else:
                user = db.user_resolve(connection, username)
                if not user:
                    raise BBJUserError("User %s is not registered" % username)

                elif auth != user["auth_hash"]:
                    raise BBJException(5, "Invalid authorization key for user.")

            # api_methods may choose to bind a usermap into the thread_data
            # which will send it off with the response
            cherrypy.thread_data.usermap = {}
            value = function(self, body, connection, user)
            response = schema.response(value, cherrypy.thread_data.usermap)

        except BBJException as e:
            response = e.schema

        except json.JSONDecodeError as e:
            response = schema.error(0, str(e))

        except Exception as e:
            error_id = uuid1().hex
            response = schema.error(1,
                "Internal server error: code {} {}"
                    .format(error_id, repr(e)))
            with open("logs/exceptions/" + error_id, "a") as log:
                traceback.print_tb(e.__traceback__, file=log)
                log.write(repr(e))
            print("logged code 1 exception " + error_id)

        finally:
            connection.close()
            return json.dumps(response)

    return wrapper


def create_usermap(connection, obj):
    """
    Creates a mapping of all the user_ids that occur in OBJ to
    their full user objects (names, profile info, etc). Can
    be a thread_index or a messages object from one.
    """

    return {
        user_id: db.user_resolve(
            connection,
            user_id,
            externalize=True,
            return_false=False)
        for user_id in {item["author"] for item in obj}
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


class API(object):
    """
    This object contains all the API endpoints for bbj.
    The html serving part of the server is not written
    yet, so this is currently the only module being
    served.
    """
    @api_method
    def user_register(self, args, database, user, **kwargs):
        """
        Register a new user into the system and return the new object.
        Requires the string arguments `user_name` and `auth_hash`.
        Do not send User/Auth headers with this method.
        """
        validate(args, ["user_name", "auth_hash"])
        return db.user_register(
            database, args["user_name"], args["auth_hash"])


    @api_method
    def user_update(self, args, database, user, **kwargs):
        """
        Receives new parameters and assigns them to the user_object
        in the database. The following new parameters can be supplied:
        `user_name`, `auth_hash`, `quip`, `bio`, and `color`. Any number
        of them may be supplied.

        The newly updated user object is returned on success.
        """
        if user == db.anon:
            raise BBJParameterError("Anons cannot modify their account.")
        validate(args, []) # just make sure its not empty
        return db.user_update(database, user, args)


    @api_method
    def get_me(self, args, database, user, **kwargs):
        """
        Requires no arguments. Returns your internal user object,
        including your authorization hash.
        """
        return user


    @api_method
    def user_get(self, args, database, user, **kwargs):
        """
        Retreive an external user object for the given `user`.
        Can be a user_id or user_name.
        """
        validate(args, ["user"])
        return db.user_resolve(
            database, args["user"], return_false=False, externalize=True)


    @api_method
    def user_is_registered(self, args, database, user, **kwargs):
        """
        Takes the argument `target_user` and returns true or false
        whether they are in the system or not.
        """
        validate(args, ["target_user"])
        return bool(db.user_resolve(database, args["target_user"]))


    @api_method
    def check_auth(self, args, database, user, **kwargs):
        """
        Takes the arguments `target_user` and `target_hash`, and
        returns boolean true or false whether the hash is valid.
        """
        validate(args, ["target_user", "target_hash"])
        user = db.user_resolve(database, args["target_user"], return_false=False)
        return args["target_hash"] == user["auth_hash"]


    @api_method
    def thread_index(self, args, database, user, **kwargs):
        """
        Return an array with all the threads, ordered by most recent activity.
        Requires no arguments.
        """
        threads = db.thread_index(database)
        cherrypy.thread_data.usermap = create_usermap(database, threads)
        return threads


    @api_method
    def thread_create(self, args, database, user, **kwargs):
        """
        Creates a new thread and returns it. Requires the non-empty
        string arguments `body` and `title`
        """
        validate(args, ["body", "title"])
        thread = db.thread_create(
            database, user["user_id"], args["body"], args["title"])
        cherrypy.thread_data.usermap = \
            create_usermap(database, thread["messages"])
        return thread


    @api_method
    def thread_reply(self, args, database, user, **kwargs):
        """
        Creates a new reply for the given thread and returns it.
        Requires the string arguments `thread_id` and `body`
        """
        validate(args, ["thread_id", "body"])
        return db.thread_reply(
            database, user["user_id"], args["thread_id"], args["body"])


    @api_method
    def thread_load(self, args, database, user, **kwargs):
        """
        Returns the thread object with all of its messages loaded.
        Requires the argument `thread_id`. `format` may also be
        specified as a formatter to run the messages through.
        Currently only "sequential" is supported.
        """
        validate(args, ["thread_id"])
        thread = db.thread_get(database, args["thread_id"])
        cherrypy.thread_data.usermap = \
            create_usermap(database, thread["messages"])
        if args.get("format") == "sequential":
            formatting.apply_formatting(thread["messages"],
                formatting.sequential_expressions)
        return thread


    @api_method
    def edit_post(self, args, database, user, **kwargs):
        """
        Replace a post with a new body. Requires the arguments
        `thread_id`, `post_id`, and `body`. This method verifies
        that the user can edit a post before commiting the change,
        otherwise an error object is returned whose description
        should be shown to the user.

        To perform sanity checks and retrieve the unformatted body
        of a post without actually attempting to replace it, use
        `edit_query` first.

        Returns the new message object.
        """
        if user == db.anon:
            raise BBJUserError("Anons cannot edit messages.")
        validate(args, ["body", "thread_id", "post_id"])
        return db.message_edit_commit(
            database, user["user_id"], args["thread_id"], args["post_id"], args["body"])


    @api_method
    def is_admin(self, args, database, user, **kwargs):
        """
        Requires the argument `target_user`. Returns a boolean
        of whether that user is an admin.
        """
        validate(args, ["target_user"])
        user = db.user_resolve(database, args["target_user"], return_false=False)
        return user["is_admin"]


    @api_method
    def edit_query(self, args, database, user, **kwargs):
        """
        Queries the database to ensure the user can edit a given
        message. Requires the arguments `thread_id` and `post_id`
        (does not require a new body)

        Returns the original message object without any formatting
        on success. Returns a descriptive code 4 otherwise.
        """
        if user == db.anon:
            raise BBJUserError("Anons cannot edit messages.")
        validate(args, ["thread_id", "post_id"])
        return db.message_edit_query(
            database, user["user_id"], args["thread_id"], args["post_id"])


    @api_method
    def format_message(self, args, database, user, **kwargs):
        """
        Requires the arguments `body` and `format`. Applies
        `format` to `body` and returns the new object. See
        `thread_load` for supported specifications for `format`.
        """
        validate(args, ["format", "body"])
        message = [{"body": args["body"]}]
        if args["format"] == "sequential":
            formatter = formatting.sequential_expressions
        else:
            raise BBJParameterError("invalid format directive.")
        formatting.apply_formatting(message, formatter)
        return message[0]["body"]


    @api_method
    def set_thread_pin(self, args, database, user, **kwargs):
        """
        Requires the arguments `thread_id` and `pinned`. Pinned
        must be a boolean of what the pinned status should be.
        This method requires that the caller is logged in and
        has admin status on their account.

        Returns the same boolean you supply as `pinned`
        """
        validate(args, ["thread_id", "pinned"])
        if not user["is_admin"]:
            raise BBJUserError("Only admins can set thread pins")
        return db.set_thread_pin(database, args["thread_id"], args["pinned"])


    @api_method
    def db_validate(self, args, database, user, **kwargs):
        """
        Requires the arguments `key` and `value`. Returns an object
        with information about the database sanity criteria for
        key. This can be used to validate user input in the client
        before trying to send it to the server.

        If the argument `error` is supplied with a non-nil value,
        the server will return a standard error object on failure
        instead of the special object described below.

        The returned object has two keys:

        {
          "bool": true/false,
          "description": null/"why this value is bad"
        }

        If bool == false, description is a string describing the
        problem. If bool == true, description is null and the
        provided value is safe to use.
        """
        validate(args, ["key", "value"])
        response = dict()
        try:
            db.validate([(args["key"], args["value"])])
            response["bool"] = True
            response["description"] = None
        except BBJException as e:
            if args.get("error"):
                raise
            response["bool"] = False
            response["description"] = e.description
        return response


    def test(self, **kwargs):
        print(cherrypy.request.body.read())
        return "{\"wow\": \"jolly good show!\"}"
    test.exposed = True


def api_http_error(status, message, traceback, version):
    return json.dumps(schema.error(2, "HTTP error {}: {}".format(status, message)))


CONFIG = {
    "/": {
        "error_page.default": api_http_error
    }
}


def run():
    # user anonymity is achieved in the laziest possible way: a literal user
    # named anonymous. may god have mercy on my soul.
    _c = sqlite3.connect(dbname)
    try:
        db.anon = db.user_resolve(_c, "anonymous")
        if not db.anon:
            db.anon = db.user_register(
                _c, "anonymous", # this is the hash for "anon"
                "5430eeed859cad61d925097ec4f53246"
                "1ccf1ab6b9802b09a313be1478a4d614")
    finally:
        _c.close()
    cherrypy.quickstart(API(), "/api", CONFIG)


if __name__ == "__main__":
    try:
        port_spec = argv.index("--port")
        port = argv[port_spec+1]
    except ValueError: # --port not specified
        port = 7099
    except IndexError: # flag given but no value
        exit("thats not how this works, silly! --port 7099")

    cherrypy.config.update({'server.socket_port': int(port)})
    run()
