# Validación de privacidad y compatibilidad — 1.0.0

- [x] No hay integraciones online en el código de la aplicación.
- [x] No existen API de guardado de preferencias, historial ni exportación de registros.
- [x] Limpieza de archivos XDG heredados con pruebas de regresión; borrado no forense.
- [x] Restricción de FFmpeg/FFprobe a protocolos de entrada locales.
- [x] Conversión local y recuperación SHA-256 comprobadas.
- [x] Eliminadas pestañas Ajustes y Diagnóstico, así como el botón de abrir la carpeta de resultados.
- [x] Reinicio automático de la configuración al terminar la creación, la recuperación y los lotes; comprobado también al fallar.
- [x] Recuperación de archivos tras renombrar el MP4, con integridad comprobada.
- [x] Mantener la verificación SHA-256 dentro del motor sin mencionarla en la interfaz.
- [x] Auditoría manual de dependencias: python3, python3-tk, ffmpeg (incluye ffprobe), tkdnd; suprimida sugerencia xdg-utils.
- [x] Formulario de arrastrar probado mediante listas Tcl para rutas con espacios y acentos.
- [ ] Arrastrar desde el gestor gráfico real con TkDND en varias versiones de Debian/Ubuntu.
- [ ] Ensayo completo de no-red con `strace -f -e trace=network` en todas las rutas de ejecución y distribuciones objetivo.
- [ ] Auditoría independiente del tratamiento de archivos temporales y borrado de rastros del sistema.
- [ ] Validación física de instalación, privacidad y arranque en Tails, sin alterar sus protecciones.

Las casillas pendientes **no se presentan como superadas**.