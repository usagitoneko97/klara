#!/bin/sh

top -d 5 -b | grep --line-buffered $1 | tee $2
