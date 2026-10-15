#!/usr/bin/env python3
"""Interfaz de comandos auxiliar para automatización y verificaciones de ISG Desktop."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import threading
import time

from isg_core import VERSION, ISGError, encode, decode, estimate_encode
from isg_privacy import cleanup_legacy_state
from isg_batch import (prepare_jobs, prepare_decode_jobs,
                       execute_jobs, execute_decode_jobs)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="isg-cli", description="Conversión local ISG Desktop")
    p.add_argument('--version', action='version', version=f'ISG Desktop {VERSION}')
    sub = p.add_subparsers(dest='command', required=True)
    e = sub.add_parser('create', help='Crear un vídeo desde un archivo')
    e.add_argument('source'); e.add_argument('output')
    b = sub.add_parser('batch-create', help='Crear varios vídeos de forma secuencial')
    b.add_argument('output_folder'); b.add_argument('sources', nargs='+')
    d = sub.add_parser('recover', help='Recuperar archivo comprobando su integridad')
    d.add_argument('video'); d.add_argument('output_folder')
    bd = sub.add_parser('batch-recover', help='Recuperar varios vídeos')
    bd.add_argument('output_folder'); bd.add_argument('videos', nargs='+')
    info = sub.add_parser('estimate', help='Estimar duración de vídeo sin crear el vídeo')
    info.add_argument('source')
    for cmd in (e, b, info):
        cmd.add_argument('--resolution', choices=['1280x720','1920x1080'], default='1280x720')
        cmd.add_argument('--block', type=int, choices=[8,12,16], default=8)
        cmd.add_argument('--copies', type=int, choices=[1,2,3], default=2)
    return p


def main(argv=None) -> int:
    cleanup_legacy_state()
    args = parser().parse_args(argv)
    cancel = threading.Event()
    recent = [0.0]

    def progress(value, message):
        now = time.monotonic()
        if now - recent[0] > 0.4 or value == 1:
            recent[0] = now
            print(f'{value*100:5.1f}% · {message}', file=sys.stderr, flush=True)

    def done(source, target, ok, detail):
        print(f'{"OK" if ok else "ERROR"}: {Path(source).name} -> {Path(target).name}: {detail}',
              file=sys.stderr, flush=True)

    try:
        if args.command in ('create','batch-create','estimate'):
            width, height = map(int, args.resolution.split('x'))
        if args.command == 'estimate':
            print(json.dumps(estimate_encode(args.source, width, height, args.block, args.copies),
                             indent=2, ensure_ascii=False))
        elif args.command == 'create':
            print(encode(args.source, args.output, width, height, args.block, args.copies,
                         cancel, progress))
        elif args.command == 'recover':
            print(decode(args.video, args.output_folder, cancel, progress))
        elif args.command == 'batch-create':
            report = execute_jobs(prepare_jobs(args.sources, args.output_folder),
                width=width, height=height, block=args.block, copies=args.copies,
                cancel=cancel, progress=progress, item_done=done)
            print(json.dumps(report, ensure_ascii=False))
            return 0 if report['failed'] == 0 else 2
        elif args.command == 'batch-recover':
            report = execute_decode_jobs(prepare_decode_jobs(args.videos, args.output_folder),
                cancel=cancel, progress=progress, item_done=done)
            print(json.dumps(report, ensure_ascii=False))
            return 0 if report['failed'] == 0 else 2
        return 0
    except (ISGError, OSError, ValueError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        cancel.set()
        print('Cancelado.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
