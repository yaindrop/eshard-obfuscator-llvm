# LLVM 22 smoke tests

These tests validate that the plugin builds and remains usable with a modern
LLVM toolchain. They are intentionally small but cover the important release
risks:

- the shared plugin loads through `clang -fpass-plugin`;
- obfuscated binaries preserve runtime behavior;
- each pass can be invoked through `opt -load-pass-plugin`;
- transformed IR passes LLVM verification;
- key passes perform a visible structural transformation;
- string encryption removes the plaintext fixture string from emitted IR.

Run them through CTest after configuring against LLVM 22:

```sh
cmake -S . -B build -G Ninja \
  -DLLVM_DIR=/opt/homebrew/opt/llvm@22/lib/cmake/llvm \
  -DCMAKE_C_COMPILER=/opt/homebrew/opt/llvm@22/bin/clang \
  -DCMAKE_CXX_COMPILER=/opt/homebrew/opt/llvm@22/bin/clang++
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```
