# Cambios

## 1.0.0 — Primera versión pública estable

Primera versión estable del nuevo ISG Desktop. Integra el motor local de conversión y recuperación, lotes, arrastrar y soltar, restablecimiento de parámetros, interfaz simplificada, iconos propios y barras de desplazamiento automáticas.

Las versiones 0.x y 1.1–1.4.3 fueron iteraciones de desarrollo anteriores a esta publicación; la numeración pública comienza en 1.0.0.

## 1.4.3 — Revisión de desarrollo (integrada en 1.0.0)

- Las pestañas solo muestran una barra vertical cuando su contenido excede la altura visible.
- Las listas de archivos de Lotes también ocultan sus barras cuando todos los elementos caben.
- Los campos, botones y el formato de los vídeos no cambian; se conserva la privacidad sin historial.

## 1.4.2 — Identidad gráfica y simplificación final

- Título de ventana fijo en «ISG Desktop», logo real aplicado a la ventana y al lanzador.
- Eliminada la cabecera en negrita y todas las menciones a extensiones de vídeo en la interfaz.
- Sin cambios en el formato, la recuperación, las funciones por lotes ni la privacidad.

## 1.4.1 — Interfaz simplificada

- Cabecera sustituida por «Convierte archivos en vídeos y recupéralos después.».
- Crear muestra solamente duración estimada del vídeo y tiempo de procesamiento orientativo durante la operación.
- Botón principal de creación renombrado a «Crear vídeo».
- Eliminados los textos de advertencia innecesarios de Recuperar y Lotes; mensajes breves y directos.
- Pestaña Información reducida a resolución, bloques y copias.
- Sin cambios en el formato de los vídeos, la recuperación, la integridad obligatoria ni la privacidad.

## 1.4.0 — Operaciones sin rastro de sesión en la interfaz

- Pestañas reducidas a Crear, Recuperar, Lotes e Información; sin Ajustes ni Diagnóstico.
- Eliminado el botón de abrir carpeta de resultado, junto a `xdg-utils` como dependencia sugerida.
- Integridad criptográfica obligatoria pero sin referencias técnicas en pantalla.
- Selecciones, rutas y parámetros restaurados automáticamente tras éxito, error o cancelación.
- Prueba de recuperación con MP4 renombrado; preservación de nombres originales.
- La aplicación sigue sin persistencia de historial ni preferencias.

## 1.3.0 — Arrastrar, mismos directorios, cero historial

- Arrastrar y soltar con la extensión local TkDND (`tkdnd`), y diálogos de siempre como alternativa.
- Carpetas de salida iguales a las carpetas de entrada por defecto, también para lotes mixtos.
- Guía en la pestaña Información; cabecera sin versión decorativa ni lema inferior.
- Elimina historial, opción de activarlo, guardado de configuraciones y exportación de registros.
- Elimina los antiguos archivos de preferencias e historial conocidos al iniciar (sin borrado forense).

## 1.2.0 — Offline

- Eliminados descargador YouTube, `yt-dlp`, proxy, permisos de red y ajustes asociados.
- FFmpeg y FFprobe restringidos a los protocolos de entrada locales.
- Conservado formato ISG-DESKTOP 2 y recuperación en lotes.
- Ajustes y documentación revisados para privacidad local.

# Historial de versiones

## 1.0.0 — 2026-10-11

- Recuperación **por lotes**, secuencial, con verificación individual SHA-256.
- Se mantienen los resultados correctos si otro archivo falla. Detección de entradas
  duplicadas y prohibición de sobrescribir salidas ya existentes.
- La cola ahora informa por elemento y sigue tras archivos dañados.
- Gestión de cancelación, progreso y resultados de recuperación integrada en la GUI.
- Nueva herramienta de terminal `isg-cli` para crear, recuperar, procesar lotes y estimar.
- Mejoras en rendimiento de renderizado mediante tabla precalculada.
- Registro gráfico limitado para evitar crecimiento indefinido de memoria.
- Validación reforzada de nombres de archivos restaurados.
- GitHub Actions arreglado y ampliado; pruebas y empaquetado reproducibles.
- El formato **ISG-DESKTOP 2 no cambia**; se conservan vídeos de las versiones 0.1–0.4.

## 0.4.0
- Creación de vídeos por lotes, historial local, preferencias persistentes,
  interfaz desplazable y medidas adicionales contra sobrescrituras.

## 0.3.0
- Mejoras de cancelación, integridad, publicación de archivos y diagnóstico.

## 0.2.0
- Paquete `.deb`, progreso y controles de operación.

## 0.1.0
- Primera interfaz y motor propio de codificación y recuperación.

## 1.1.0 — Compatibilidad Debian y controles de privacidad

- Sin persistencia automática en instalaciones nuevas (opt-in para preferencias e historial).
- Autorización de red obligatoria en cada sesión, con confirmación para conexión directa.
- Proxy SOCKS5h opcional, aislado de preferencias, sin credenciales en argumentos.
- yt-dlp ignora configuración del usuario, no usa caché propia ni registra salida bruta.
- Nombres descargados basados en identificador y controles de borrado de datos previos.
- Batería de pruebas de privacidad y política pública en PRIVACY.md.
- Paquete Debian sin scripts privilegiados; yt-dlp pasa de Recommends a Suggests.
