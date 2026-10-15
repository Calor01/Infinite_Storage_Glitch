#!/usr/bin/env bash
# Auditoría local de baja intrusión. No sustituye una revisión de red de Tails.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests -p 'test_privacy.py' -v
if command -v strace >/dev/null 2>&1; then
  trace="$(mktemp)"
  trap 'rm -f "$trace"' EXIT
  echo 'Inspeccionando llamadas de red durante una conversión/recuperación real…'
  strace -f -e trace=network -o "$trace" python3 test_core.py
  if grep -E 'connect\(.*AF_INET6?|sendto\(.*AF_INET6?' "$trace"; then
    echo 'AVISO: se observaron llamadas de red. Revisión manual obligatoria.' >&2
    exit 2
  fi
  echo 'PASS: ninguna conexión AF_INET/AF_INET6 observada en esta ejecución.'
else
  echo 'NOT RUN: no está instalado strace; sin auditoría de syscalls de los subprocesos.'
  if [[ "${ISG_REQUIRE_STRACE:-0}" == "1" ]]; then
    echo 'FAIL: la auditoría exige strace.' >&2; exit 3
  fi
fi
