"""Prepara uma vistoria para o preenchimento por cômodo (somente leitura no sistema).

Uso: python3 preparar.py <vis_codigo> [--todos] [--comodos 1,2,5]

1. Lê a vistoria pela API (texto) e separa, em cada cômodo, os itens ainda SEM preenchimento
   (itens que já têm algum detalhe preenchido são pulados; --todos inclui todos).
2. Classifica cada item pendente em 'padrao' (modelo leve) ou 'atencao' (modelo forte).
3. Baixa só as miniaturas necessárias e monta painéis densos:
   - padrao:  até 3 fotos espalhadas por item, 30 por painel;
   - atencao: todas as fotos do item (até 30 por painel); itens com mais de 30 fotos viram
              mosaico de 48 miniaturas menores por painel (cobre tudo; o zoom vem depois);
   - ambiente: fotos do próprio cômodo (essenciais em cômodo sem itens, como lavabos).
4. Grava trabalho/<vis>/comodo_<idx>.json (tarefa compacta de cada cômodo) e fotos.json (URLs para o zoom)
   e imprime o resumo usado como `args` do workflow.
"""
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pleno  # noqa: E402

CAMPOS = {1: 'Material', 2: 'Pintura', 3: 'Cor', 4: 'Funcionamento', 5: 'Marca', 6: 'Estado', 7: 'Avarias'}


def espalhadas(n, k):
    if n <= k:
        return list(range(n))
    return sorted({round(i * (n - 1) / (k - 1)) for i in range(k)})


def video_info(url, arq):
    """Baixa o vídeo (cache) e devolve (duração em s, volume máximo em dB ou None)."""
    if not arq.exists() or arq.stat().st_size < 1000:
        subprocess.run(['curl', '-sS', '--max-time', '240', '-o', str(arq), url.split('?')[0]])
    dur = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', str(arq)],
                         capture_output=True, text=True).stdout.strip()
    vol = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(arq), '-af', 'volumedetect', '-vn', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    m = re.search(r'max_volume: (-?[\d.]+) dB', vol)
    return (float(dur) if dur else 0.0), (float(m.group(1)) if m else None)


def quadros(arq, dur, n, base, pasta_thumbs):
    """Extrai n quadros espalhados do vídeo como miniaturas. Devolve [(segundo, código_da_miniatura)]."""
    ts = [0.0] if dur <= 1 else sorted({round(0.4 + i * (dur - 0.8) / max(n - 1, 1), 1) for i in range(n)})
    out = []
    for t in ts:
        cod = f'{base}_{t:g}s'
        dest = pasta_thumbs / f'{cod}.jpg'
        if not dest.exists():
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', str(t), '-i', str(arq), '-frames:v', '1',
                            '-vf', 'scale=300:300:force_original_aspect_ratio=decrease', '-y', str(dest)])
        out.append((t, cod))
    return out


def montar(arquivos, rotulos, saida, titulo, lado, colunas):
    args = ['montage']
    for f, r in zip(arquivos, rotulos):
        args += ['-label', r, f]
    subprocess.run(args + ['-tile', f'{colunas}x', '-geometry', f'{lado}x{lado}+3+3', '-pointsize', '12',
                           '-title', titulo, '-background', 'white', saida], check=True)


