from src.exceptions import BBJException, BBJParameterError, BBJUserError
from jinja2 import Environment, FileSystemLoader, select_autoescape
from src import db, schema, formatting
from os.path import abspath
from hashlib import sha256
from functools import wraps
from uuid import uuid1
from sys import argv
import traceback
import cherrypy
import sqlite3
import json

dbname = "data.sqlite"
template_environment = Environment(loader=FileSystemLoader("templates/"), autoescape=select_autoescape())


# any values here may be overrided in the config.json. Any values not listed
# here will have no effect on the server.
default_config = {
    "admins": [],
    "port": 7099,
    "host": "127.0.0.1",
    "instance_name": "BBJ",
    "allow_anon": True,
    "debug": False
}

try:
    with open("config.json", "r") as _in:
        app_config = json.load(_in)
    # update the file with new keys if necessary
    for key, default_value in default_config.items():
        # The application will never store a config value
        # as the NoneType, so users may set an option as
        # null in their file to reset it to default
        if key not in app_config or app_config[key] == None:
            app_config[key] = default_value
# else just use the defaults
except FileNotFoundError:
    app_config = default_config
finally:
    with open("config.json", "w") as _out:
        json.dump(app_config, _out, indent=2)


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
        debug = app_config["debug"]
        try:
            connection = sqlite3.connect(dbname)
            # read in the body from the request to a string...
            if cherrypy.request.method == "POST":
                read_in = str(cherrypy.request.body.read(), "utf8")
                if not read_in:
                    # the body may be empty, not all methods require input
                    body = {}
                else:
                    body = json.loads(read_in)
                    if not isinstance(body, dict):
                        raise BBJParameterError("Non-JSONObject input")
                    # lowercase all of its top-level keys
                    body = {key.lower(): value for key, value in body.items()}
            else:
                body = {}

            username = cherrypy.request.headers.get("User")
            auth = cherrypy.request.headers.get("Auth")

            if (username and not auth) or (auth and not username):
                raise BBJParameterError(
                    "User or Auth was given without the other.")

            elif not username and not auth:
                user = db.anon

            else:
                user = db.user_resolve(connection, username)
                if not user:
                    raise BBJUserError("User %s is not registered" % username)

                elif auth.lower() != user["auth_hash"].lower():
                    raise BBJException(
                        5, "Invalid authorization key for user.")

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
            response = schema.error(
                1, "Internal server error: code {} {}".format(
                    error_id, repr(e)))
            with open("logs/exceptions/" + error_id, "a") as log:
                traceback.print_tb(e.__traceback__, file=log)
                log.write(repr(e))
            print("logged code 1 exception " + error_id)

        finally:
            connection.close()
            return json.dumps(response)

    return wrapper


# def html_method(function):
#     """
#     Wrapper function for HTML methods.
#     """
#     pass

def create_usermap(connection, obj, index=False):
    """
    Creates a mapping of all the user_ids that occur in OBJ to
    their full user objects (names, profile info, etc). Can
    be a thread_index or a messages object from one.
    """
    user_set = {item["author"] for item in obj}
    if index:
        [user_set.add(item["last_author"]) for item in obj]
    return {
        user_id: db.user_resolve(
            connection,
            user_id,
            externalize=True,
            return_false=False)
        for user_id in user_set
    }


def do_formatting(format_spec, messages):
    if not format_spec:
        return None

    elif format_spec == "sequential":
        method = formatting.sequential_expressions

    else:
        raise BBJParameterError("invalid formatter specification")

    formatting.apply_formatting(messages, method)
    return True


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


def no_anon_hook(user, message=None, user_error=True):
    if user is db.anon:
        exception = BBJUserError if user_error else BBJParameterError
        if message:
            raise exception(message)
        elif not app_config["allow_anon"]:
            raise exception(
                "Anonymous participation has been disabled on this instance.")


