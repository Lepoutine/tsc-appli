#!/bin/sh
# Construit tsc-graphics.dll (Windows x64) depuis Linux avec clang + lld, sans SDK Windows.
set -e
cd "$(dirname "$0")"
O=${1:-tsc-graphics.dll}
T=$(mktemp -d)
llvm-dlltool -m i386:x86-64 -d kernel32.def -l "$T/kernel32.lib"
llvm-dlltool -m i386:x86-64 -d user32.def -l "$T/user32.lib"
clang --target=x86_64-pc-windows-msvc -x c++ -std=c++17 -ffreestanding -fno-builtin -fno-exceptions -fno-rtti -fno-stack-protector -mno-stack-arg-probe -O2 -Wall -Wextra -c tsc_graphics.cpp -o "$T/g.obj"
llvm-rc -c 1252 -fo "$T/g.res" graphics.rc
lld-link /dll /nodefaultlib /entry:DllMain /def:exports.def /machine:x64 /out:"$O" "$T/g.obj" "$T/g.res" "$T/kernel32.lib" "$T/user32.lib"
rm -rf "$T"; rm -f "${O%.dll}.lib" "${O%.dll}.exp"
echo "ok : $O"
