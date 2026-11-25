#!/bin/sh
set -eu
TASK_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TASK_UV_DIR="$TASK_ROOT/.tools/uv"
TASK_UV="$TASK_UV_DIR/uv"
if [ ! -x "$TASK_UV" ]; then
    mkdir -p "$TASK_UV_DIR"
    case "$(uname -m)" in arm64|aarch64) TASK_ARCH=aarch64 ;; x86_64|amd64) TASK_ARCH=x86_64 ;; *) echo 'Arquitectura no compatible.'; exit 1 ;; esac
    case "$(uname -s)" in Darwin) TASK_PLATFORM=apple-darwin ;; Linux) TASK_PLATFORM=unknown-linux-gnu ;; *) echo 'Usa iniciar.cmd en Windows.'; exit 1 ;; esac
    TASK_NAME="uv-$TASK_ARCH-$TASK_PLATFORM.tar.gz"
    TASK_URL="https://github.com/astral-sh/uv/releases/download/0.13.9/$TASK_NAME"
    curl --fail --location "$TASK_URL" --output "$TASK_UV_DIR/$TASK_NAME"
    curl --fail --location "$TASK_URL.sha256" --output "$TASK_UV_DIR/$TASK_NAME.sha256"
    TASK_EXPECTED=$(awk '{print $1}' "$TASK_UV_DIR/$TASK_NAME.sha256")
    if command -v sha256sum >/dev/null 2>&1; then
        TASK_ACTUAL=$(sha256sum "$TASK_UV_DIR/$TASK_NAME" | awk '{print $1}')
    else
        TASK_ACTUAL=$(shasum -a 256 "$TASK_UV_DIR/$TASK_NAME" | awk '{print $1}')
    fi
    [ "$TASK_EXPECTED" = "$TASK_ACTUAL" ] || { echo 'Checksum de uv incorrecto.'; exit 1; }
    tar -xzf "$TASK_UV_DIR/$TASK_NAME" -C "$TASK_UV_DIR"
    cp "$TASK_UV_DIR/uv-$TASK_ARCH-$TASK_PLATFORM/uv" "$TASK_UV"
    chmod +x "$TASK_UV"
fi
cd "$TASK_ROOT"
if [ "$#" -eq 0 ]; then set -- iniciar; fi
exec "$TASK_UV" run --python 3.11 --extra mcp herramientas/entorno.py "$@"
