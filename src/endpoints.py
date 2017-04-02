from src import db, schema

def user_register(user_name, auth_hash):
    return db.user_register(user_name, auth_hash)
