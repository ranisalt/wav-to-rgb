#!/usr/bin/env fish
ffmpeg -i $argv[1] -ac 1 $argv[2]
