# ordenar_imagenes.py

Script para ordenar y renombrar imagenes de forma secuencial (con ceros a la
izquierda), asi el orden alfabetico de los archivos coincide con el orden que
queres. Util cuando le pasas imagenes a Claude (u otra herramienta) y termina
procesandolas en un orden distinto al esperado.

Por defecto **no toca los archivos originales**: copia las imagenes ya
renombradas a una carpeta nueva y genera un `orden.txt` con el resultado.

## Uso

```bash
# Orden natural por nombre (imagen1, imagen2, ..., imagen10, ...)
python3 ordenar_imagenes.py ./fotos

# Orden por fecha de modificacion
python3 ordenar_imagenes.py ./fotos --by date

# Orden segun una lista propia (un nombre de archivo por linea)
python3 ordenar_imagenes.py ./fotos --manifest orden_deseado.txt

# Ver que haria sin escribir nada
python3 ordenar_imagenes.py ./fotos --dry-run

# Renombrar los archivos originales en vez de copiarlos a una carpeta nueva
python3 ordenar_imagenes.py ./fotos --in-place
```

Otras opciones: `--prefix` (prefijo de los nombres nuevos, default `img`),
`--start` (numero inicial, default `1`), `--output` (carpeta de salida
personalizada).

El `orden.txt` generado se puede pegar en el prompt de Claude para reforzar
el orden exacto en el que debe usar las imagenes.
