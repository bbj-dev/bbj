from src import schema

def ordered_keys(subscriptable_object, *keys):
    """
    returns a tuple with the values for KEYS in the order KEYS are provided,
    from SUBSCRIPTABLE_OBJECT. Useful for working with dictionaries when
    parameter ordering is important. Used for sql transactions.
    """
    return tuple([subscriptable_object[key] for key in keys])


def schema_values(scheme, obj):
    """
    Returns the values in the database order for a given
    schema. Used for sql transactions.
    """
    if scheme == "user":
        return ordered_keys(obj,
            "user_id", "user_name", "auth_hash", "quip",
            "bio", "color", "is_admin", "created")

    elif scheme == "thread":
        return ordered_keys(obj,
            "thread_id", "author", "title",
            "last_mod", "created", "reply_count",
            "pinned", "last_author")

    elif scheme == "message":
        return ordered_keys(obj,
            "thread_id", "post_id", "author",
            "created", "edited", "body", "send_raw")
