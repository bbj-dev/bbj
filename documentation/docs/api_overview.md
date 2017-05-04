
# How to BBJ?

## Input

BBJ is interacted with entirely through POST requests, whose bodies are
json objects.

The endpoints, all listed below, can be contacted at the path /api/ relative
to the root of where BBJ is hosted. If bbj is hosted on a server on port 80
at the root:

`http://server.com/api/endpoint_here`

The body of your request contains all of it's argument fields, instead of
using URL parameters. As a demonstration, to call `thread_create`,
it requires two arguments: `title`, and `body`. We put those argument
names at the root of the json object, and their values are the info
passed into the API for that spot. Your input will look like this:

```json
{
    "title": "Hello world!!",
    "body": "Hi! I am exploring this cool board thing!!"
}
```

And you will POST this body to `http://server.com:PORT/api/thread_create`.

A few endpoints do not require any arguments. These can still be POSTed to,
but the body may be completely empty or an empty json object. You can even
GET these if you so choose.

For all endpoints, argument keys that are not consumed by the endpoint are
ignored. Posting an object with a key/value pair of `"sandwich": True` will
not clog up any pipes :) In the same vein, endpoints who dont take arguments
don't care if you supply them anyway.

## Output

BBJ returns data in a consistently formatted json object. The base object
has three keys: `data`, `usermap`, and `error`. Visualizied:

```javascript
{
  "error":   false, // boolean false or error object
  "data":    null,  // null or the requested data from endpoint.
  "usermap": {}     // potentially empty object, maps user_ids to user objects
}

// If "error" is true, it looks like this:

{
  "error": {
      "code": // an integer from 0 to 5,
      "description": // a string describing the error in detail.
  }
  "data": null   // ALWAYS null if error is not false
  "usermap": {}  // ALWAYS empty if error is not false
}
```

### data

`data` is what the endpoint actually returns. The type of contents vary
by endpoint and are documented below. If an endpoint says it returns a
boolean, it will look like `"data": True`. If it says it returns an array,
it will look like `"data": ["stuff", "goes", "here"]`

### usermap

The usermap is a json object mapping user_ids within `data` to full user
objects. BBJ handles users entirely by an ID system, meaning any references
to them inside of response data will not include vital information like their
username, or their profile information. Instead, we fetch those values from
this usermap object. All of it's root keys are user_id's and their values
are user objects. It should be noted that the anonymous user has it's own
ID and profile object as well.

### error

`error` is typically `false`. If it is __not__ false, then the request failed
and the json object that `error` contains should be inspected. (see the above
visualation) Errors follow a strict code system, making it easy for your client
to map these responses to native exception types or signals in your language of
choice. See [the full error page](errors.md) for details.


# Authorization

## check_auth

### Args:
**target_user**: string: either a user_name or a user_id

**target_hash**: string: sha256 hash for the password to check



Takes the arguments `target_user` and `target_hash`, and
returns boolean true or false whether the hash is valid.



--------

# Threads & Messages

## delete_post

### Args:
**thread_id**: string: the id of the thread this message was posted in.

**post_id**: integer: the id of the target message.



Requires the arguments `thread_id` and `post_id`.

Delete a message from a thread. The same rules apply
here as `edit_post` and `edit_query`: the logged in user
must either be the one who posted the message within 24hrs,
or have admin rights. The same error descriptions and code
are returned on falilure. Boolean true is returned on
success.

If the post_id is 0, the whole thread is deleted.

## edit_post

### Args:
**thread_id**: string: the thread the message was posted in.

**post_id**: integer: the target post_id to edit.

**body**: string: the new message body.

**OPTIONAL: send_raw**: boolean: set the formatting mode for the target message.



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

## edit_query

### Args:
**thread_id**: string: the id of the thread the message was posted in.

**post_id**: integer: the id of the target message.



Queries the database to ensure the user can edit a given
message. Requires the arguments `thread_id` and `post_id`
(does not require a new body)

Returns the original message object without any formatting
on success. Returns a descriptive code 4 otherwise.

## message_feed

### Args:
**time**: int/float: epoch/unix time of the earliest point of interest



Returns a special object representing all activity on the board since
the argument `time`, a unix/epoch timestamp.

{
    "threads": {
        "thread_id": {
            ...thread object
        },
        ...more thread_id/object pairs
    },
    "messages": [...standard message object array sorted by date]
}