class API(object):
    """
    This object contains all the API endpoints for bbj. The html serving
    part of the server is not written yet, so this is currently the only
    module being served.

    The docstrings below are specifically formatted for the mkdocs static
    site generator. The ugly `doctype` and `arglist` attributes assigned
    after each method definition are for use in the `mkendpoints.py` script.
    """

    @api_method
    def instance_info(self, args, database, user, **kwargs):
        """
        Return configuration info for this running instance of the BBJ server.
        """
        return {
            "allow_anon": app_config["allow_anon"],
            "instance_name": app_config["instance_name"],
            "admins": app_config["admins"]
        }

    @api_method
    def user_register(self, args, database, user, **kwargs):
        """
        Register a new user into the system and return the new user object
        on success. The returned object includes the same `user_name` and
        `auth_hash` that you supply, in addition to all the default user
        parameters. Returns code 4 errors for any failures.
        """
        validate(args, ["user_name", "auth_hash"])
        return db.user_register(
            database, args["user_name"], args["auth_hash"])
    user_register.doctype = "Users"
    user_register.arglist = (
        ("user_name", "string: the desired display name"),
        ("auth_hash", "string: a sha256 hash of a password")
    )

    @api_method
    def user_update(self, args, database, user, **kwargs):
        """
        Receives new parameters and assigns them to the user object.
        This method requires that you send a valid User/Auth header
        pair with your request, and the changes are made to that
        account.

        Take care to keep your client's User/Auth header pair up to date
        after using this method.

        The newly updated user object is returned on success,
        including the `auth_hash`.
        """
        no_anon_hook(user, "Anons cannot modify their account.")
        validate(args, [])  # just make sure its not empty
        return db.user_update(database, user, args)
    user_update.doctype = "Users"
    user_update.arglist = (
        ("Any of the following may be submitted", ""),
        ("user_name", "string: a desired display name"),
        ("auth_hash", "string: sha256 hash for a new password"),
        ("quip", "string: a short string that can be used as a signature"),
        ("bio", "string: a user biography for their profile"),
        ("color", "integer: 0-6, a display color for the user")
    )

    @api_method
    def get_me(self, args, database, user, **kwargs):
        """
        Requires no arguments. Returns your internal user object,
        including your `auth_hash`.
        """
        return user
    get_me.doctype = "Users"
    get_me.arglist = (("", ""),)

    @api_method
    def user_map(self, args, database, user, **kwargs):
        """
        Returns an array with all registered user_ids, with the usermap
        object populated by their full objects. This method is _NEVER_
        neccesary when using other endpoints, as the usermap returned
        on those requests already contains all the information you will
        need. This endpoint is useful for statistic purposes only.
        """
        users = {
            user[0] for user in database.execute("SELECT user_id FROM users")
        }
        cherrypy.thread_data.usermap = {
            user: db.user_resolve(
                database,
                user,
                externalize=True,
                return_false=False)
            for user in users
        }
        return list(users)
    user_map.doctype = "Tools"
    user_map.arglist = (("", ""),)

    @api_method
    def user_get(self, args, database, user, **kwargs):
        """
        Returns a user object for the given target.
        """
        validate(args, ["target_user"])
        return db.user_resolve(
            database, args["target_user"], return_false=False, externalize=True)
    user_get.doctype = "Users"
    user_get.arglist = (
        ("target_user", "string: either a user_name or a user_id"),
    )

    @api_method
    def user_is_registered(self, args, database, user, **kwargs):
        """
        Returns boolean `true` or `false` of whether the given target is
        registered on the server.
        """
        validate(args, ["target_user"])
        return bool(db.user_resolve(database, args["target_user"]))
    user_is_registered.doctype = "Users"
    user_is_registered.arglist = (
        ("target_user", "string: either a user_name or a user_id"),
    )

    @api_method
    def check_auth(self, args, database, user, **kwargs):
        """
        Returns boolean `true` or `false` of whether the hash given
        is correct for the given user.
        """
        validate(args, ["target_user", "target_hash"])
        user = db.user_resolve(
            database, args["target_user"], return_false=False)
        return args["target_hash"].lower() == user["auth_hash"].lower()
    check_auth.doctype = "Authorization"
    check_auth.arglist = (
        ("target_user", "string: either a user_name or a user_id"),
        ("target_hash", "string: sha256 hash for the password to check")
    )

    @api_method
    def thread_index(self, args, database, user, **kwargs):
        """
        Return an array with all the server's threads. They are already sorted for
        you; most recently modified threads are at the beginning of the array.
        Unless you supply `include_op`, these threads have no `messages` parameter.
        If you do, the `messages` parameter is an array with a single message object
        for the original post.
        """
        threads = db.thread_index(database, include_op=args.get("include_op"))
        cherrypy.thread_data.usermap = create_usermap(database, threads, True)
        return threads
    thread_index.doctype = "Threads & Messages"
    thread_index.arglist = (
        ("OPTIONAL: include_op", "boolean: Include a `messages` object containing the original post"),
    )

    @api_method
    def message_feed(self, args, database, user, **kwargs):
        """
        Returns a special object representing all activity on the board since `time`.

        ```javascript
        {
            "threads": {
                "thread_id": {
                    // ...thread object
                },
                // ...more thread_id/object pairs
            },
            "messages": [
                ...standard message object array sorted by date
            ]
        }
        ```

        The message objects in `messages` are the same objects returned
        in threads normally. They each have a thread_id parameter, and
        you can access metadata for these threads by the `threads` object
        which is also provided.

        The `messages` array is already sorted by submission time, newest
        first. The order in the threads object is undefined and you should
        instead use their `last_mod` attribute if you intend to list them
        out visually.
        """
        # TODO: Update with new formatting documentation for arg `format`
        validate(args, ["time"])
        feed = db.message_feed(database, args["time"])

        _map = create_usermap(database, feed["messages"])
        _map.update(create_usermap(database, feed["threads"].values(), True))
        cherrypy.thread_data.usermap.update(_map)

        do_formatting(args.get("format"), feed["messages"])
        return feed
    message_feed.doctype = "Threads & Messages"
    message_feed.arglist = (
        ("time", "int/float: epoch/unix time of the earliest point of interest"),
        ("OPTIONAL: format", "string: the specifier for the desired formatting engine")
    )

    @api_method
    def thread_create(self, args, database, user, **kwargs):
        """
        Creates a new thread and returns it. Requires the non-empty
        string arguments `body` and `title`.

        If the argument `send_raw` is specified and has a non-nil
        value, the OP message will never recieve special formatting.
        """
        no_anon_hook(user)
        validate(args, ["body", "title"])
        thread = db.thread_create(
            database, user["user_id"], args["body"],
            args["title"], args.get("send_raw"))
        cherrypy.thread_data.usermap = \
            create_usermap(database, thread["messages"])
        return thread
    thread_create.doctype = "Threads & Messages"
    thread_create.arglist = (
        ("body", "string: The body of the first message"),
        ("title", "string: The title name for this thread"),
        ("OPTIONAL: send_raw", "boolean: formatting mode for the first message.")
    )

    @api_method
    def thread_reply(self, args, database, user, **kwargs):
        """
        Creates a new reply for the given thread and returns it.
        Requires the string arguments `thread_id` and `body`

        If the argument `send_raw` is specified and has a non-nil
        value, the message will never recieve special formatting.
        """
        no_anon_hook(user)
        validate(args, ["thread_id", "body"])
        return db.thread_reply(
            database, user["user_id"], args["thread_id"],
            args["body"], args.get("send_raw"))
    thread_reply.doctype = "Threads & Messages"
    thread_reply.arglist = (
        ("thread_id", "string: the id for the thread this message should post to."),
        ("body", "string: the message's body of text."),
        ("OPTIONAL: send_raw", "boolean: formatting mode for the posted message.")
    )

    @api_method
    def thread_load(self, args, database, user, **kwargs):
        """
        Returns the thread object with all of its messages loaded.
        Requires the argument `thread_id`. `format` may also be
        specified as a formatter to run the messages through.
        Currently only "sequential" is supported.

        You may also supply the parameter `op_only`. When it's value
        is non-nil, the messages array will only include post_id 0 (the first)
        """
        validate(args, ["thread_id"])
        thread = db.thread_get(
            database, args["thread_id"], op_only=args.get("op_only"))
        cherrypy.thread_data.usermap = \
            create_usermap(database, thread["messages"])
        do_formatting(args.get("format"), thread["messages"])
        return thread
    thread_load.doctype = "Threads & Messages"
    thread_load.arglist = (
        ("thread_id", "string: the thread to load."),
        ("OPTIONAL: op_only", "boolean: include only the original message in `messages`"),
        # XXX formal formatting documentation is desperately needed
        ("OPTIONAL: format", "string: the formatting type of the returned messages.")
    )

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

        Optionally you may also include the argument `send_raw` to
        set the message's formatting flag. However, if this is the
        only change you would like to make, you should use the
        endpoint `set_post_raw` instead.

        Returns the new message object.
        """
        no_anon_hook(user, "Anons cannot edit messages.")
        validate(args, ["body", "thread_id", "post_id"])
        return db.message_edit_commit(
            database, user["user_id"], args["thread_id"],
            args["post_id"], args["body"], args.get("send_raw"))
    edit_post.doctype = "Threads & Messages"
    edit_post.arglist = (
        ("thread_id", "string: the thread the message was posted in."),
        ("post_id", "integer: the target post_id to edit."),
        ("body", "string: the new message body."),
        ("OPTIONAL: send_raw", "boolean: set the formatting mode for the target message.")
    )

    @api_method
    def delete_post(self, args, database, user, **kwargs):
        """
        Requires the arguments `thread_id` and `post_id`.

        Delete a message from a thread. The same rules apply
        here as `edit_post` and `edit_query`: the logged in user
        must either be the one who posted the message within 24hrs,
        or have admin rights. The same error descriptions and code
        are returned on falilure. Boolean true is returned on
        success.

        If the post_id is 0, the whole thread is deleted.
        """
        no_anon_hook(user, "Anons cannot delete messages.")
        validate(args, ["thread_id", "post_id"])
        return db.message_delete(
            database, user["user_id"], args["thread_id"], args["post_id"])
    delete_post.doctype = "Threads & Messages"
    delete_post.arglist = (
        ("thread_id", "string: the id of the thread this message was posted in."),
        ("post_id", "integer: the id of the target message.")
    )

    @api_method
    def set_post_raw(self, args, database, user, **kwargs):
        """
        Requires the boolean argument of `value`, string argument
        `thread_id`, and integer argument `post_id`. `value`, when false,
        means that the message will be passed through message formatters
        before being sent to clients. When `value` is true, this means
        it will never go through formatters, all of its whitespace is
        sent to clients verbatim and expressions are not processed.

        The same rules for editing messages (see `edit_query`) apply here
        and the same error objects are returned for violations.

        You may optionally set this value as well when using `edit_post`,
        but if this is the only change you want to make to the message,
        using this endpoint instead is preferable.
        """
        no_anon_hook(user, "Anons cannot edit messages.")
        validate(args, ["value", "thread_id", "post_id"])
        return db.message_edit_commit(
            database, user["user_id"],
            args["thread_id"], args["post_id"],
            None, args["value"], None)
    set_post_raw.doctype = "Threads & Messages"
    set_post_raw.arglist = (
        ("thread_id", "string: the id of the thread the message was posted in."),
        ("post_id", "integer: the id of the target message."),
        ("value", "boolean: the new `send_raw` value to apply to the message.")
    )

    @api_method
    def is_admin(self, args, database, user, **kwargs):
        """
        Requires the argument `target_user`. Returns a boolean
        of whether that user is an admin.
        """
        validate(args, ["target_user"])
        user = db.user_resolve(
            database, args["target_user"], return_false=False)
        return user["is_admin"]
    is_admin.doctype = "Users"
    is_admin.arglist = (
        ("target_user", "string: user_id or user_name to check against."),
    )

    @api_method
    def edit_query(self, args, database, user, **kwargs):
        """
        Queries the database to ensure the user can edit a given
        message. Requires the arguments `thread_id` and `post_id`
        (does not require a new body)

        Returns the original message object without any formatting
        on success. Returns a descriptive code 4 otherwise.
        """
        no_anon_hook(user, "Anons cannot edit messages.")
        validate(args, ["thread_id", "post_id"])
        return db.message_edit_query(
            database, user["user_id"], args["thread_id"], args["post_id"])
    edit_query.doctype = "Threads & Messages"
    edit_query.arglist = (
        ("thread_id", "string: the id of the thread the message was posted in."),
        ("post_id", "integer: the id of the target message.")
    )

    @api_method
    def format_message(self, args, database, user, **kwargs):
        """
        Requires the arguments `body` and `format`. Applies
        `format` to `body` and returns the new object. See
        `thread_load` for supported specifications for `format`.
        """
        validate(args, ["format", "body"])
        message = [{"body": args["body"]}]
        do_formatting(args["format"], message)
        return message[0]["body"]
    format_message.doctype = "Tools"
    format_message.arglist = (
        ("body", "string: the message body to apply formatting to."),
        # XXX: remember to update this with new formatting docs
        ("format", "string: the specifier for the desired formatting engine")
    )

    @api_method
    def thread_set_pin(self, args, database, user, **kwargs):
        """
        Requires the arguments `thread_id` and `value`. `value`
        must be a boolean of what the pinned status should be.
        This method requires that the caller is logged in and
        has admin status on their account.

        Returns the same boolean you supply as `value`
        """
        validate(args, ["thread_id", "value"])
        if not user["is_admin"]:
            raise BBJUserError("Only admins can set thread pins")
        return db.thread_set_pin(database, args["thread_id"], args["value"])
    thread_set_pin.doctype = "Threads & Messages"
    thread_set_pin.arglist = (
        ("thread_id", "string: the id of the thread to modify."),
        ("value", "boolean: `true` to pin thread, `false` otherwise.")
    )

    @api_method
    def db_validate(self, args, database, user, **kwargs):
        """
        See also [the Input Validation page](validation.md).

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
    db_validate.doctype = "Tools"
    db_validate.arglist = (
        ("key", "string: the identifier for the ruleset to check."),
        ("value", "VARIES: the object for which `key` will check for."),
        ("OPTIONAL: error", "boolean: when `true`, will return an API error "
         "response instead of a special object.")
    )

