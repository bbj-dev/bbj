Errors in BBJ are separated into 6 different codes to help
ease handling a little bit. Errors are all or nothing, there
are no "warnings". If a response has a non-false error field,
then data will always be null. An error response from the api
looks like this...

```
{
  "error": {
      "code": // an integer from 0 to 5,
      "description": // a string describing the error in detail.
  }
  "data": null   // ALWAYS null if error is not false
  "usermap": {}  // ALWAYS empty if error is not false
}
```

The codes split errors into a few categories. Some are oriented
to client developers while others should be shown directly to
users.

  * 0: Malformed but non-empty json input. An empty json input where it is required is handled by code 3. This is just decoding errors. The exception text is returned as description.
  * 1: Internal server error. A short representation of the internal exception as well as the code the server logged it as is returned in the description. Your clients cannot recover from this class of error, and its probably not your fault if you encounter it. If you ever get one, file a bug report.
  * 2: Server HTTP error: This is similar to the above but captures errors for the HTTP server rather than BBJs own codebase. The description contains the HTTP error code and server description. This notably covers 404s and thus invalid endpoint names.
  * 3: Parameter error: client sent erroneous input for its method. This could mean missing arguments, type errors, etc. It generalizes errors that should be fixed by the client developer and the returned descriptions are geared to them rather than end users.
  * 4: User error: These errors regard actions that the user has taken that are invalid, but not really errors in a traditional sense. The description field should be shown to users verbatim, in a clear and noticeable fashion. They are formatted as concise English sentences and end with appropriate punctuation marks.
  * 5: Authorization error: This code represents an erroneous User/Auth header pair. This should trigger the user to provide correct credentials or fall back to anon mode.
