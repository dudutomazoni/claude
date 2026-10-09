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
    thumbs, paineis = pasta / 'thumbs', pasta / 'paineis'
    thumbs.mkdir(exist_ok=True)
    paineis.mkdir(exist_ok=True)
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
        tarefa = {'vis': int(vis), 'idx': idx, 'amb_codigo': a['amb_codigo'], 'ambiente': nome,
                  'tip_amb_codigo': a.get('tip_amb_codigo'), 'tip_vis_codigo': d['tip_vis_codigo'],
                  'notas_ambiente': [n['not_descricao'] for n in a.get('notas') or []],
                  'n_fotos_ambiente': len(fotos_amb), 'itens': [], 'paineis': {'padrao': [], 'atencao': [], 'ambiente': []}}
        pend = {'padrao': [], 'atencao': []}
        for n, it in enumerate(itens_todos, 1):
            fotos = [f['path'] for f in it.get('fotos') or []]
            for k, u in enumerate(fotos, 1):
                fotos_url[f'{idx}:{n}:{k}'] = u
            if pleno.item_preenchido(it) and not todos:
                continue
            nome_it = it['tipo_ambiente_item']['tip_amb_ite_descricao']
            classe = 'padrao' if nome_it.lower() in classes else 'atencao'
            campos = [CAMPOS.get(dd['tip_det_codigo'], dd['tipo_detalhe']['tip_det_nome'])
                      for dd in sorted(it.get('detalhe_descricao') or [], key=lambda x: x['det_des_ordem'])]
            tarefa['itens'].append({'n': n, 'amb_ite_codigo': it['amb_ite_codigo'], 'item': nome_it, 'qtd': it['amb_ite_quantidade'],
                                    'classe': classe, 'campos': [c for c in campos if c != 'Pintura'], 'n_fotos': len(fotos),
                                    'notas': [n2['not_descricao'] for n2 in it.get('notas') or []]})
            pend[classe].append((n, nome_it, fotos))
        sem_itens = not itens_todos
        # painel padrão: até 3 fotos espalhadas de cada item
        tiles = []
        for n, nome_it, fotos in pend['padrao']:
            for k in espalhadas(len(fotos), 3):
                tiles.append((f'{idx}_{n}_{k + 1}', fotos[k], f'{n}.{nome_it[:16]} f{k + 1}'))
        for p in range(0, len(tiles), 30):
            tarefa['paineis']['padrao'].append(('padrao', tiles[p:p + 30], 220, 6))
        # painéis de atenção: todas as fotos; itens grandes em mosaico menor
        grupo = []
        for n, nome_it, fotos in pend['atencao']:
            t = [(f'{idx}_{n}_{k}', u, f'{n}.{nome_it[:14]} f{k}') for k, u in enumerate(fotos, 1)]
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
        if fotos_amb and (sem_itens or tarefa['itens']):
            t = [(f'{idx}_a_{k}', u, f'amb f{k}') for k, u in enumerate(fotos_amb, 1)]
            if not sem_itens:
                t = [t[i] for i in espalhadas(len(t), 30)]
            for p in range(0, len(t), 30):
                tarefa['paineis']['ambiente'].append(('ambiente', t[p:p + 30], 220, 6))
        # numera e registra downloads
        for tipo in ('padrao', 'atencao', 'ambiente'):
            lista = []
            for p, (_, t, lado, cols) in enumerate(tarefa['paineis'][tipo], 1):
                arq = str(paineis / f'{idx:02d}_{tipo}_{p}.jpg')
                lista.append({'arquivo': arq, 'tiles': t, 'lado': lado, 'colunas': cols})
                baixar += [(str(thumbs / f'{c}.jpg'), u.split('?')[0].replace('/fotos/', '/fotos/thumbs/')) for c, u, _ in t]
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
                'sem_itens': t['_sem_itens'], 'paineis': sum(len(v) for v in t['paineis'].values())}
        for k in ('_pendentes', '_sem_itens', '_nome'):
            t.pop(k)
        (pasta / f"comodo_{t['idx']}.json").write_text(json.dumps(t, ensure_ascii=False, indent=1))
        if info['padrao'] or info['atencao'] or info['sem_itens']:
            saida.append(info)
    (pasta / 'fotos.json').write_text(json.dumps(fotos_url, ensure_ascii=False))
    print(f"Vistoria {vis}: {d.get('vis_identificacao')} | tipo {d['tip_vis_codigo']}")
    for i in saida:
        print(f"  {i['idx']:>2}. {i['ambiente']:<18} padrão {i['padrao']:>2} | atenção {i['atencao']:>2} | sem itens {'sim' if i['sem_itens'] else 'não'} | painéis {i['paineis']}")
    if not saida:
        print('  Nada pendente: todos os itens já têm preenchimento.')
    print('ARGS_WORKFLOW=' + json.dumps({'vis': int(vis), 'base': str(pleno.BASE), 'comodos': saida}, ensure_ascii=False))


if __name__ == '__main__':
    main()
