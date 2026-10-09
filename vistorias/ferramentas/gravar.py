"""Grava no Pleno o resultado de UM cômodo e confere em seguida.

Uso: python3 gravar.py <vis> <resultado.json> [--simular] [--sobrescrever]

Formato do resultado (um cômodo):
{
  "amb_codigo": 1966,
  "itens": [ {"amb_ite_codigo": 40339, "Material": "madeira", "Cor": "Branca", "Funcionamento": "funcionando",
              "Marca": "", "Estado": "Em bom estado", "Avarias": "riscos, manchas", "nota": "Frase curta."} ],
  "nota_ambiente": "",
  "novos_itens": [ {"tipo": "Vaso sanitário", "qtd": 1, "Material": "louça", "Cor": "Branca", "Funcionamento": "funcionando",
                    "Estado": "Em bom estado", "Avarias": "", "nota": ""} ]
}
Regras:
- Nunca sobrescreve: campo que já tem valor é pulado (a nota só entra se o item não tiver nota);
  --sobrescrever permite substituir. Rodar de novo é seguro: só grava o que ainda está vazio.
- Termos: precisam existir na lista do sistema (tipoDetalheDescricao). Diferença só de maiúsculas é corrigida
  sozinha; termo inexistente é rejeitado e listado (saída com código 2) para correção.
- Campo que o item não tem (ex.: Tapete sem 'Estado') é criado com detalheDescricao/store.
- Itens novos: ambienteItem/storeMultiple + detalheDescricao/storeMultiple (campos já com valores) + nota.
  Registro em trabalho/<vis>/novos_itens.json evita criar duas vezes se o script rodar de novo.
- No fim relê a vistoria e confere cada valor gravado. Log em trabalho/<vis>/gravacao.jsonl.
"""
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pleno  # noqa: E402

TD = {'Material': 1, 'Cor': 3, 'Funcionamento': 4, 'Marca': 5, 'Estado': 6, 'Avarias': 7}
NOME_TD = {v: k for k, v in TD.items()}