testing = None

class HTML(object):
    """
    This object contains all of the endpoints for the HTML application.
    This is not a full javascript fronted developed with a framework like React.
    This fits in line with the general "theme" of the tilde servers
    this application was originally designed for. If you want a more
    modern implementation, a fully javascript-based client can be developed.
    But the server will not have one built in.
    """

    @cherrypy.expose
    def login(self, username=None, password=None):
        database = sqlite3.connect(dbname)
        cookie = cherrypy.request.cookie
        if username and password:
            user = db.user_resolve(database, username)
            auth_hash = sha256(bytes(password, "utf8")).hexdigest()
            if not user:
                return "User not registered"
            elif auth_hash.lower() != user["auth_hash"].lower():
                return "Authorization info incorrect."
            cherrypy.response.cookie["username"] = username 
            cherrypy.response.cookie["username"]["max-age"] = 34560000
            cherrypy.response.cookie["auth_hash"] = auth_hash
            cherrypy.response.cookie["auth_hash"]["max-age"] = 34560000
            raise cherrypy.HTTPRedirect("/index")
        
        if "username" in cookie and "auth_hash" in cookie:
            user = db.user_resolve(database, cookie["username"].value)
            if cookie["auth_hash"].value.lower() == user["auth_hash"]:
                authorized_user = user
            else:
                authorized_user = None
        else:
            authorized_user = None


        template = template_environment.get_template("login.html")
        variables = {
            "authorized_user": authorized_user
        }
        return template.render(variables)
    
    @cherrypy.expose
    def logout(self):
        cookie_in = cherrypy.request.cookie
        if "username" in cookie_in and "auth_hash" in cookie_in:
            cherrypy.response.cookie["username"] = ""
            cherrypy.response.cookie["username"]["expires"] = 0
            cherrypy.response.cookie["auth_hash"] = ""
            cherrypy.response.cookie["auth_hash"]["expires"] = 0
        raise cherrypy.HTTPRedirect("/index")


    @cherrypy.expose
    def setBookmark(self, bookmarkId=None, delBookmark=None):
        if "bookmarks" in cherrypy.request.cookie:
            bookmarks = json.loads(cherrypy.request.cookie["bookmarks"].value)
        else:
            bookmarks = []

        database = sqlite3.connect(dbname)
        threads = db.thread_index(database)
        
        if bookmarkId:
            if bookmarkId in [thread["thread_id"] for thread in threads]:
                bookmarks.append(bookmarkId)
        elif delBookmark:
            if delBookmark in bookmarks:
                bookmarks.remove(delBookmark)
        
        cherrypy.response.cookie["bookmarks"] = json.dumps(bookmarks)
        cherrypy.response.cookie["bookmarks"]["max-age"] = 34560000
        raise cherrypy.HTTPRedirect("/index")


    @cherrypy.expose
    def index(self, bookmarkId=None, delBookmark=None):
        database = sqlite3.connect(dbname)
        cookie = cherrypy.request.cookie
        include_op = "include_op" in cookie and cookie["include_op"]
        threads = db.thread_index(database, include_op=include_op)
        usermap = create_usermap(database, threads, True)

        if "username" in cookie and "auth_hash" in cookie:
            user = db.user_resolve(database, cookie["username"].value)
            if cookie["auth_hash"].value.lower() == user["auth_hash"]:
                authorized_user = user
            else:
                authorized_user = None
        else:
            authorized_user = None

        pinned_threads = [thread for thread in threads if thread["pinned"]]

        if "bookmarks" in cookie:
            user_bookmarks = json.loads(cookie["bookmarks"].value)
            bookmarked_threads = [thread for thread in threads if thread["thread_id"] in user_bookmarks]
            threads = [
                thread for thread in threads 
                if not thread["pinned"] 
                and not thread["thread_id"] in user_bookmarks
            ]
        else:
            bookmarked_threads = []
            threads = [
                thread for thread in threads 
                if not thread["pinned"]
            ]
        
        template = template_environment.get_template("threadIndex.html")
        variables = {
            "pinned_threads": pinned_threads,
            "bookmarked_threads": bookmarked_threads,
            "threads": threads,
            "include_op": include_op,
            "usermap": usermap,
            "authorized_user": authorized_user
        }
        return template.render(variables)


    @cherrypy.expose
    def thread(self, id=None):
        if not id:
            return "Please supply a Thread ID"
        database = sqlite3.connect(dbname)
        cookie = cherrypy.request.cookie
        thread = db.thread_get(database, id)
        usermap = create_usermap(database, thread["messages"])

        if "username" in cookie and "auth_hash" in cookie:
            user = db.user_resolve(database, cookie["username"].value)
            if cookie["auth_hash"].value.lower() == user["auth_hash"]:
                authorized_user = user
            else:
                authorized_user = None
        else:
            authorized_user = None

        template = template_environment.get_template("threadLoad.html")
        variables = {
            "thread": thread,
            "usermap": usermap,
            "authorized_user": authorized_user
        }
        return template.render(variables)
    

    @cherrypy.expose
    def threadSubmit(self, title=None, postContent=None):
        database = sqlite3.connect(dbname)
        cookie = cherrypy.request.cookie
        if "username" in cookie and "auth_hash" in cookie:
            user = db.user_resolve(database, cookie["username"].value)
            if cookie["auth_hash"].value.lower() == user["auth_hash"]:
                if title and postContent and title.strip() and postContent.strip():
                    thread = db.thread_create(database, user["user_id"], postContent, title)
                    raise cherrypy.HTTPRedirect("/thread?id=" + thread["thread_id"])
                else: 
                    return "Post or Title are empty"
        else:
            return "Not logged in."

                
    
    @cherrypy.expose
    def threadReply(self, postContent=None, threadId=None):
        if not threadId:
            return "No thread ID provided."
        elif not postContent:
            return "Reply content is empty."
        database = sqlite3.connect(dbname)
        cookie = cherrypy.request.cookie
        if "username" in cookie and "auth_hash" in cookie:
            user = db.user_resolve(database, cookie["username"].value)
            if cookie["auth_hash"].value.lower() != user["auth_hash"]:
                return "Authorization info not correct."
            if postContent.strip():
                db.thread_reply(database, user["user_id"], threadId, postContent)
            else:
                return "Post reply is empty."
            raise cherrypy.HTTPRedirect("/thread?id=" + threadId)
        return "User not logged in"