def main():
    vis = sys.argv[1]
    todos = '--todos' in sys.argv
    so = None
    if '--comodos' in sys.argv:
        so = {int(x) for x in sys.argv[sys.argv.index('--comodos') + 1].split(',')}
    classes = {x.lower() for x in json.load(open(pleno.BASE / 'padrao' / 'classes_itens.json'))['padrao']}
    pasta = pleno.pasta_vis(vis)
    thumbs, paineis, videos = pasta / 'thumbs', pasta / 'paineis', pasta / 'videos'
    thumbs.mkdir(exist_ok=True)
    paineis.mkdir(exist_ok=True)
    videos.mkdir(exist_ok=True)

    def tiles_video(urls, base, rot, n_quadros):
        """Quadros de cada vídeo como miniaturas (código, None, rótulo) + resumo dos vídeos para a tarefa."""
        tiles, info = [], []
        for k, u in enumerate(urls, 1):
            arq = videos / f'{base}_v{k}.mp4'
            dur, som = video_info(u, arq)
            info.append({'video': k, 'duracao_s': round(dur, 1), 'som_max_db': som})
            for t, cod in quadros(arq, dur, n_quadros, f'{base}_v{k}', thumbs):
                tiles.append((cod, None, f'{rot} v{k} {t:g}s'))
        return tiles, info
    d = pleno.vistoria(vis)
    fotos_url, baixar, resumo = {}, [], []

    for idx, a in enumerate(pleno.ambientes_ordenados(d), 1):
        if so and idx not in so:
            continue
        nome = a['tipo_ambiente']['tip_amb_descricao']
        itens_todos = pleno.itens_ordenados(a)
        fotos_amb = [f['path'] for f in a.get('fotos') or []]
        for k, u in enumerate(fotos_amb, 1):
            fotos_url[f'{idx}:a:{k}'] = u
        videos_amb = [v['path'] for v in a.get('videos') or []]
        for k, u in enumerate(videos_amb, 1):
            fotos_url[f'{idx}:a:v{k}'] = u
        tarefa = {'vis': int(vis), 'idx': idx, 'amb_codigo': a['amb_codigo'], 'ambiente': nome,
                  'tip_amb_codigo': a.get('tip_amb_codigo'), 'tip_vis_codigo': d['tip_vis_codigo'],
                  'notas_ambiente': [n['not_descricao'] for n in a.get('notas') or []],
                  'n_fotos_ambiente': len(fotos_amb), 'itens': [], 'paineis': {'padrao': [], 'atencao': [], 'ambiente': []}}
        pend = {'padrao': [], 'atencao': []}
        for n, it in enumerate(itens_todos, 1):
            fotos = [f['path'] for f in it.get('fotos') or []]
            for k, u in enumerate(fotos, 1):
                fotos_url[f'{idx}:{n}:{k}'] = u
            vids = [v['path'] for v in it.get('videos') or []]
            for k, u in enumerate(vids, 1):
                fotos_url[f'{idx}:{n}:v{k}'] = u
            if pleno.item_preenchido(it) and not todos:
                continue
            nome_it = it['tipo_ambiente_item']['tip_amb_ite_descricao']
            classe = 'padrao' if nome_it.lower() in classes else 'atencao'
            campos = [CAMPOS.get(dd['tip_det_codigo'], dd['tipo_detalhe']['tip_det_nome'])
                      for dd in sorted(it.get('detalhe_descricao') or [], key=lambda x: x['det_des_ordem'])]
            campos = [c for c in campos if c != 'Pintura']
            sem_campos = not campos
            if sem_campos:  # item veio do app sem campos: o gravar.py cria os que receberem valor
                campos = ['Material', 'Cor', 'Estado', 'Avarias']
            # vídeos: quadros espalhados entram no painel do item (4 no padrão, 8 na atenção) + duração e som
            vt, vinfo = tiles_video(vids, f'{idx}_{n}', f'{n}.{nome_it[:10]}', 4 if classe == 'padrao' else 8)
            tarefa['itens'].append({'n': n, 'amb_ite_codigo': it['amb_ite_codigo'], 'item': nome_it, 'qtd': it['amb_ite_quantidade'],
                                    'classe': classe, 'campos': campos, 'campos_novos': sem_campos, 'n_fotos': len(fotos),
                                    'videos': vinfo, 'notas': [n2['not_descricao'] for n2 in it.get('notas') or []]})
            pend[classe].append((n, nome_it, fotos, vt))
        sem_itens = not itens_todos
        # painel padrão: até 3 fotos espalhadas de cada item + quadros dos vídeos
        tiles = []
        for n, nome_it, fotos, vt in pend['padrao']:
            for k in espalhadas(len(fotos), 3):
                tiles.append((f'{idx}_{n}_{k + 1}', fotos[k], f'{n}.{nome_it[:16]} f{k + 1}'))
            tiles += vt
        for p in range(0, len(tiles), 30):
            tarefa['paineis']['padrao'].append(('padrao', tiles[p:p + 30], 220, 6))
        # painéis de atenção: todas as fotos e quadros de vídeo; itens grandes em mosaico menor
        grupo = []
        for n, nome_it, fotos, vt in pend['atencao']:
            t = [(f'{idx}_{n}_{k}', u, f'{n}.{nome_it[:14]} f{k}') for k, u in enumerate(fotos, 1)] + vt
            if len(t) > 30:
                for p in range(0, len(t), 48):
                    tarefa['paineis']['atencao'].append(('atencao', t[p:p + 48], 150, 8))
            elif len(grupo) + len(t) > 30:
                tarefa['paineis']['atencao'].append(('atencao', grupo, 220, 6))
                grupo = list(t)
            else:
                grupo += t
        if grupo:
            tarefa['paineis']['atencao'].append(('atencao', grupo, 220, 6))
        # fotos do ambiente: obrigatórias em cômodo sem itens; contexto (até 30) nos demais
        if (fotos_amb or videos_amb) and (sem_itens or tarefa['itens']):
            t = [(f'{idx}_a_{k}', u, f'amb f{k}') for k, u in enumerate(fotos_amb, 1)]
            if not sem_itens:
                t = [t[i] for i in espalhadas(len(t), 30)] if t else []
            vt, vinfo = tiles_video(videos_amb, f'{idx}_a', 'amb', 8)
            tarefa['videos_ambiente'] = vinfo
            t += vt
            for p in range(0, len(t), 30):
                tarefa['paineis']['ambiente'].append(('ambiente', t[p:p + 30], 220, 6))
        # numera e registra downloads
        for tipo in ('padrao', 'atencao', 'ambiente'):
            lista = []
            for p, (_, t, lado, cols) in enumerate(tarefa['paineis'][tipo], 1):
                arq = str(paineis / f'{idx:02d}_{tipo}_{p}.jpg')
                lista.append({'arquivo': arq, 'tiles': t, 'lado': lado, 'colunas': cols})
                baixar += [(str(thumbs / f'{c}.jpg'), u.split('?')[0].replace('/fotos/', '/fotos/thumbs/')) for c, u, _ in t if u]
            tarefa['paineis'][tipo] = lista
        tarefa['_pendentes'] = {k: len(v) for k, v in pend.items()}
        tarefa['_sem_itens'] = sem_itens
        tarefa['_nome'] = nome
        resumo.append(tarefa)

    def get(job):
        dest, url = job
        if not os.path.exists(dest) or os.path.getsize(dest) < 500:
            subprocess.run(['curl', '-sS', '--max-time', '60', '-o', dest, url])
    with ThreadPoolExecutor(16) as ex:
        list(ex.map(get, baixar))
    saida = []
    for t in resumo:
        for tipo in ('padrao', 'atencao', 'ambiente'):
            for p, pa in enumerate(t['paineis'][tipo], 1):
                montar([str(thumbs / f'{c}.jpg') for c, _, _ in pa['tiles']], [r for _, _, r in pa['tiles']], pa['arquivo'],
                       f"{t['idx']}. {t['_nome']} - {tipo} {p}", pa['lado'], pa['colunas'])
            t['paineis'][tipo] = [pa['arquivo'] for pa in t['paineis'][tipo]]
        info = {'idx': t['idx'], 'ambiente': t['_nome'], 'padrao': t['_pendentes']['padrao'], 'atencao': t['_pendentes']['atencao'],
                'sem_itens': t['_sem_itens'], 'paineis': sum(len(v) for v in t['paineis'].values()),
                'p_padrao': t['paineis']['padrao'], 'p_atencao': t['paineis']['atencao'], 'p_ambiente': t['paineis']['ambiente'],
                'n_sem_foto': sum(1 for x in t['itens'] if x['classe'] == 'padrao' and not x['n_fotos'])}
        for k in ('_pendentes', '_sem_itens', '_nome'):
            t.pop(k)
        (pasta / f"comodo_{t['idx']}.json").write_text(json.dumps(t, ensure_ascii=False, indent=1))
        if info['padrao'] or info['atencao'] or info['sem_itens']:
            saida.append(info)
    arq_fotos = pasta / 'fotos.json'
    if so and arq_fotos.exists():  # rodada parcial (--comodos): mantém as fotos dos outros cômodos para o zoom
        fotos_url = {**json.loads(arq_fotos.read_text()), **fotos_url}
    arq_fotos.write_text(json.dumps(fotos_url, ensure_ascii=False))
    print(f"Vistoria {vis}: {d.get('vis_identificacao')} | tipo {d['tip_vis_codigo']}")
    for i in saida:
        print(f"  {i['idx']:>2}. {i['ambiente']:<18} padrão {i['padrao']:>2} | atenção {i['atencao']:>2} | sem itens {'sim' if i['sem_itens'] else 'não'} | painéis {i['paineis']}")
    if not saida:
        print('  Nada pendente: todos os itens já têm preenchimento.')
    print('ARGS_WORKFLOW=' + json.dumps({'vis': int(vis), 'base': str(pleno.BASE), 'comodos': saida}, ensure_ascii=False))


if __name__ == '__main__':
    main()
