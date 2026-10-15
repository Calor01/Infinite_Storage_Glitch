# Seguridad — ISG Desktop 1.0.0

- La conversión y recuperación son locales; no hay funciones de red, autenticación ni descarga.
- FFmpeg/FFprobe restringen protocolos de entrada a `file,pipe`, pero los decodificadores de vídeo continúan procesando datos externos potencialmente maliciosos.
- Los MP4 no cifran los datos ni su nombre; SHA-256 comprueba integridad, no confidencialidad.
- Mantén al día FFmpeg y evita abrir vídeos de fuentes no confiables.
- No consideres un vídeo tu única copia de seguridad.
- Se preservan los resultados ya verificados y se evita sobrescribir destinos.
- Un sistema operativo puede conservar datos temporales, miniaturas y memoria de intercambio.

Para comunicar vulnerabilidades: utiliza el canal privado de avisos de seguridad de GitHub cuando esté habilitado.