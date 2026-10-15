# Contribuir

ISG Desktop está escrito en Python (biblioteca estándar), Tkinter y FFmpeg.

1. Abre una incidencia describiendo el problema, versión de Ubuntu/Debian,
   versión de FFmpeg y pasos para reproducirlo. Nunca adjuntes archivos privados
   ni vídeos que contengan datos confidenciales.
2. Haz una rama de Git y cambia el código manteniendo compatibilidad con
   `ISG-DESKTOP 2` o documentando expresamente un formato nuevo.
3. Pasa los comandos de pruebas de README antes de abrir un pull request.
4. Incluye pruebas automatizadas para cada corrección importante.
5. No añadas llamadas a red ocultas, telemetría ni la carga de URLs ajenas sin
   permiso del usuario.

Antes de publicar un `.deb`, sustituye el identificador de mantenimiento por
una dirección propia usando `ISG_MAINTAINER='Nombre <correo@dominio>'`.

El software se distribuye con licencia MIT. Esta es una implementación
independiente inspirada en `KKarmugil/Infinite_Storage_Glitch`.
