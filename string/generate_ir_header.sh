#!/usr/bin/env bash
set -euo pipefail

CC=${1}
XXD=${2}
INPUT_FILE=${3}
OUTPUT_DIR=${4}
OUTPUT_FILENAME=${5}

if command -v cygpath >/dev/null 2>&1; then
  INPUT_FILE="$(cygpath -u "${INPUT_FILE}")"
  OUTPUT_DIR="$(cygpath -u "${OUTPUT_DIR}")"
fi
BC_FILENAME="$(basename "${INPUT_FILE}").bc"

mkdir -p "${OUTPUT_DIR}"
cd "${OUTPUT_DIR}"
EXTRA_FLAGS=()
if [[ "$(uname -s)" == "Darwin" ]]; then
  SDK_PATH="$(xcrun --show-sdk-path)"
  EXTRA_FLAGS+=("-isysroot" "${SDK_PATH}")
fi
"${CC}" -Os -emit-llvm "${EXTRA_FLAGS[@]}" -c "${INPUT_FILE}" -o "${BC_FILENAME}"
"${XXD}" -i "${BC_FILENAME}" > "${OUTPUT_FILENAME}"