The message objects in "messages" are the same objects returned
in threads normally. They each have a thread_id parameter, and
you can access metadata for these threads by the "threads" object
which is also provided.

The "messages" array is already sorted by submission time, newest
first. The order in the threads object is undefined and you should
instead use their `last_mod` attribute if you intend to list them
out visually.

You may optionally provide a `format` argument: this is treated
the same way as the `thread_load` endpoint and you should refer
to its documentation for more info.

## set_post_raw

### Args:
**thread_id**: string: the id of the thread the message was posted in.

**post_id**: integer: the id of the target message.

**value**: boolean: the new `send_raw` value to apply to the message.



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

## set_thread_pin

### Args:
**thread_id**: string: the id of the thread to modify.

**value**: boolean: `true` to pin thread, `false` otherwise.



Requires the arguments `thread_id` and `value`. `value`
must be a boolean of what the pinned status should be.
This method requires that the caller is logged in and
has admin status on their account.

Returns the same boolean you supply as `value`

## thread_create

### Args:
**body**: string: The body of the first message

**title**: string: The title name for this thread

**OPTIONAL: send_raw**: boolean: formatting mode for the first message.



Creates a new thread and returns it. Requires the non-empty
string arguments `body` and `title`.

If the argument `send_raw` is specified and has a non-nil
value, the OP message will never recieve special formatting.

## thread_index

### Args:
**OPTIONAL: include_op**: boolean: Include a `messages` object with the original post



Return an array with all the threads, ordered by most recent activity.
Requires no arguments.

Optionally, you may supply the argument `include_op`, which, when
non-nil, will include a "messages" key with the object, whose sole
content is the original message (post_id 0).

## thread_load

### Args:
**thread_id**: string: the thread to load.

**OPTIONAL: op_only**: boolean: include only the original message in `messages`

**OPTIONAL: format**: string: the formatting type of the returned messages.



Returns the thread object with all of its messages loaded.
Requires the argument `thread_id`. `format` may also be
specified as a formatter to run the messages through.
Currently only "sequential" is supported.

You may also supply the parameter `op_only`. When it's value
is non-nil, the messages array will only include post_id 0 (the first)

## thread_reply

### Args:
**thread_id**: string: the id for the thread this message should post to.

**body**: string: the message's body of text.

**OPTIONAL: send_raw**: boolean: formatting mode for the posted message.



Creates a new reply for the given thread and returns it.
Requires the string arguments `thread_id` and `body`

If the argument `send_raw` is specified and has a non-nil
value, the message will never recieve special formatting.



--------

# Tools

## db_validate

### Args:
**key**: string: the identifier for the ruleset to check.

**value**: VARIES: the object for which `key` will check for.

**OPTIONAL: error**: boolean: when `true`, will return an API error response instead of a special object.



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

## format_message

### Args:
**body**: string: the message body to apply formatting to.

**format**: string: the specifier for the desired formatting engine



Requires the arguments `body` and `format`. Applies
`format` to `body` and returns the new object. See
`thread_load` for supported specifications for `format`.

## user_map

### Args:
__No arguments__

Returns an array with all registered user_ids, with the usermap
object populated by their full objects.



--------

# Users

## get_me

### Args:
__No arguments__

Requires no arguments. Returns your internal user object,
including your authorization hash.

## is_admin

### Args:
**target_user**: string: user_id or user_name to check against.



Requires the argument `target_user`. Returns a boolean
of whether that user is an admin.

## user_get

### Args:
**target_user**: string: either a user_name or a user_id



Retreive an external user object for the given `target_user`.
Can be a user_id or user_name.

## user_is_registered

### Args:
**target_user**: string: either a user_name or a user_id



Takes the argument `target_user` and returns true or false
whether they are in the system or not.

## user_register

### Args:
**user_name**: string: the desired display name

**auth_hash**: string: a sha256 hash of a password



Register a new user into the system and return the new object.
Requires the string arguments `user_name` and `auth_hash`.
Do not send User/Auth headers with this method.

## user_update

### Args:
**Any of the following may be submitted:**: 

**user_name**: string: a desired display name

**auth_hash**: string: sha256 hash for a new password

**quip**: string: a short string that can be used as a signature

**bio**: string: a user biography for their profile

**color**: integer: 0-6, a display color for the user



Receives new parameters and assigns them to the user_object
in the database. The following new parameters can be supplied:
`user_name`, `auth_hash`, `quip`, `bio`, and `color`. Any number
of them may be supplied.

The newly updated user object is returned on success.



--------

