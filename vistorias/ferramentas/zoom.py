"""Zoom em fotos específicas, várias de uma vez, numa única imagem.

Uso: python3 zoom.py <vis> <idx_comodo> <ref> [<ref> ...]
  ref = n:k     -> foto k do item n do cômodo (como no rótulo do painel: "n.Item fk")
        a:k     -> foto k do próprio cômodo ("amb fk")
        n:vK:T  -> quadro do vídeo K do item n no segundo T (rótulo "n.Item vK Ts"); a:vK:T para vídeo do cômodo
        n:k@x0,y0,x1,y1 -> recorte (frações 0-1 da foto), ex.: 4:23@0.5,0.5,1,1 = quarto inferior direito
Baixa a foto original (com cache), monta grades 2x2 de ~750 px por foto e imprime os arquivos gerados.
Leia todos os arquivos impressos de uma vez (uma rodada).
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pleno  # noqa: E402


def main():
    vis, idx, refs = sys.argv[1], sys.argv[2], sys.argv[3:]
    pasta = pleno.pasta_vis(vis)
    urls = json.loads((pasta / 'fotos.json').read_text())
    full, zdir = pasta / 'full', pasta / 'zoom'
    full.mkdir(exist_ok=True)
    zdir.mkdir(exist_ok=True)
    prontos = []
    vdir = pasta / 'videos'
    vdir.mkdir(exist_ok=True)
    for ref in refs:
        base, _, rec = ref.partition('@')
        partes = base.split(':')
        n, k = partes[0], partes[1]
        url = urls.get(f'{idx}:{n}:{k}')
        if not url:
            print('referência inexistente:', ref)
            continue
        if k.startswith('v'):  # quadro de vídeo: n:vK:SEGUNDOS
            t = partes[2] if len(partes) > 2 else '1'
            vid = vdir / f"{idx}_{n if n != 'a' else 'a'}_{k}.mp4"
            if not vid.exists() or vid.stat().st_size < 1000:
                subprocess.run(['curl', '-sS', '--max-time', '240', '-o', str(vid), url.split('?')[0]], check=True)
            orig = full / f'{idx}_{n}_{k}_{t}s.jpg'
            if not orig.exists():
                subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', t, '-i', str(vid), '-frames:v', '1', '-y', str(orig)], check=True)
            k = f'{k} {t}s'
        else:
            orig = full / f'{idx}_{n}_{k}.jpg'
            if not orig.exists() or orig.stat().st_size < 1000:
                subprocess.run(['curl', '-sS', '--max-time', '90', '-o', str(orig), url], check=True)
        out = zdir / f"{idx}_{n}_{k.replace(' ', '_')}{'_r' + rec.replace(',', '-') if rec else ''}.jpg"
        cmd = ['convert', str(orig), '-auto-orient']
        if rec:
            x0, y0, x1, y1 = [float(v) for v in rec.split(',')]
            w, h = [int(v) for v in subprocess.run(['identify', '-format', '%w %h', str(orig)], capture_output=True, text=True).stdout.split()]
            cmd += ['-crop', f'{int((x1 - x0) * w)}x{int((y1 - y0) * h)}+{int(x0 * w)}+{int(y0 * h)}', '+repage']
        cmd += ['-resize', '750x750', str(out)]
        subprocess.run(cmd, check=True)
        prontos.append((str(out), f"{n if n != 'a' else 'amb'} {k if k.startswith('v') else 'f' + k}{' recorte' if rec else ''}"))
    arquivos = []
    for p in range(0, len(prontos), 4):
        grupo = prontos[p:p + 4]
        saida = zdir / f"grade_{idx}_{'_'.join(os.path.basename(f)[:-4] for f, _ in grupo)[:80]}.jpg"
        args = ['montage']
        for f, r in grupo:
            args += ['-label', r, f]
        subprocess.run(args + ['-tile', '2x', '-geometry', '750x750+4+4', '-pointsize', '18', '-background', 'white', str(saida)], check=True)
        arquivos.append(str(saida))
    print('\n'.join(arquivos))


if __name__ == '__main__':
    main()
