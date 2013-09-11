#!/bin/bash -eu

WORKDIR=$(pwd)

MIRROR=$WORKDIR/mirror

QUEUE=$WORKDIR/queue
PENDING=$QUEUE/pending
RUNNING=$QUEUE/running


push_to_pending() {
    cd $MIRROR

    cat index | awk '{print $2}' | while read FROM; do
        TO=$(echo $FROM | sed 's!/!_!g')
        cp -v $FROM $PENDING/$TO
    done
    echo "$(wc -l index | awk '{print $1}') ks files were copied"
}

check_exist_files_in_queue() {
    files=$(find $PENDING $RUNNING -type f)
    if [ -n "$files" ]; then
        echo "There are some files in queue:"
        echo $files | xargs -n1
        echo -n "Do you want to delete them all ?[N/y] "

        read choice
        if [ "$choice" == y ] || [ "$choice" == Y ]; then
            rm -v $files
        fi
    fi
}

#### Main
if [ ! -d $QUEUE ]; then
    echo "Can't find queue($QUEUE), maybe you are in a wrong directory !"
    exit 1
fi

check_exist_files_in_queue

python $(dirname $0)/grab_ks.py && push_to_pending