"""Devolve a lista completa de opções aos campos gravados pela versão antiga do gravar.py (sem `descricoes`).

Uso: python3 reparar_opcoes.py <vis> --data AAAA-MM-DD [--itens 40353,40354] [--simular]

Regrava cada campo COM VALOR cuja última alteração foi na data indicada (dia em que o gravador antigo rodou),
mantendo exatamente os valores atuais e enviando a lista completa de opções, como o site faz ao marcar.
Campos alterados em outra data (ex.: corrigidos à mão) não são tocados. No fim confere que nenhum valor mudou.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pleno  # noqa: E402


def main():
    vis = sys.argv[1]
    data = sys.argv[sys.argv.index('--data') + 1]
    so = {int(x) for x in sys.argv[sys.argv.index('--itens') + 1].split(',')} if '--itens' in sys.argv else None
    simular = '--simular' in sys.argv
    pasta = pleno.pasta_vis(vis)
    log = open(pasta / 'reparo_opcoes.jsonl', 'a')
    d = pleno.vistoria(vis)
    antes, feitos, erros = {}, 0, []
    for pos, a in enumerate(pleno.ambientes_ordenados(d)):
        for it in a['ambientes_itens']:
            if so and it['amb_ite_codigo'] not in so:
                continue
            for dd in it.get('detalhe_descricao') or []:
                rel = dd.get('relacoes_detalhes_descricoes_tipos') or []
                if not rel or (dd.get('updated_at') or '')[:10] != data:
                    continue
                antes[dd['det_des_codigo']] = sorted(r['tip_det_des_codigo'] for r in rel)
                corpo = pleno.corpo_detalhe(dd['det_des_codigo'], it['amb_ite_codigo'], it['tipo_ambiente_item']['tip_amb_ite_codigo'],
                                            dd['tip_det_codigo'], dd['tipo_detalhe']['tip_det_nome'], dd['det_des_ordem'], rel,
                                            [r['tip_det_des_codigo'] for r in rel], [r['tip_det_descricao'] for r in rel],
                                            pos, dd.get('det_des_mod_padrao'))
                if simular:
                    feitos += 1
                    continue
                code, r = pleno.chamar('PUT', f"detalheDescricao/{dd['det_des_codigo']}/update", corpo)
                ok = code == '200' and isinstance(r, dict) and r.get('success')
                log.write(json.dumps({'ok': ok, 'det_des_codigo': dd['det_des_codigo'], 'item': it['tipo_ambiente_item']['tip_amb_ite_descricao'],
                                      'campo': dd['tipo_detalhe']['tip_det_nome'], 'n_opcoes': len(corpo['descricoes']), 'http': code,
                                      'resp': str(r)[:200]}, ensure_ascii=False) + '\n')
                log.flush()
                if ok:
                    feitos += 1
                else:
                    erros.append((dd['det_des_codigo'], code, str(r)[:150]))
    mudou = []
    if not simular and antes:
        d2 = pleno.vistoria(vis)
        depois = {dd['det_des_codigo']: sorted(r['tip_det_des_codigo'] for r in dd.get('relacoes_detalhes_descricoes_tipos') or [])
                  for a in d2['ambientes'] for it in a['ambientes_itens'] for dd in it.get('detalhe_descricao') or []}
        mudou = [k for k, v in antes.items() if depois.get(k) != v]
    print(f"Vistoria {vis}: campos reparados {feitos}{' [SIMULAÇÃO]' if simular else ''} | erros {len(erros)} | valores que mudaram {len(mudou)}")
    for e in erros[:20]:
        print('  ERRO', e)
    for m in mudou[:20]:
        print('  MUDOU', m, antes[m])
    sys.exit(1 if erros or mudou else 0)


if __name__ == '__main__':
    main()
