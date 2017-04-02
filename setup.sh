#!/bin/bash
set -e

if [[ $1 == --init ]]; then
	sqlite3 data.sqlite < schema.sql
	echo cleared
	exit
fi

DEPS=(
    cherrypy
    markdown
)

if [[ -z $1 ]]; then
    cat << EOF
Pass the python interpreter to use for pip installation
(either a venv or a system interpreter)
EOF
    exit
fi

$1 -m pip install ${DEPS[*]}

echo "Enter [i] to initialize a new database"
read CLEAR
[[ $CLEAR == "i" ]] && sqlite3 bbj.db < schema.sql
