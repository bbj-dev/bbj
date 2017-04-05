import urllib.request as url
from hashlib import sha256
import json


class BBJ:
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
    def __init__(self, host="127.0.0.1", port=7099):
        self.base = "http://{}:{}/api/%s".format(host, port)
        self.user_name = self.user_auth = None
        self.send_auth = True


    def __call__(self, *args, **kwargs):
        return self.request(*args, **kwargs)


    def request(self, endpoint, **params):
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
        Takes an API error object and raises the appropriate exception.
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


    def validate(self, key, value, exception=AssertionError):
        """
        Uses the server's db_sanity_check method to verify the validty
        of value by key. If it is invalid, kwarg exception (default
        AssertionError) is raised with the exception containing the
        attribute .description as the server's reason. Exception can
        be a False value to just rturn boolean False.
        """
        response = self(
            "db_sanity_check",
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
        Accepts an iterable of tuples, where in each, [0] is a key and
        [1] a value to pass to validate.
        """
        for key, value in keys_and_values:
            self.validate(key, value, exception)



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
        specified user is not registered.

        On success, True is returned and the values are set.
        """
        if hash_auth:
            user_auth = sha256(bytes(user_auth, "utf8")).hexdigest()

        if check_validity and not self.validate_credentials(user_name, user_auth):
            self.user_auth = self.user_name = None
            raise ConnectionRefusedError("Auth and User do not match")

        self.user_auth = user_auth
        self.user_name = user_name
        return True


    def validate_credentials(self, user_name, user_auth):
        """
        Pings the server to check that user_name can be authenticated with
        user_auth. Raises ConnectionRefusedError if they cannot. Raises
        ValueError if the credentials contain illegal values.
        """
        self.validate_all([
                ("user_name", user_name),
                ("auth_hash", user_auth)
            ], ValueError)
        response = self("check_auth",
             no_auth=True,
             target_user=user_name,
             target_hash=user_auth
        )
        return response["data"]


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


    def user_is_registered(self, target_user):
        """
        Returns a boolean true or false whether target_user
        is a registered BBJ user.
        """
        return self("user_is_registered", target_user=target_user)["data"]


    def user_register(self, user_name, user_auth, hash_auth=True, set_as_user=True):
        """
        Register user_name into the system with user_auth. Unless hash_auth
        is set to false, user_auth should be a password string.

        When set_as_user is True, the newly registered user is internalizedn
        and subsequent uses of the object will be authorized for them.
        """
        if hash_auth:
            user_auth = sha256(bytes(user_auth, "utf8")).hexdigest()

        response = self(
            "user_register",
            no_auth=True,
            user_name=user_name,
            auth_hash=user_auth
        )["data"]

        assert all([
            user_auth == response["auth_hash"],
            user_name == response["user_name"]
        ])

        if set_as_user:
            self.user_name = user_name
            self.user_auth = user_auth

        return response


    def thread_index(self):
        """
        Returns a tuple where [0] is a list of all threads ordered by
        most recently interacted, and [1] is a usermap object.
        """
        response = self("thread_index")
        return response["data"], response["usermap"]


    def thread_load(self, thread_id):
        """
        Returns a tuple where [0] is a thread object and [1] is a usermap object.
        """
        response = self("thread_load", thread_id=thread_id)
        return response["data"], response["usermap"]
