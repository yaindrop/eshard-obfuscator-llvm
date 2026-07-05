#!/usr/bin/env python3
import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


FIXTURE = r"""
__attribute__((noinline)) int calc(int x) {
  int y = x + 7;
  y = (y ^ 0x55) + (x & 3);
  y = y - (x | 9);
  return y ^ (x + 11);
}

__attribute__((noinline)) int branchy(int x) {
  if ((x % 3) == 0) {
    return x * 2 + 1;
  }
  if ((x & 1) != 0) {
    return x - 5;
  }
  return x + 13;
}

__attribute__((noinline)) int phrase_score(void) {
  const char *s = "FLOWBIT_SECRET_427";
  int total = 0;
  for (int i = 0; s[i] != 0; ++i) {
    total += s[i] * (i + 1);
  }
  return total;
}

int main(void) {
  int total = phrase_score();
  for (int i = 0; i < 16; ++i) {
    total += calc(i) + branchy(i);
  }
  return total == 13542 ? 0 : 1;
}
"""


def run(args, *, env=None, cwd=None):
  completed = subprocess.run(
      args,
      cwd=cwd,
      env=env,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True,
  )
  if completed.returncode != 0:
    print("$ " + " ".join(map(str, args)))
    if completed.stdout:
      print(completed.stdout)
    if completed.stderr:
      print(completed.stderr, file=sys.stderr)
    raise SystemExit(completed.returncode)
  return completed


def require_tool(path):
  resolved = shutil.which(str(path)) if not Path(path).is_absolute() else str(path)
  if resolved is None or not Path(resolved).exists():
    raise SystemExit(f"required tool not found: {path}")
  return Path(resolved)


def count_basic_blocks(ir_text):
  return sum(
      1
      for line in ir_text.splitlines()
      if re.match(r"^\s*[-a-zA-Z$._0-9]+:\s*(?:;.*)?$", line)
  )


def count_instruction(ir_text, opcode):
  needle = f" {opcode} "
  return sum(1 for line in ir_text.splitlines() if needle in line)


def assert_changed(label, before, after):
  if before == after:
    raise SystemExit(f"{label}: pass did not change IR")


def verify_ir(opt, ir_path):
  run([opt, "-S", "-passes=verify", ir_path, "-o", os.devnull])


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--plugin", required=True)
  parser.add_argument("--llvm-bin", required=True)
  parser.add_argument("--filecheck", required=False)
  args = parser.parse_args()

  plugin = Path(args.plugin).resolve()
  llvm_bin = Path(args.llvm_bin).resolve()
  clang = require_tool(llvm_bin / "clang")
  opt = require_tool(llvm_bin / "opt")
  if args.filecheck:
    require_tool(args.filecheck)
  if not plugin.exists():
    raise SystemExit(f"plugin not found: {plugin}")

  env = os.environ.copy()
  env["LLVM_OBF_SEED"] = "0xA04252B187478C00A40BC6D81D1A8A52"

  with tempfile.TemporaryDirectory(prefix="llvm-obf-test-") as temp_dir:
    temp = Path(temp_dir)
    source = temp / "fixture.c"
    source.write_text(FIXTURE)

    baseline = temp / "baseline"
    obfuscated = temp / "obfuscated"
    if platform.system() == "Windows":
      baseline = baseline.with_suffix(".exe")
      obfuscated = obfuscated.with_suffix(".exe")

    run([clang, "-O1", source, "-o", baseline])
    run([baseline])

    obf_env = env.copy()
    obf_env["LLVM_OBF_SCALAROPTIMIZERLATE_PASSES"] = (
        "flattening,bogus,substitution,split-basic-blocks"
    )
    obf_env["LLVM_OBF_OPTIMIZERLASTEP_PASSES"] = "string-encryption"
    run([clang, "-O1", f"-fpass-plugin={plugin}", source, "-o", obfuscated],
        env=obf_env)
    run([obfuscated])

    input_ir = temp / "input.ll"
    run([clang, "-O1", "-S", "-emit-llvm", source, "-o", input_ir])
    input_text = input_ir.read_text()
    verify_ir(opt, input_ir)

    pass_cases = [
        ("substitution", "substitution", lambda before, after:
         count_instruction(after, "xor") >= count_instruction(before, "xor")),
        ("split-basic-blocks", "split-basic-blocks", lambda before, after:
         count_basic_blocks(after) > count_basic_blocks(before)),
        ("flattening", "flattening", lambda before, after: " switch " in after),
        ("bogus", "bogus", lambda before, after:
         count_basic_blocks(after) > count_basic_blocks(before)),
    ]

    for name, passes, predicate in pass_cases:
      output_ir = temp / f"{name}.ll"
      run([opt, "-S", f"-load-pass-plugin={plugin}", f"-passes={passes}",
           input_ir, "-o", output_ir], env=env)
      output_text = output_ir.read_text()
      verify_ir(opt, output_ir)
      assert_changed(name, input_text, output_text)
      if not predicate(input_text, output_text):
        raise SystemExit(f"{name}: structural check failed")

    string_ir = temp / "string-encryption.ll"
    run([opt, "-S", f"-load-pass-plugin={plugin}", "-passes=string-encryption",
         input_ir, "-o", string_ir], env=env)
    string_text = string_ir.read_text()
    verify_ir(opt, string_ir)
    assert_changed("string-encryption", input_text, string_text)
    if "FLOWBIT_SECRET_427" in string_text:
      raise SystemExit("string-encryption: plaintext string is still present")

  print("llvm22 smoke tests passed")


if __name__ == "__main__":
  main()
