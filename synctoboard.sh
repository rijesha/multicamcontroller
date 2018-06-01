#!/bin/bash

echo "ip: $1"

rsync -vv --delete  -r . root@10.42.0.$1:~/multicamcontroller/

