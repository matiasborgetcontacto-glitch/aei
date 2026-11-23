# Guía de clips (TermoClips) — LEER ANTES DE CADA TANDA

Clipper de La Cobra (kick.com/lacobraaa), Davo Xeneize (kick.com/davooxeneize) y 412.
Responder siempre en español rioplatense.

## Contenido
- Clips de 20 a 40 s. Cortar siempre al final de una frase.
- Priorizar momentos graciosos y de acción, no solo charla ni solo GTA.
- No usar insultos en los títulos.
- Si se habla de un jugador, se puede mostrar su foto grande con su nombre (ej.: Montero).

## Formato del video (1080x1920)
- Recorte vertical de la cámara. **Nunca fondo borroso.**
- Dos personas: pantalla dividida en dos cuadrados (invitado arriba, streamer abajo) con una línea blanca en el medio.
- Pantalla o juego con cámara chica: contenido arriba y cámara abajo.
- **SIN SUBTÍTULOS.**
- **Logo de Kick** (`kick_logo.png`): arriba al centro (y=35), semitransparente, durante todo el clip.
- **Sonido de click** (`click.mp3`, doble click): suena al arrancar el clip, cuando entra el título.
- **Cartel del gancho** (`titulo_gancho.py`):
  - Caja blanca redondeada, texto en negro y la parte clave en rojo (entre *asteriscos*).
  - Montserrat ExtraBold 67, horizontal, máximo unas 3 líneas.
  - La caja va en y≈1104 (TY=1074).
  - Entra con un pop (0,25 s), queda hasta ~3,8 s y sale con distorsión de ondas (0,5 s).
  - No tiene que tapar caras.
- **Zoom fluido** (solo con cámara vertical; **en pantalla dividida NO hay zoom**): arranca acercándose (1,0 a 1,12 en 0,6 s) y cambia de plano suave (1,12 ↔ 1,24) al final de cada frase, cada 3,5 s como mínimo.

## Entrega
- Nombre del archivo: `N_nombre_TT-FB-YT.mp4`.
- Mandar el archivo y el link de CloudFront.
- Descripción en 3 bloques de código:
  1. Título con un emoji.
  2. Descripción para TT/FB + `#lacobra #davoxeneize #412 #futbol`.
  3. Descripción para YT de 100 caracteres o menos + `#shorts`.

## Técnica
- YouTube bloquea las descargas desde el servidor. Pedir el video por Google Drive con "Cualquier persona con el enlace" y bajarlo con `drive.usercontent.google.com/download?id=...&confirm=t`.
- El sandbox se borra a las 24 h sin uso. Los recursos (logo, click, scripts) se guardan en esta carpeta del repo.
- Script de efectos de referencia: `efectos_clip.py`. Agregarle el logo, el click y el cartel nuevo, y sacarle los subtítulos.

## Editor local (sin Higgsfield, para no pedir permisos)
- `clip.py words SRC.mp4 OUT.json` transcribe; `clip.py cut ...` corta; `clip.py fx NOMBRE 'TITULO *ROJO*' OUT.mp4 --crop W:H:X:Y` aplica todo (logo, click, cartel, zoom).
- Pantalla dividida: `--split TOPCROP BOTCROP` (sin zoom).
- Diseño libre (ej. juego con 2 cámaras: Davo arriba, tablero al medio, Cobra abajo): `--vf "split=3[x][y][z];..."` con alturas PARES (si no, ffmpeg se rompe). Foto de jugador: `--card img.png --card-at 4.3`.
- Kick: subtítulos automáticos en `.../media/hls/subtitles/es/playlist.m3u8` para leer el vivo; video en `.../media/hls/1080p60/N.ts` (segmentos de 10 s).
- Entregar solo con SendUserFile (sin links de CloudFront).

## Mejores momentos de 412 (video largo para YouTube)
- 412 es el programa (Davo, La Cobra, Teo, Agusneta, Benito y otros) en el vivo de Kick. Se hace el compilado al día siguiente.
- Referencia: "PERDÓN GENTE - MEJORES MOMENTOS DE 412" (Bombillo Clips, youtube 7U_If2O4vVs).
  - Horizontal 1920x1080, unos 12–15 min.
  - Momentos en orden cronológico, cortes secos.
  - Solo lo gracioso o caliente (la barra, las peleas, los chistes, las cargadas). Nada de charla larga.
- **Intro (cold open, unos 5–8 s):** el momento más picante del programa en blanco y negro, con una barra negra abajo y la frase clave en blanco, en mayúsculas y bold (ej.: "QUE SE VAYAN TODOS"). Después arranca el compilado en color.
- Miniatura: los protagonistas con la cara del momento (ej.: manos juntas pidiendo perdón) más el texto del gancho.
- Título: `GANCHO EN MAYÚSCULAS - MEJORES MOMENTOS DE 412`. Tags: 412, davoo xeneize, la cobraaa, mejores momentos 412.
- Durante el vivo: anotar los segmentos (índice N del .ts) de cada momento. Después: bajar 1080p, cortar y concatenar.
