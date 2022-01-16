#!/bin/sh

create_db() {
  sqlite3 data.sqlite < schema.sql
  chmod 600 data.sqlite
}

case $1 in
    --help)
      cat <<EOF
This script initializes the deps and files for bbj and also sets up its database.
It takes the following flags:
  --help to print this
  --dbset only runs the sql script

You can optionally pass a different python interpreter to use (such as
a virtual environment), with no arguments this will use the system python3

EOF
      exit;;

    --dbset)
      create_db
      exit;;
esac

[ -e logs ] || mkdir -p logs/exceptions

PYTHON=$(which python3)
[ -z "$1" ] || PYTHON="$1"
printf "Using %s...\n" "$PYTHON"
$PYTHON -m pip install -r requirements.txt

printf "Enter [i] to initialize a new database\n"
read -r CLEAR

if [ "$CLEAR" = "i" ]; then
    create_db
fi