def main():
    vis, arq = sys.argv[1], sys.argv[2]
    simular, sobrescrever = '--simular' in sys.argv, '--sobrescrever' in sys.argv
    res = json.load(open(arq))
    pasta = pleno.pasta_vis(vis)
    log = open(pasta / 'gravacao.jsonl', 'a')
    opc = pleno.opcoes_detalhe()
    opc_low = {}
    for k, v in opc.items():
        opc_low.setdefault(k.lower(), []).append(k)
    cat = json.load(open(pleno.BASE / 'padrao' / 'tipos_itens.json'))['tipos_item']
    cat_low = {k.lower(): (k, v) for k, v in cat.items()}
    d = pleno.vistoria(vis)
    amb = next((a for a in d['ambientes'] if a['amb_codigo'] == res['amb_codigo']), None)
    if not amb:
        raise SystemExit(f"amb_codigo {res['amb_codigo']} não existe na vistoria {vis}")
    itens = {it['amb_ite_codigo']: it for it in amb['ambientes_itens']}
    rejeitados, feitos, pulados, erros = [], [], [], []
    esperado = {}  # (amb_ite_codigo, tip_det) -> [termos]

    def op(metodo, rota, corpo, desc):
        if simular:
            feitos.append(('SIMULADO', desc))
            return True, {}
        code, r = pleno.chamar(metodo, rota, corpo)
        ok = code == '200' and isinstance(r, dict) and r.get('success')
        log.write(json.dumps({'ok': ok, 'desc': desc, 'metodo': metodo, 'rota': rota, 'corpo': corpo, 'http': code,
                              'resp': str(r)[:400]}, ensure_ascii=False) + '\n')
        log.flush()
        (feitos if ok else erros).append((code, desc))
        return ok, (r.get('data') if isinstance(r, dict) else r)

    def codigos(valor, onde):
        termos = [t.strip() for t in str(valor).split(',') if t.strip()]
        cods, nomes = [], []
        for t in termos:
            if t in opc:
                nome = t
            elif len(opc_low.get(t.lower(), [])) >= 1:
                nome = opc_low[t.lower()][0]
            else:
                rejeitados.append((onde, t))
                return None, None
            cods.append(sorted(opc[nome])[0])
            nomes.append(nome)
        return cods, nomes

    def html_nota(t):
        return f'<p>{html.escape(t.strip(), quote=False)}</p>'

    def tem_nota(lista, texto):
        alvo = html_nota(texto)
        return any((n.get('not_descricao') or '').strip() == alvo for n in lista or [])

    # 1) itens existentes
    for e in res.get('itens', []):
        it = itens.get(e['amb_ite_codigo'])
        nome_it = it['tipo_ambiente_item']['tip_amb_ite_descricao'] if it else '?'
        if not it:
            erros.append(('-', f"item {e['amb_ite_codigo']} não pertence a este cômodo"))
            continue
        dets = {dd['tip_det_codigo']: dd for dd in it.get('detalhe_descricao') or []}
        prox = max([dd['det_des_ordem'] for dd in dets.values()] + [-1]) + 1
        for campo, td in TD.items():
            val = (e.get(campo) or '').strip()
            if not val:
                continue
            if td in dets and pleno.valores(dets[td]) and not sobrescrever:
                pulados.append(f'{nome_it} / {campo} (já tinha: {", ".join(pleno.valores(dets[td]))})')
                continue
            cods, nomes = codigos(val, f'{nome_it} / {campo}')
            if cods is None:
                continue
            esperado[(it['amb_ite_codigo'], td)] = nomes
            if td in dets:
                dd = dets[td]
                corpo = {'det_des_codigo': dd['det_des_codigo'], 'amb_ite_codigo': it['amb_ite_codigo'], 'cha_codigo': None,
                         'med_codigo': None, 'det_des_ordem': dd['det_des_ordem'], 'tip_det_codigo': td,
                         'tipo_detalhe': campo, 'tip_det_des_codigo_array': cods}
                op('PUT', f"detalheDescricao/{dd['det_des_codigo']}/update", corpo, f'{nome_it} / {campo} = {val}')
            else:
                corpo = {'det_des_codigo': None, 'amb_ite_codigo': it['amb_ite_codigo'], 'cha_codigo': None, 'med_codigo': None,
                         'det_des_ordem': prox, 'tip_det_codigo': td, 'tipo_detalhe': campo, 'tip_det_des_codigo_array': cods}
                prox += 1
                op('POST', 'detalheDescricao/store', corpo, f'{nome_it} / {campo} (campo novo) = {val}')
        nota = (e.get('nota') or '').strip()
        if nota:
            if it.get('notas') and not sobrescrever:
                pulados.append(f'{nome_it} nota (item já tem nota)')
            elif not tem_nota(it.get('notas'), nota):
                op('POST', 'nota/store', {'amb_ite_codigo': it['amb_ite_codigo'], 'not_descricao': html_nota(nota),
                                          'not_ordem': len(it.get('notas') or []) + 1}, f'{nome_it} / nota')
    # 2) nota do cômodo
    na = (res.get('nota_ambiente') or '').strip()
    if na and not tem_nota(amb.get('notas'), na):
        op('POST', 'nota/store', {'amb_codigo': amb['amb_codigo'], 'not_descricao': html_nota(na),
                                  'not_ordem': len(amb.get('notas') or []) + 1}, 'nota do cômodo')
    # 3) itens novos
    reg_arq = pasta / 'novos_itens.json'
    reg = json.loads(reg_arq.read_text()) if reg_arq.exists() else {}
    for k, e in enumerate(res.get('novos_itens', [])):
        chave = f"{amb['amb_codigo']}|{e['tipo']}|{(e.get('nota') or '')[:60]}|{k}"
        if chave in reg:
            pulados.append(f"novo item {e['tipo']} (já criado: {reg[chave]})")
            continue
        tipo = cat_low.get(e['tipo'].strip().lower())
        if not tipo:
            rejeitados.append((f"novo item '{e['tipo']}'", 'tipo inexistente no catálogo (padrao/tipos_itens.json)'))
            continue
        campos = {}
        for campo, td in TD.items():
            val = (e.get(campo) or '').strip()
            if val:
                cods, nomes = codigos(val, f"novo {e['tipo']} / {campo}")
                if cods is None:
                    campos = None
                    break
                campos[td] = (cods, nomes, val)
        if campos is None:
            continue
        ok, r = op('POST', 'ambienteItem/storeMultiple', [{'amb_ite_quantidade': int(e.get('qtd') or 1), 'amb_codigo': amb['amb_codigo'],
                   'tip_ite_codigo': tipo[1], 'tip_est_codigo': None, 'tip_vis_codigo': d['tip_vis_codigo']}], f"novo item {tipo[0]}")
        if not ok:
            continue
        if simular:
            continue
        novo = r[0]
        ite = novo['amb_ite_codigo']
        reg[chave] = ite
        reg_arq.write_text(json.dumps(reg, ensure_ascii=False, indent=1))
        info = {t['tip_det_codigo']: t.get('tip_det_nome') for t in (novo.get('tipo_ambiente_item') or {}).get('tipos_detalhes') or []}
        tds = list(info) + [td for td in campos if td not in info]
        linhas = []
        for o, td in enumerate(tds):
            if td == 2 and td not in campos:
                continue  # Pintura fica de fora
            linhas.append({'det_des_codigo': None, 'amb_ite_codigo': ite, 'cha_codigo': None, 'med_codigo': None, 'det_des_ordem': o,
                           'tip_det_codigo': td, 'tipo_detalhe': info.get(td) or NOME_TD.get(td, str(td)),
                           'tip_det_des_codigo_array': campos.get(td, ([], [], ''))[0], 'uniqId': f'n{ite}_{td}'})
            if td in campos:
                esperado[(ite, td)] = campos[td][1]
        op('POST', 'detalheDescricao/storeMultiple', linhas, f'novo item {tipo[0]} / detalhes')
        if (e.get('nota') or '').strip():
            op('POST', 'nota/store', {'amb_ite_codigo': ite, 'not_descricao': html_nota(e['nota']), 'not_ordem': 1}, f'novo item {tipo[0]} / nota')
    # 4) conferência
    divergencias = []
    if not simular and esperado:
        d2 = pleno.vistoria(vis)
        a2 = next(a for a in d2['ambientes'] if a['amb_codigo'] == amb['amb_codigo'])
        atual = {}
        for it in a2['ambientes_itens']:
            for dd in it.get('detalhe_descricao') or []:
                atual[(it['amb_ite_codigo'], dd['tip_det_codigo'])] = sorted(pleno.valores(dd))
        for chave, nomes in esperado.items():
            if atual.get(chave) != sorted(nomes):
                divergencias.append((chave, nomes, atual.get(chave)))
    print(f"Cômodo {amb['tipo_ambiente']['tip_amb_descricao']} (amb {amb['amb_codigo']}): gravações ok {len(feitos)} | erros {len(erros)} | "
          f"pulados {len(pulados)} | termos rejeitados {len(rejeitados)} | divergências na conferência {len(divergencias)}"
          + (' [SIMULAÇÃO]' if simular else ''))
    for x in erros:
        print('  ERRO', x)
    for x in rejeitados:
        print('  REJEITADO', x)
    for x in divergencias:
        print('  DIVERGÊNCIA', x)
    for x in pulados:
        print('  pulado:', x)
    sys.exit(1 if erros or divergencias else (2 if rejeitados else 0))


if __name__ == '__main__':
    main()
