# ISG Desktop 1.0.0

Conversor **100 % local** de archivos ↔ vídeos MP4 para Debian y derivados. Esta implementación es independiente y está inspirada en el proyecto de [KKarmugil](https://github.com/KKarmugil/Infinite_Storage_Glitch). El formato ISG-DESKTOP 2 es compatible con los vídeos generados por ISG Desktop 0.1–1.3, pero **no** con los del programa de 2024.

**Sin descargas de Internet ni Google, sin cuentas, telemetría, historial, registro exportable ni ajustes persistentes.** La interfaz solo muestra el estado de la operación actual. El menú y la barra de tareas identifican la ventana como **ISG Desktop** y muestran su logotipo propio. La aplicación intenta borrar automáticamente los antiguos `settings.json` e `history.json` que pudieran dejar versiones previas: no supone eliminación forense ni borra registros independientes generados por el sistema operativo.

> **Importante:** el vídeo generado **no está cifrado** y contiene los datos y el nombre del archivo original. No está garantizado que resista recomprensiones o servicios de vídeo externos. No sustituye a una copia de seguridad.

## Funciones

- Crear vídeo de cualquier archivo local y recuperar el original con SHA-256.
- Selección con diálogo o **arrastrar y soltar** (depende del paquete `tkdnd` del sistema; no descarga bibliotecas por su cuenta).
- **Guardar por defecto en la misma carpeta que el archivo original**; para vídeos recuperados, por defecto junto al vídeo de entrada. Las carpetas de los lotes pueden ser diferentes para cada entrada.
- Resoluciones 1280×720 y 1920×1080; bloques de 8/12/16 píxeles; 1/2/3 copias. La pestaña **Información** resume las diferencias entre los parámetros.
- Conversión y recuperación por lotes, barra de progreso, cancelación y detección de colisiones, sin botón de abrir carpeta de resultado.
- Sin guardado de preferencias ni registro de operaciones, **sin opción para activarlos**. Los parámetros, rutas y selecciones se borran de la interfaz y se restablecen al terminar cada tarea, incluso si falla o se cancela; un lote completo cuenta como una tarea.
- Se puede **cambiar el nombre del MP4**: la recuperación utiliza el nombre original guardado dentro del vídeo, que se restaura si supera la comprobación interna de integridad.
- Herramienta CLI opcional `isg-cli` para automatización por cuenta del usuario; el shell, los administradores de archivos y el sistema operativo pueden almacenar sus propios rastros.

## Instalar en Debian o Ubuntu

```bash
sudo apt install ./isg-desktop_1.0.0_all.deb
```

El paquete declara únicamente `python3`, `python3-tk`, `ffmpeg` (que también aporta `ffprobe`) y `tkdnd` como dependencias imprescindibles. La antigua sugerencia `xdg-utils` se ha eliminado junto al botón de abrir carpetas. Instálalo con APT para que las resuelva (podría necesitar conexión para la **instalación**, no para ejecutar ISG Desktop). La extensión de arrastrar y soltar utiliza TkDND local; en una ejecución desde el código sin `tkdnd`, el resto de funciones funcionan mediante botones **Examinar**.

Abre desde el menú gráfico o con `isg-desktop`. Desde el código fuente: `bash lanzar.sh`.

## Uso

Las barras verticales de las pestañas y de las listas aparecen únicamente cuando hay contenido que no cabe en el espacio disponible.


1. **Crear:** arrastra un archivo o usa Examinar. El vídeo propuesto queda junto al original; puedes cambiarlo manualmente. Se muestra la duración estimada del vídeo y, durante la creación, una estimación del tiempo de procesamiento basada en el progreso real.
2. **Recuperar:** arrastra el vídeo o selecciónalo. La carpeta propuesta es la del vídeo; puedes cambiarla.
3. **Lotes:** arrastra varios archivos a la zona superior para crear vídeos o vídeos a la zona inferior para recuperar. **Deja vacía la carpeta de destino** para guardar cada salida junto a su correspondiente entrada.
4. **Información:** consulta la explicación breve de resolución, tamaño de bloque y número de copias.

Al completar una operación —con éxito, fallo o cancelación—, la interfaz borra las selecciones y vuelve a los parámetros predeterminados. En los lotes, se espera a terminar el lote entero.

**Nunca sobrescribe archivos existentes.** Los archivos temporales usados durante operaciones se eliminan al terminar o cancelar en condiciones normales; los sistemas de archivos, backups, snapshots o swap están fuera del control del programa.

## CLI

```bash
isg-cli create archivo.zip archivo.zip.mp4
isg-cli recover archivo.zip.mp4 ./recuperados
isg-cli batch-create ./videos uno.pdf dos.zip
isg-cli batch-recover ./recuperados ./videos/uno.pdf.mp4
```

## Pruebas

```bash
python3 -m unittest discover -s tests -v
python3 test_core.py
python3 qa_variants.py
xvfb-run -a python3 tests/test_gui_smoke.py
xvfb-run -a python3 tests/test_gui_scrollbars.py
xvfb-run -a python3 tests/test_gui_privacy.py
xvfb-run -a python3 tests/test_gui_drop.py
xvfb-run -a python3 tests/test_gui_default_output.py
xvfb-run -a python3 tests/test_gui_batch_integration.py
xvfb-run -a python3 tests/test_gui_recovery_batch.py
xvfb-run -a python3 tests/test_gui_reset_and_rename.py
xvfb-run -a python3 tests/test_gui_copy.py
bash scripts/privacy-check.sh
```

**Privacidad:** el programa no escribe historial ni preferencias y elimina sus temporales en condiciones normales, pero el sistema operativo, el entorno de escritorio, el gestor de archivos, el swap y los snapshots pueden conservar rastros; no se garantiza un borrado forense.

**Limitación:** las pruebas automáticas de arrastrar y soltar verifican el manejo de listas Tcl y los destinos; debe comprobarse una acción real desde el explorador con `tkdnd` instalado en Debian/Ubuntu. El bloqueo de conexiones del sistema operativo y la integración en Tails **requieren validación específica**, no existe certificación oficial de Tails. Consulta `PRIVACY.md` y `PRIVACY_VALIDATION.md`.

## Licencia y procedencia

El fork de [Calor01/Infinite_Storage_Glitch](https://github.com/Calor01/Infinite_Storage_Glitch) conserva el historial y la licencia MIT de karmugil. Esta distribución incluye el aviso de copyright original. El paquete no incorpora servicios ni scripts de instalación con privilegios.