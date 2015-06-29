#!/usr/bin/env fish
mpv $argv[1] | python main.py -i $argv[1] -o /dev/ttyUSB0
