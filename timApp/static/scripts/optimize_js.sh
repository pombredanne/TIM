#!/usr/bin/env bash
echo Minifying compiled TypeScript files...
../../../run_command.sh /bin/bash -c 'cd static/scripts && node node_modules/.bin/r.js -o build/app.build.js'
