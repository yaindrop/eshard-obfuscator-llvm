# LLVM 23 obfuscator plugin

This fork is an LLVM 23 native obfuscation pass plugin. It applies
transformations on [LLVM IR](https://llvm.org/docs/LangRef.html) through the
modern LLVM pass plugin API.

Only LLVM 23.x is supported. Older LLVM pass-manager compatibility code has
been removed on purpose.

## Compilation

Build against an LLVM 23 installation (Homebrew's unversioned `llvm` currently provides 23):

```
cmake -S . -B build -G Ninja \
  -DLLVM_DIR=/opt/homebrew/opt/llvm/lib/cmake/llvm \
  -DCMAKE_C_COMPILER=/opt/homebrew/opt/llvm/bin/clang \
  -DCMAKE_CXX_COMPILER=/opt/homebrew/opt/llvm/bin/clang++
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

If the compilation is successful, the plugin is `libLLVMObfuscator` with the
platform shared-library extension and can be used with **clang**
(`-fpass-plugin=`) or **opt** (`-load-pass-plugin`).

## Usage

### With clang

This plugin can be used with clang's switch `-fpass-plugin`.

`clang -fpass-plugin=<path/to/libLLVMObfuscator> hello_world.c -o hello_world`

You can chose to insert passes in the optimization pipeline by setting the following environment variables before running clang:
- LLVM_OBF_PEEPHOLE_PASSES
- LLVM_OBF_SCALAROPTIMIZERLATE_PASSES
- LLVM_OBF_VECTORIZERSTART_PASSES
- LLVM_OBF_PIPELINESTART_PASSES
- LLVM_OBF_PIPELINEEARLYSIMPLIFICATION_PASSES
- LLVM_OBF_OPTIMIZERLASTEP_PASSES

For instance if you want to run the flattening, bogus and substitution passes in that order, you can do:
`export LLVM_OBF_SCALAROPTIMIZERLATE_PASSES="flattening, bogus, substitution, split-basic-blocks"`

Or you can run the string encryption pass with:
`export LLVM_OBF_OPTIMIZERLASTEP_PASSES="string-encryption"`

Refer to the llvm::PassBuilder documentation for more information on each insertion point.

### With opt

[`opt`](https://llvm.org/docs/CommandGuide/opt.html) can be used to apply specific passes from LLVM IR you
would pre-generate using `clang`.

```
# pre-generate LLVM IR
clang -O1 -S -emit-llvm hello_world.c -o hello_world.ll

# apply the pass
opt -S -load-pass-plugin <path/to/libLLVMObfuscator> \
  -passes="<my-pass-name>" hello_world.ll -o hello_world_obfuscated.ll

# generate the binary file
clang hello_world_obfuscated.ll -o hello_world_obfuscated
```

### Debugging

To allow debugging passes in a deterministic way, the environment variable `LLVM_OBF_SEED` can be set to fix the CryptoUtils seed (used to for all random number generation and
encryption).

The variable should contain a hex string of 32 characters or 34 characters if prefixed with "0x", for example:
`export LLVM_OBF_SEED="0xA04252B187478C00A40BC6D81D1A8A52"`

The environment variable `LLVM_OBF_DEBUG_SEED` can be set to "y" to print the
seed every time the plugin is loaded.

## Tests

The CTest suite builds small C fixtures, loads the plugin through both clang and
opt, verifies transformed IR, checks that each pass changes IR structure, and
executes an obfuscated binary to confirm runtime behavior is preserved.

## Acknowledgement

This project started from [`Obfuscator-LLVM`](https://github.com/obfuscator-llvm/obfuscator) by the information security group of the University of Applied Sciences and Arts Western Switzerland of Yverdon-les-Bains
([HEIG-VD](https://heig-vd.ch/international)).
