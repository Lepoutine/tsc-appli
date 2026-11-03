#!/bin/sh
# Test du plugin sous Linux (faux jeu, faux Windows, faux XAudio2), avec controle des debordements memoire.
set -e; cd "$(dirname "$0")"; S=..
T=$(mktemp -d)
sed 's/#include "clapet_win.h"/#include "test\/clapet_win.h"/' $S/tsc_clapet.cpp > "$T/clapet.cpp"
g++ -std=c++17 -DTSC_TEST -fsanitize=address,undefined -fno-sanitize=vptr -g -w -I. -I$S -I$S/sdk/include -o "$T/test" test.cpp "$T/clapet.cpp" -lpthread
"$T/test"; r=$?; rm -rf "$T"; exit $r
