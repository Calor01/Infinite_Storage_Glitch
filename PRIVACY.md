# Privacidad — ISG Desktop 1.0.0

- Toda la transformación de los datos es local. No se incluyen funciones para servicios de red ni credenciales, autenticación, descargas, telemetría o actualizaciones automáticas.
- No hay pestaña de historial, opciones para activarlo, exportación de registros, configuración persistente ni código que escriba archivos de estado. Los campos y la barra de progreso contienen datos transitorios en memoria durante la operación. Al concluir cualquier tarea, incluida una fallida o cancelada, se borran las rutas y selecciones de los formularios y se restablecen resolución, bloque y copias; en lotes esto sucede al terminar la cola.
- Al iniciar, se intentan eliminar los archivos conocidos de versiones antiguas de la misma aplicación (`settings.json` y `history.json`) bajo las rutas XDG. Si no hay permisos, pueden permanecer; no se garantiza borrado forense.
- Se crean **los archivos de salida solicitados y archivos temporales de procesamiento**; también podrían existir cachés, swap, diarios del sistema de archivos o snapshots del sistema operativo fuera de nuestro control. El explorador de archivos, la terminal y los gestores de paquetes pueden mantener su propio historial.
- El vídeo no cifra el archivo ni su nombre. No publiques vídeos que contengan datos privados sin cifrarlos previamente mediante una herramienta adecuada.
- FFmpeg y FFprobe están limitados a protocolos `file,pipe` en la entrada y a demultiplexores compatibles. Un archivo multimedia malicioso puede aprovechar vulnerabilidades de bibliotecas de medios; mantén FFmpeg actualizado.
- El borrado de los campos de la interfaz no puede asegurar que el gestor de ventanas, el selector de ficheros, el swap o el sistema operativo no conserven información. No debe considerarse un borrado seguro de memoria.
- La función de arrastrar utiliza la extensión local `tkdnd` proporcionada por el gestor de paquetes. No descarga bibliotecas ni incluye componentes compilados dentro de la aplicación.
- El `.deb` solo instala archivos de la aplicación; no contiene scripts privilegiados, demonios ni manipula cortafuegos, DNS o Tor.
- **Las pruebas de privacidad documentadas no equivalen a una auditoría independiente ni a una aprobación por Tails.**
