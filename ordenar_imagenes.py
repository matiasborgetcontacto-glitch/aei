#!/usr/bin/env python3
"""Ordena un conjunto de imagenes y las renombra con numeracion secuencial
con ceros a la izquierda, para que cualquier orden alfabetico posterior
(incluido el que usa Claude al leer una carpeta) coincida con el orden real.

Por defecto NO modifica los archivos originales: copia las imagenes ya
renombradas a una carpeta de salida y genera un manifiesto "orden.txt".

Ejemplos:
    python3 ordenar_imagenes.py ./fotos
    python3 ordenar_imagenes.py ./fotos --by date
    python3 ordenar_imagenes.py ./fotos --manifest orden_deseado.txt
    python3 ordenar_imagenes.py ./fotos --in-place
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff", ".heic",
}

_NUM_RE = re.compile(r"(\d+)")


def natural_sort_key(path: Path):
    parts = _NUM_RE.split(path.stem.lower())
    return [int(p) if p.isdigit() else p for p in parts]


def list_images(folder: Path):
    return [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]


def order_by_manifest(images, manifest_path: Path):
    wanted = [line.strip() for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_name = {p.name: p for p in images}

    ordered = []
    missing = []
    for name in wanted:
        if name in by_name:
            ordered.append(by_name.pop(name))
        else:
            missing.append(name)

    if missing:
        print(f"Aviso: {len(missing)} nombre(s) del manifiesto no se encontraron en la carpeta:", file=sys.stderr)
        for name in missing:
            print(f"  - {name}", file=sys.stderr)

    if by_name:
        print(f"Aviso: {len(by_name)} imagen(es) de la carpeta no estaban en el manifiesto; se agregan al final en orden natural:", file=sys.stderr)
        ordered.extend(sorted(by_name.values(), key=natural_sort_key))

    return ordered


def build_order(images, by: str, manifest: Path):
    if manifest is not None:
        return order_by_manifest(images, manifest)
    if by == "date":
        return sorted(images, key=lambda p: p.stat().st_mtime)
    return sorted(images, key=natural_sort_key)


def main():
    parser = argparse.ArgumentParser(description="Ordena y renombra imagenes de forma secuencial.")
    parser.add_argument("carpeta", type=Path, help="Carpeta que contiene las imagenes")
    parser.add_argument("--by", choices=["name", "date"], default="name",
                         help="Criterio de orden cuando no se pasa --manifest (default: name, orden natural)")
    parser.add_argument("--manifest", type=Path, default=None,
                         help="Archivo de texto con un nombre de imagen por linea, en el orden deseado")
    parser.add_argument("--prefix", default="img", help="Prefijo para los nombres nuevos (default: img)")
    parser.add_argument("--start", type=int, default=1, help="Numero inicial (default: 1)")
    parser.add_argument("--output", type=Path, default=None,
                         help="Carpeta de salida (default: '<carpeta>_ordenada')")
    parser.add_argument("--in-place", action="store_true",
                         help="Renombra los archivos originales en vez de copiarlos a una carpeta nueva")
    parser.add_argument("--dry-run", action="store_true", help="Muestra el resultado sin escribir nada en disco")
    args = parser.parse_args()

    if not args.carpeta.is_dir():
        parser.error(f"'{args.carpeta}' no es una carpeta valida")

    images = list_images(args.carpeta)
    if not images:
        print(f"No se encontraron imagenes en '{args.carpeta}'.", file=sys.stderr)
        sys.exit(1)

    ordered = build_order(images, args.by, args.manifest)
    width = max(len(str(args.start + len(ordered) - 1)), 2)

    output_dir = args.carpeta if args.in_place else (args.output or args.carpeta.with_name(args.carpeta.name + "_ordenada"))
    if not args.in_place and not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    plan = []
    manifest_lines = []
    for i, src in enumerate(ordered, start=args.start):
        new_name = f"{args.prefix}_{str(i).zfill(width)}{src.suffix.lower()}"
        plan.append((src, new_name))
        manifest_lines.append(new_name)
        print(f"{src.name}  ->  {new_name}")

    if not args.dry_run:
        if args.in_place:
            # Renombrar en dos pasadas via nombres temporales unicos para
            # evitar colisiones si un nombre nuevo coincide con uno original.
            temp_paths = []
            for idx, (src, _new_name) in enumerate(plan):
                tmp = src.with_name(f".tmp_{idx}_{src.name}")
                src.rename(tmp)
                temp_paths.append(tmp)
            for tmp, (_src, new_name) in zip(temp_paths, plan):
                tmp.rename(output_dir / new_name)
        else:
            for src, new_name in plan:
                shutil.copy2(src, output_dir / new_name)

    if not args.dry_run:
        (output_dir / "orden.txt").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
        print(f"\nListo. {len(ordered)} imagen(es) escritas en '{output_dir}'.")
        print(f"Manifiesto guardado en '{output_dir / 'orden.txt'}' (pegalo en tu prompt de Claude si queres reforzar el orden).")
    else:
        print("\n(dry-run: no se escribio ningun archivo)")


if __name__ == "__main__":
    main()
