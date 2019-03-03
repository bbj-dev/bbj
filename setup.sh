#!/bin/bash

DEPS=(
    cherrypy
    urwid
)

case $1 in
    --help )
        cat <<EOF
This script initializes the deps and files for bbj and also sets up its database.
It takes the following flags:
  --help to print this
  --dbset only runs the sql script

You can optionally pass a different python interpreter to use (such as
a virtual environment), with no arguments this will use the system python3

EOF
        exit;;

    --dbset )
        sqlite3 data.sqlite < schema.sql
        echo cleared
        chmod 600 data.sqlite
        exit;;
esac

[[ -e logs ]] || mkdir logs; mkdir logs/exceptions

PYTHON=`which python3`
[[ -z $1 ]] || PYTHON=$1
echo Using $PYTHON...
$PYTHON -m pip install ${DEPS[*]}

echo "Enter [i] to initialize a new database"
read CLEAR

if [[ $CLEAR == "i" ]]; then
    sqlite3 data.sqlite < schema.sql 
    chmod 600 data.sqlite
fi

