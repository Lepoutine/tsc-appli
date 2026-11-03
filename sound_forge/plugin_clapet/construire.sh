#!/bin/sh
# Construit tsc-clapet.dll (Windows x64) depuis Linux avec clang + lld, sans SDK Windows ni CRT.
set -e
cd "$(dirname "$0")"
O=${1:-tsc-clapet.dll}
T=$(mktemp -d)
llvm-dlltool -m i386:x86-64 -d kernel32.def -l "$T/kernel32.lib"
clang --target=x86_64-pc-windows-msvc -x c++ -std=c++17 -ffreestanding -fno-builtin -fno-exceptions -fno-rtti -fno-stack-protector -O2 -Wall -Wextra -Wno-unused-parameter -Isdk/include -c tsc_clapet.cpp -o "$T/clapet.obj"
lld-link /dll /nodefaultlib /entry:DllMain /def:exports.def /machine:x64 /out:"$O" "$T/clapet.obj" "$T/kernel32.lib"
rm -rf "$T"; rm -f "${O%.dll}.lib" "${O%.dll}.exp"
echo "ok : $O"
