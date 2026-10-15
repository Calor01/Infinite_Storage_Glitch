from pathlib import Path
import os, subprocess, tempfile
from isg_core import encode, decode, ISGError
with tempfile.TemporaryDirectory() as d:
    p = Path(d)
    data = os.urandom(9000)
    src = p/'prueba-variantes.bin'; src.write_bytes(data)
    for w,h in [(1280,720),(1920,1080)]:
        for block in (8,12,16):
            out = p/f'v-{w}-{block}.mp4'
            encode(str(src),str(out),w,h,block,1)
            rdir = p/f'r-{w}-{block}'; rdir.mkdir()
            target=decode(str(out),str(rdir))
            assert target.read_bytes() == data
            print('PASS',w,h,block, flush=True)
    base = p/'ytinput.mp4'
    encode(str(src),str(base),1280,720,8,2)
    transcoded = p/'yt-transcode.mp4'
    proc = subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(base),'-c:v','libx264','-crf','28','-preset','veryfast','-pix_fmt','yuv420p',str(transcoded)],capture_output=True)
    assert proc.returncode==0, proc.stderr
    rdir=p/'r-transcoded';rdir.mkdir()
    restored=decode(str(transcoded),str(rdir))
    assert restored.read_bytes() == data
    print('PASS transcodificación H.264 CRF28 (simulación local)', flush=True)
    try:
        decode(str(base),str(rdir))
    except ISGError as e:
        assert 'ya existe' in str(e), str(e)
        print('PASS no sobrescribe',flush=True)
    else: raise AssertionError('Sobrescrito')
print('TODOS LOS ENSAYOS HAN PASADO')
