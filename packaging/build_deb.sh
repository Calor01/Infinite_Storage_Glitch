#!/usr/bin/env bash
# Construye un paquete Debian binario sin instalar nada en el sistema anfitrión.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
version="$(sed -nE 's/^VERSION = "([^"]+)"/\1/p' "$root/isg_core.py" | head -n 1)"
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo 'Error: versión inválida.' >&2; exit 1
fi
command -v dpkg-deb >/dev/null 2>&1 || { echo 'Instala dpkg-deb.' >&2; exit 1; }
out="${1:-$root/dist}"
mkdir -p "$out"
out="$(cd "$out" && pwd)"
staging="$(mktemp -d)"
chmod 0755 "$staging"
trap 'rm -rf -- "$staging"' EXIT
app="$staging/usr/share/isg-desktop"
mkdir -p "$app" "$staging/DEBIAN" "$staging/usr/bin" \
  "$staging/usr/share/applications" "$staging/usr/share/icons/hicolor/scalable/apps" \
  "$staging/usr/share/icons/hicolor/128x128/apps" "$staging/usr/share/icons/hicolor/64x64/apps" \
  "$staging/usr/share/doc/isg-desktop"
install -m 0644 "$root/isg_core.py" "$root/isg_gui.py" "$root/isg_cli.py" \
  "$root/isg_privacy.py" "$root/isg_batch.py" "$app/"
install -m 0644 "$root/packaging/isg-desktop.desktop" "$staging/usr/share/applications/"
install -m 0644 "$root/assets/isg-desktop.svg" "$staging/usr/share/icons/hicolor/scalable/apps/"
mkdir -p "$app/assets"
for size in 32 64 128; do
  install -m 0644 "$root/assets/isg-desktop-${size}.png" "$app/assets/"
done
install -m 0644 "$root/assets/isg-desktop-128.png" "$staging/usr/share/icons/hicolor/128x128/apps/isg-desktop.png"
install -m 0644 "$root/assets/isg-desktop-64.png" "$staging/usr/share/icons/hicolor/64x64/apps/isg-desktop.png"
install -m 0644 "$root/LICENSE" "$staging/usr/share/doc/isg-desktop/copyright"
install -m 0644 "$root/README.md" "$root/CHANGELOG.md" "$root/PRIVACY.md" "$root/PRIVACY_VALIDATION.md" "$root/SECURITY.md" "$staging/usr/share/doc/isg-desktop/"
cat > "$staging/usr/bin/isg-desktop" <<'SCRIPT'
#!/bin/sh
exec /usr/bin/python3 -B /usr/share/isg-desktop/isg_gui.py "$@"
SCRIPT
cat > "$staging/usr/bin/isg-cli" <<'SCRIPT'
#!/bin/sh
exec /usr/bin/python3 -B /usr/share/isg-desktop/isg_cli.py "$@"
SCRIPT
chmod 0755 "$staging/usr/bin/isg-desktop" "$staging/usr/bin/isg-cli"
maintainer="${ISG_MAINTAINER:-ISG Desktop Contributors <maintainer@example.invalid>}"
cat > "$staging/DEBIAN/control" <<CONTROL
Package: isg-desktop
Version: $version
Section: utils
Priority: optional
Architecture: all
Maintainer: $maintainer
Depends: python3 (>= 3.10), python3-tk, ffmpeg, tkdnd
Description: Convertir archivos en vídeos y recuperar su contenido
 Aplicación gráfica Python/Tkinter con creación y recuperación por lotes.
 Funciona sin conexión a Internet y no incluye integraciones de red.
 Los vídeos no cifran los datos; una transcodificación externa puede
 inutilizarlos. No sustituye a las copias de seguridad.
CONTROL
# Facilita construir paquetes reproducibles con SOURCE_DATE_EPOCH.
if [[ -n "${SOURCE_DATE_EPOCH:-}" ]]; then
  find "$staging" -print0 | xargs -0 touch -h -d "@$SOURCE_DATE_EPOCH"
fi
dpkg-deb --build --root-owner-group "$staging" "$out/isg-desktop_${version}_all.deb"
echo "Paquete creado: $out/isg-desktop_${version}_all.deb"
