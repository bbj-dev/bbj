from urllib.error import URLError
import urllib.request as url
from hashlib import sha256
from time import time
import json


class BBJ(object):
    # this module isnt exactly complete. The below description claims
    # `all of its endpoints are mapped to native methods` though this
    # is not yet true. The documentation for the API is not yet
    # complete, and neither is this client. Currently this module is
    # being adapted to fit the needs of the urwid client. As it evolves,
    # and the rest of the project evolves, this client will be completed
    # and well documented.
    """
    A python implementation to the BBJ api: all of its endpoints are
    mapped to native methods, it maps error responses to exceptions, and
    it includes helper functions for several common patterns.

    It should be noted that endpoints utilizing usermaps are returned as
    tuples, where [0] is the value and [1] is the usermap dictionary.
    Methods who do this will mention it in their documentation.
    You can call them like `threads, usermap = bbj.thread_index()`

    __init__ can take a host string and a port value (which can be
    either int or str). It defaults to "127.0.0.1" and 7099, expanding
    out to http://127.0.0.1:7099/.

    Standard library exceptions are used, but several new attributes are
    attached to them before raising: .code, .description, and .body.
    code and description map the same values returned by the api. body
    is the raw error object. Classes are mapped as follows:

      0, 1, 2: ChildProcessError
      3: ValueError
      4: UserWarning
      5: ConnectionRefusedError

    attributes can be accessed as follows:

    try:
        response = bbj.endpoint():
    except UserWarning as e:
        assert e.code == 4
        print(e.description)
        # want the raw error object? thats weird, but whatever.
        return e.body

    See the offical API error documentation for more details.
    """
    def __init__(self, host="127.0.0.1", port=7099, https=False):
        """
        Optionally takes port and host as kwargs. It will immediately
        try to resolve a connection to the server, if its down, it
        raises a URLError.

        Important attributes:
          .base is a string url for which all requests go to. It is
          constructed on instantiation and the standalone host/port
          are not stored.

          .user_{name,auth} can be None, or strings of the username
          and the authorization hash, respectively. When both values
          are present (ie both resolve to True in a boolean context),
          the request method sends this info with all its requests
          and the user is effectively "logged in".

          .send_auth, defaulting to True, determines whether to send
          authorization information when it is available (see above).
          If you set this to False, anonymous network usage is
          guaranteed.
        """
        self.base = "http{}://{}:{}/api/%s".format("s" if https else "", host, port)
        self.user_name = self.user_auth = None
        self.send_auth = True
        try:
            self.user = self("get_me")["data"]
            self.update_instance_info()
        except URLError:
            raise URLError("Cannot connect to %s (is the server down?)" % self.base[0:-2])


    def __call__(self, *args, **kwargs):
        """
        Calling the network object itself is exactly the same as calling
        it's .request() method.
        """
        return self.request(*args, **kwargs)


    def _hash(self, string):
        """
        Handy function to hash a password and return it.
        """
        return sha256(bytes(string, "utf8")).hexdigest()


    def request(self, endpoint, **params):
        """
        Takes the string endpoint, and a variable number of kwargs
        to pass into the request body. The parameters required will
        vary by endpoint, and if they are wrong, ValueError will be
        raised.

        However, one kwarg is magical here: no_auth. If you include
        this, its not sent with the request, it just disables the
        sending of auth info when it is available (for more info,
        read __init__'s documentation).

        You don't have to use this method yourself, the other methods
        must use this as a base though.

        See raise_exception() for details on how this function reacts
        to various failure conditions.
        """
        headers = {"Content-Type": "application/json"}
        if params.get("no_auth"):
            params.pop("no_auth")

        elif all([self.send_auth, self.user_name, self.user_auth]):
            headers.update({"User": self.user_name, "Auth": self.user_auth})

        data = bytes(json.dumps(params), "utf8")
        request = url.Request(
            self.base % endpoint,
            data=data,
            headers=headers)

        try:
            with url.urlopen(request) as _r:
                response = _r.read()
        except url.HTTPError as e:
            response = e.file.read()
        value = json.loads(str(response, "utf8"))

        if value and value.get("error"):
            self.raise_exception(value["error"])

        return value


    def raise_exception(self, error_object):
        """
        Takes an API error object and raises the appropriate exception,
        attaching the code and description to the object. The classes
        are mapped to the codes as follows:

        0, 1, 2: ChildProcessError (internal server, http, and json errors)
        3: ValueError (invalid endpoint arguments)
        4: UserWarning (illegal values provided by user, not a real "error")
        5: ConnectionRefusedError (authorizations declined)

        To capture a code and description in your client:

        try:
            response = bbj.endpoint():
        except UserWarning as e:
            assert e.code == 4
            print(e.description)
            # want the raw error object? thats weird, but whatever.
            return e.body
        """
        description = error_object["description"]
        code = error_object["code"]
        if code in [0, 1, 2]:
            e = ChildProcessError(description)

        elif code == 3:
            e = ValueError(description)

        elif code == 4:
            e = UserWarning(description)

        elif code == 5:
            e = ConnectionRefusedError(description)

        e.code, e.description, e.body = code, description, error_object
        raise e


    def update_instance_info(self):
        """
        Stores configuration info for the connected BBJ server.

        {
            "instance_name": (string), // a title set by the server owner
            "allow_anon": (bool), // whether anonymous participation is allowed
            "admins": (list) // usernames of those who have admin rights on the server
        }
        """
        response = self("instance_info")
        self.instance_info = response["data"]


    def validate(self, key, value, exception=AssertionError):
        """
        Uses the server's db_validate method to verify the validty
        of `value` by `key`. If it is invalid, kwarg exception (default
        AssertionError) is raised with the exception containing the
        attribute .description as the server's reason. Exception can
        be a False value to just return boolean False.

        Examples:

        # this will fail bacause the server wont allow newlines in usernames.
          try:
              bbj.validate("user_name", "des\nvox")
          except AssertionError as e:
              print(e.description)

        # or you can handle it as a boolean like this:
        is_okay = bbj.validate("title", "teacups and roses <3", exception=None)
        """
        response = self(
            "db_validate",
            no_auth=True,
            key=key,
            value=value
        )

        if not response["data"]["bool"]:
            if not exception:
                return False
            description = response["data"]["description"]
            error = exception(description)
            error.description = description
            raise error

        return True


    def validate_all(self, keys_and_values, exception=AssertionError):
        """
        Takes a single iterable object as its argument, containing
        assertions to make, and applies `validate` to each pair.
        See `validate` for full details. This method also takes
        the kwarg `exception`, and passes it to validate.

        Returns a list containing each response from validate. Under
        successful circumstances, each element will be True. If you
        specify exception=None, then the elements can contain false
        as well.

        Example:
          values = [
            ("title", "the wea\nther sucks"),
            ("body", "rain is gross lmao")
          ]

          try:
              bbj.validate_all(values)
          except AssertionError as e:
              print(e.description)

          # as booleans:
          validated = bbj.validate_all(values, exception=None)
          # => [False, True]
          assert all(validated)

        """
        return [
            self.validate(key, value, exception) for key, value in keys_and_values
        ]


    def set_credentials(self, user_name, user_auth, hash_auth=True, check_validity=True):
        """
        Internalizes user_name and user_auth. Unless hash_auth=False is
        specified, user_auth is assumed to be an unhashed password
        string and it gets hashed with sha256. If you want to handle
        hashing yourself, make sure to disable that.

        Unless check_validity is set to false, the new credentials are
        sent to the server and a ConnectionRefusedError is raised if
        they do not match server authentication data. ValueError is
        raised if the credentials contain illegal values, or the
        specified user is not registered. If you need to differentiate
        the two, using the method `user_is_registered` might be more
        your speed.

        On success, True is returned and the values are set. Subsequent
        requests will now be authorized for the user (see request()'s
        documentation for details on how to override this behavior
        when necessary)

        Examples:
          try:
              bbj.set_credentials("user", "i am sandvich")
          except ConnectionRefusedError:
              # bad auth info
          except ValueError:
              # paramter validation failed or the user is not registered

          # you can handle hashing yourself if you want
          password = input("Enter your password:")
          bbj.set_credentials(
              "user",
              sha256(bytes(password, "utf8")).hexdigest(),
              hash_auth=False
          )
        """
        if check_validity and not self.validate_credentials(user_name, user_auth):
            self.user_auth = self.user_name = None
            raise ConnectionRefusedError("Auth and User do not match")

        self.user_auth = user_auth
        self.user_name = user_name
        self.user = self("get_me")["data"]
        return True


    def validate_credentials(self, user_name, user_auth, exception=True):
        """
        Pings the server to check that user_name can be authenticated with
        user_auth. Raises ConnectionRefusedError if they cannot. Raises
        ValueError if the credentials contain illegal values.

        Alternatively, you can specify exception=False to just return a
        boolean False if the credentials are incorrect. Will still raise
        a ValueError if the parameters are illegal.

        Example:
          # this method DOES NOT take a password string. it must be hashed.
          try: validate_credentials("user", hashed_password)
          except ConnectionRefusedError:
              ...
          except ValueError:
              ...

          # as a boolean:
          is_okay = bbj.validate_credentials("user", hashed_password, exception=False)
        """
        self.validate_all([
                ("user_name", user_name),
                ("auth_hash", user_auth)
            ], ValueError)
        try:
            response = self("check_auth",
                no_auth=True,
                target_user=user_name,
                target_hash=user_auth
            )
            return response["data"]

        except ConnectionRefusedError as e:
            if exception:
                raise e
            return False


    def user_is_registered(self, user_name):
        """
        Returns True or False whether user_name is registered
        into the system.
        """
        response = self(
            "user_is_registered",
            no_auth=True,
            target_user=user_name
        )

        return response["data"]


    def user_register(self, user_name, user_auth, hash_auth=True, set_as_user=True):
        """
        Register user_name into the system with user_auth. Unless hash_auth
        is set to false, user_auth should be a password string.

        When set_as_user is True, the newly registered user is internalized
        and subsequent uses of the object will be authorized for them.

        Example:

          try:
              bbj.user_register("user", "sandvich")
          except UserWarning as e:
              # show this to users. always.
              print(e.description)

          # the object is now also set for this user...
          assert bbj.get_me()["user_name"] == "user"
          # ...unless you call it like this:
          # bbj.user_register("user", "sandvich", set_as_user=False)
        """
        if hash_auth:
            user_auth = sha256(bytes(user_auth, "utf8")).hexdigest()

        response = self("user_register",
            no_auth=True,
            user_name=user_name,
            auth_hash=user_auth
        )["data"]

        assert all([
            user_auth == response["auth_hash"],
            user_name == response["user_name"]
        ])

        if set_as_user:
            self.set_credentials(user_name, user_auth, False)

        return response


    def user_update(self, **params):
        """
        Update the user's data on the server. The new parameters
        may be any of `user_name`, `auth_hash`, `quip`, `bio`,
        `color`. On success, the newly updated user object is
        returned and is also internalized as self.user.
        """
        response = self("user_update", **params)
        if params.get("user_name"):
            self.user_name = params["user_name"]
        if params.get("auth_hash"):
            self.user_auth = params["auth_hash"]
        self.user = self("get_me")["data"]
        return response["data"]


    def user_get(self, user_id_or_name):
        """
        Return a full user object by their id or username.
        Note that this isn't required when using thread_load
        or thread_index, because they return a usermap which
        is a dictionary with keys of the ids connected to these
        same objects. You shouldn't use this method when a usermap
        is provided.

        If the user element isnt found, ValueError is raised.
        See also `user_is_registered`
        """
        response = self("user_get", target_user=user_id_or_name)
        return response["data"]


    def thread_index(self, include_op=False):
        """
        Returns a tuple where [0] is a list of all threads ordered by
        most recently interacted, and [1] is a usermap object.

        Example:
          threads, usermap = bbj.thread_index()
          for thread in threads:
              author_id = thread["author"]
              print(usermap[author_id]["user_name"])
        """
        response = self("thread_index", include_op=include_op)
        return response["data"], response["usermap"]


    def thread_load(self, thread_id, format=None, op_only=False):
        """
        Returns a tuple where [0] is a thread object and [1] is a usermap object.

        Example:
          thread, usermap = bbj.thread_load(some_id)
          for message in thread["messages"]:
              author_id = message["author"]
              print(usermap[author_id]["user_name"])
              print(message["body"])
        """
        response = self("thread_load",
            format=format, thread_id=thread_id, op_only=op_only)
        return response["data"], response["usermap"]


    def thread_create(self, title, body):
        """
        Submit a new thread, and return its new object. Requires the
        string arguments `title` and `body`. Title must be under
        120 chars in length, else UserWarning is raised. Body must
        also not be empty.
        """
        response = self("thread_create", title=title, body=body)
        return response["data"]


    def thread_reply(self, thread_id, body):
        """
        Submits a new reply to a thread and returns the new object.
        Requires the thread's id and a non-empty body string.
        """
        response = self("thread_reply", thread_id=thread_id, body=body)
        return response["data"]


    def fake_message(self, body="!!", format="sequential", author=None, post_id=0):
        """
        Produce a a valid message object with `body`. Useful for
        testing and can also be used mimic server messages in a
        client.
        """
        return {
            "body": self.format_message(body, format),
            "author": author or self.user["user_id"],
            "post_id": post_id,
            "created": time(),
            "edited": False,
            "send_raw": False,
            "thread_id": "gibberish"
        }


    def format_message(self, body, format="sequential"):
        """
        Send `body` to the server to be formatted according to `format`,
        defaulting to the sequential parser. Returns the body object.
        """
        response = self("format_message", body=body, format=format)
        return response["data"]


    def message_delete(self, thread_id, post_id):
        """
        Delete message `post_id` from `thread_id`. The same rules apply
        to deletions as they do for edits. The same exceptions are raised
        with the same descriptions. If post_id is 0, this will also delete
        the entire thread. Returns True on success.
        """
        response = self("delete_post", thread_id=thread_id, post_id=post_id)
        return response["data"]


    def edit_query(self, thread_id, post_id):
        """
        Queries ther server database to see if a post can
        be edited by the logged in user. thread_id and
        post_id are required.

        Returns a message object on success, or raises
        a UserWarning describing why it failed.
        """
        response = self("edit_query", thread_id=thread_id, post_id=int(post_id))
        return response["data"]


    def can_edit(self, thread_id, post_id):
        """
        Return bool True/False that the post at thread_id | post_id
        can be edited by the logged in user. Will not raise UserWarning.
        """
        try:
            result = bool(self.edit_query(thread_id, post_id))
        except UserWarning:
            result = False
        return result


    def edit_message(self, thread_id, post_id, new_body):
        """
        Requires the thread_id and post_id. The edit flag is then
        set on the message, new_body is set on the server, and the
        newly edited message object is returned on success.

        Will raise UserWarning if server editing rules are violated.
        See also `can_edit` and `edit_query`
        """
        response = self(
            "edit_post", thread_id=thread_id,
            post_id=post_id, body=new_body)
        return response["data"]


    def set_post_raw(self, thread_id, post_id, value):
        """
        This is a subset of `edit_message` that retains the old
        body and just sets its `send_raw` to your supplied `value`.
        The `edited` parameter of the message on the server is not
        modified.
        """
        response = self(
            "set_post_raw",
            thread_id=thread_id,
            post_id=post_id,
            value=bool(value))
        return response["data"]


    def user_is_admin(self, user_name_or_id):
        """
        Return boolean True or False whether the given user identifier
        is an admin on the server. Will raise ValueError if this user
        is not registered.
        """
        response = self("is_admin", target_user=user_name_or_id)
        return response["data"]


    def thread_set_pin(self, thread_id, new_status):
        """
        Set whether a thread should be pinned or not. new_status
        is evaluated as a boolean, and given that the logged in
        user is an admin, the thread is set to this status on
        the server, and the boolean is returned.
        """
        response = self("thread_set_pin", thread_id=thread_id, value=new_status)
        return response["data"]


    def message_feed(self, time, format=None):
        """
        Returns a special object representing all activity on the board since
        the argument `time`, a unix/epoch timestamp.

        {
            "threads": {
                "thread_id": {
                    ...thread object
                },
                ...more thread_id/object pairs
            },
            "messages": [...standard message object array sorted by date],
            "usermap": {
                ...standard user_id mapping object
            }
        }

        The message objects in "messages" are the same objects returned
        in threads normally. They each have a thread_id parameter, and
        you can access metadata for these threads by the "threads" object
        which is also provided. All user_ids can be resolved into full user
        objects from the usermap object.

        The "messages" array is already sorted by submission time, newest
        first. The order in the threads object is undefined and you should
        instead use their `last_mod` attribute if you intend to list them
        out visually.

        the optional argument `format` can be given and bahaves the same
        as `thread_load`.
        """
        response = self("message_feed", time=time, format=format)
        return {
            "usermap": response["usermap"],
            "threads": response["data"]["threads"],
            "messages": response["data"]["messages"]
        }
