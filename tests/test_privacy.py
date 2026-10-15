"""Pruebas estáticas/dinámicas de privacidad; no equivalen a auditoría de Tails."""
from __future__ import annotations
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from isg_privacy import DEFAULTS, legacy_paths, cleanup_legacy_state
from isg_core import encode, decode


class PrivacyTests(unittest.TestCase):
    def test_private_defaults(self):
        self.assertFalse(DEFAULTS['restore_folder'])
        self.assertFalse(DEFAULTS['batch_folder'])

    def test_no_download_module_or_network_ui(self):
        import isg_gui
        self.assertFalse((Path(__file__).resolve().parent.parent / "isg_prefs.py").exists())
        self.assertFalse(hasattr(isg_gui.App, "_record_history"))
        self.assertFalse(hasattr(isg_gui.App, "_save_log"))
        self.assertFalse(hasattr(isg_gui.App, "_start_download"))

    def test_no_online_integrations_in_distributed_code(self):
        """Regresión: no volver a incluir APIs, descargadores ni proxies externos."""
        project = Path(__file__).resolve().parent.parent
        sources = [project / name for name in (
            "isg_core.py", "isg_gui.py", "isg_cli.py", "isg_batch.py", "isg_privacy.py",
            "packaging/build_deb.sh",
        )]
        forbidden = ("yt-dlp", "yt_dlp", "youtube", "youtu.be", "google", "proxy_url", "http://", "https://")
        for source in sources:
            code = source.read_text(encoding="utf-8").lower()
            for term in forbidden:
                with self.subTest(source=source.name, term=term):
                    self.assertNotIn(term, code)

    def test_network_playlist_disallowed_by_media_input_policy(self):
        # HLS local con dirección remota, usando extensión de vídeo aparente.
        # No hace una solicitud de red: los protocolos y formatos se limitan antes.
        from isg_core import ISGError, decode
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            disguised = root / "playlist.mp4"
            disguised.write_text("#EXTM3U\n#EXT-X-TARGETDURATION:3\n#EXTINF:3,\nhttp://127.0.0.1:8888/x.ts\n", encoding="utf-8")
            with self.assertRaises(ISGError):
                decode(str(disguised), d)

    def test_legacy_files_are_deleted_without_new_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {'XDG_CONFIG_HOME': folder + '/config',
                                         'XDG_STATE_HOME': folder + '/state'}):
                paths = legacy_paths()
                for path in paths:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text('legacy sensitive path')
                cleanup_legacy_state()
                self.assertTrue(all(not path.exists() for path in paths))
                self.assertTrue(all(not path.exists() for path in paths))

    def test_local_roundtrip_does_not_call_python_socket_connect(self):
        # Esta prueba NO intercepta syscalls de FFmpeg: requieren una prueba aparte.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            src = root / 'sensitive.txt'; src.write_bytes(os.urandom(127))
            video = root / 'output.mp4'; restored = root / 'restored'; restored.mkdir()
            with patch.object(socket.socket, 'connect', side_effect=AssertionError('network')):
                encode(str(src), str(video), block=12, copies=1)
                decode(str(video), str(restored))
            self.assertEqual((restored / src.name).read_bytes(), src.read_bytes())


if __name__ == '__main__':
    unittest.main()