def api_http_error(status, message, traceback, version):
    return json.dumps(schema.error(
        2, "HTTP error {}: {}".format(status, message)))


API_CONFIG = {
    "/": {
        "error_page.default": api_http_error
    }
}

WEB_CONFIG = {
    "/css": {
        "tools.staticdir.on": True,
        "tools.staticdir.dir": abspath("css")
    },
    "/js": {
        "tools.staticdir.on": True,
        "tools.staticdir.dir": abspath("js")
    }
}


def run():
    _c = sqlite3.connect(dbname)
    try:
        db.set_admins(_c, app_config["admins"])
        # user anonymity is achieved in the laziest possible way: a literal user
        # named anonymous. may god have mercy on my soul.
        db.anon = db.user_resolve(_c, "anonymous")
        if not db.anon:
            db.anon = db.user_register(
                _c, "anonymous",  # this is the hash for "anon"
                "5430eeed859cad61d925097ec4f53246"
                "1ccf1ab6b9802b09a313be1478a4d614")
    finally:
        _c.close()

    cherrypy.tree.mount(API(), '/api', API_CONFIG)
    cherrypy.tree.mount(HTML(), '/', WEB_CONFIG)
    cherrypy.engine.start()
    cherrypy.engine.block()
    # cherrypy.quickstart(API(), "/api", API_CONFIG)


def get_arg(key, default, get_value=True):
    try:
        spec = argv.index("--" + key)
        value = argv[spec + 1] if get_value else True
    except ValueError:  # --key not specified
        value = default
    except IndexError:  # flag given but no value
        exit("invalid format for --" + key)
    return value


if __name__ == "__main__":
    port = get_arg("port", app_config["port"])
    host = get_arg("host", app_config["host"])
    debug = get_arg("debug", app_config["debug"], False)
    cherrypy.config.update({
        "server.socket_port": int(port),
        "server.socket_host": host
    })
    run()
