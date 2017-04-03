"""
These exceptions create schema objects to send back to the client.
The new error codes have not been fully documented since ditching
the prototype but there are less of them and the handling is much
more robust and less verbose in the source code.

At any point of the API's codepath, these may be raised and will be
captured by the request handler. Their schema is then sent back to
the client.
"""

from src.schema import error


class BBJException(Exception):
    """
    Base class for all exceptions specific to BBJ. These also
    hold schema error objects, reducing the amount of code
    required to produce useful errors.
    """
    def __init__(self, code, description):
        self.schema = error(code, description)
        self.description = description
        self.code = code

    def __str__(self):
        return self.description


class BBJParameterError(BBJException):
    """
    This class of error holds code 3. This is a general
    classification used to report errors on behalf of
    the client. It covers malformed or missing parameter
    values for endpoints, type errors, index errors, etc.
    A complete client should not encounter these and the
    descriptions are geared towards client developers
    rather than users.
    """
    def __init__(self, description):
        super().__init__(3, description)


class BBJUserError(BBJException):
    """
    This class of error holds code 4. Its description should
    be shown verbatim in clients, as it deals with invalid user
    actions rather than client or server errors. It is especially
    useful during registration, and reporting lack of admin privs
    when editing messages.
    """
    def __init__(self, description):
        super().__init__(4, description)


class BBJAuthError(BBJException):
    """
    This class of error holds code 5. Similar to code 4,
    these should be shown to users verbatim. Provided when:

      * a client tries to post without user/auth_hash pair
      * the auth_hash does not match the given user
    """
    def __init__(self, description):
        super().__init__(5, description)
