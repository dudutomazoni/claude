"""Situação do preenchimento direto do sistema (somente leitura).

Uso: python3 status.py <vis> [--detalhe] [--comodo N]
Mostra, por cômodo, quantos itens já têm preenchimento, quantos faltam, notas e avarias.
--detalhe lista cada item com os valores gravados (para conferência rápida em texto).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pleno  # noqa: E402


def main():
    vis = sys.argv[1]
    det = '--detalhe' in sys.argv
    so = int(sys.argv[sys.argv.index('--comodo') + 1]) if '--comodo' in sys.argv else None
    d = pleno.vistoria(vis)
    strip = lambda h: re.sub(r'<[^>]+>', '', h or '').strip()
    tot_f = tot_p = 0
    print(f"Vistoria {vis}: {d.get('vis_identificacao')}")
    for idx, a in enumerate(pleno.ambientes_ordenados(d), 1):
        if so and idx != so:
            continue
        its = pleno.itens_ordenados(a)
        feitos = [it for it in its if pleno.item_preenchido(it)]
        faltam = [it['tipo_ambiente_item']['tip_amb_ite_descricao'] for it in its if not pleno.item_preenchido(it)]
        avar = sum(1 for it in its for dd in it.get('detalhe_descricao') or [] if dd['tip_det_codigo'] == 7 and pleno.valores(dd))
        tot_f += len(feitos)
        tot_p += len(faltam)
        print(f"{idx:>2}. {a['tipo_ambiente']['tip_amb_descricao']:<18} itens {len(its):>3} | preenchidos {len(feitos):>3} | faltam {len(faltam):>3}"
              f" | com avaria {avar:>2} | notas do cômodo {len(a.get('notas') or [])}" + (f" | faltam: {', '.join(faltam)}" if faltam else ''))
        if det:
            for n, it in enumerate(its, 1):
                vals = {dd['tipo_detalhe']['tip_det_nome']: ', '.join(pleno.valores(dd)) for dd in it.get('detalhe_descricao') or [] if pleno.valores(dd)}
                notas = [strip(x['not_descricao']) for x in it.get('notas') or []]
                print(f"     {n}. {it['tipo_ambiente_item']['tip_amb_ite_descricao']} x{it['amb_ite_quantidade']} | {vals}" + (f" | nota: {notas}" if notas else ''))
    print(f"Total: preenchidos {tot_f} | faltam {tot_p}")


if __name__ == '__main__':
    main()
