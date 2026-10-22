"""Acesso à API do Pleno (a mesma que o site usa) e utilidades comuns.

- Token em vistorias/trabalho/token.txt; em 401 faz login de novo (login.js) e repete a chamada.
- Credenciais só por variável de ambiente: PLENO_USER e PLENO_PASS.
- Chamadas via curl (respeita o proxy e o CA do ambiente).
"""
import fcntl
import json
import os
import pathlib
import subprocess
import time

BASE = pathlib.Path(__file__).resolve().parent.parent          # vistorias/
FERR = BASE / 'ferramentas'
TRAB = BASE / 'trabalho'
TOKEN = TRAB / 'token.txt'
API = 'https://api.sistemaspleno.com/api/vistoria/'


def pasta_vis(vis):
    p = TRAB / str(vis)
    p.mkdir(parents=True, exist_ok=True)
    return p


CRED = pathlib.Path.home() / '.config' / 'pleno' / 'credenciais.json'   # alternativa só para a sessão atual (fora do repositório)


def _credenciais():
    """PLENO_USER/PLENO_PASS do ambiente (recomendado) ou ~/.config/pleno/credenciais.json (chmod 600, container temporário)."""
    if os.environ.get('PLENO_USER') and os.environ.get('PLENO_PASS'):
        return
    if CRED.exists():
        c = json.loads(CRED.read_text())
        os.environ['PLENO_USER'], os.environ['PLENO_PASS'] = c['usuario'], c['senha']
        return
    raise SystemExit('Defina PLENO_USER e PLENO_PASS (configurações do ambiente) antes de rodar.')


def login(token_usado=None):
    """Faz login (um processo por vez). Se outro processo já renovou o token, só reaproveita."""
    _credenciais()
    TRAB.mkdir(parents=True, exist_ok=True)
    with open(TRAB / '.login.lock', 'w') as trava:
        fcntl.flock(trava, fcntl.LOCK_EX)
        if token_usado and TOKEN.exists() and TOKEN.read_text().strip() != token_usado:
            return
        subprocess.run(['node', str(FERR / 'login.js'), str(TOKEN)], check=True, cwd=str(FERR))


def _token():
    if not TOKEN.exists():
        login()
    return TOKEN.read_text().strip()


def chamar(metodo, rota, corpo=None, tentativas=3):
    """Retorna (http, json_ou_texto). Refaz login em 401 e repete em erro de rede."""
    for t in range(tentativas):
        tok = _token()
        args = ['curl', '-g', '-sS', '--max-time', '120', '-X', metodo, '-H', f'Authorization: {tok}',
                '-H', 'Accept: application/json', '-H', 'Content-Type: application/json', '-w', '\n%{http_code}', API + rota]
        if corpo is not None:
            args += ['--data-binary', json.dumps(corpo, ensure_ascii=False)]
        out = subprocess.run(args, capture_output=True, text=True).stdout
        txt, code = out.rsplit('\n', 1) if '\n' in out else (out, '000')
        if code == '401' and t < tentativas - 1:
            login(token_usado=tok)
            continue
        if code in ('000', '502', '503', '504') and t < tentativas - 1:
            time.sleep(2 * (t + 1))
            continue
        try:
            return code, json.loads(txt)
        except ValueError:
            return code, txt
    return code, txt


def get(rota):
    code, r = chamar('GET', rota)
    if code != '200' or not isinstance(r, dict) or not r.get('success', True):
        raise RuntimeError(f'GET {rota} -> {code} {str(r)[:300]}')
    return r.get('data', r)


def vistoria(vis, salvar=True):
    d = get(f'vistoria/{vis}/show')
    if salvar:
        (pasta_vis(vis) / 'show.json').write_text(json.dumps(d, ensure_ascii=False))
    return d


def opcoes_detalhe(max_idade_h=24):
    """Lista global de termos (tipoDetalheDescricao) -> {descricao: [codigos]} com cache local."""
    cache = TRAB / 'opcoes_detalhe.json'
    if not cache.exists() or time.time() - cache.stat().st_mtime > max_idade_h * 3600:
        TRAB.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(get('tipoDetalheDescricao'), ensure_ascii=False))
    m = {}
    for x in json.loads(cache.read_text()):
        if x.get('deleted_at'):
            continue
        m.setdefault(x['tip_det_descricao'].strip(), []).append(x['tip_det_des_codigo'])
    return m


_cache_campo = {}


def opcoes_campo(tip_det_codigo, tip_amb_ite_codigo):
    """Lista de opções que o site mostra para um campo de um tipo de item (mesma consulta do site)."""
    k = (tip_det_codigo, tip_amb_ite_codigo)
    if k not in _cache_campo:
        r = get(f'tipoDetalheDescricao?tip_det_codigo={tip_det_codigo}&modelo=false&preferir_com_grupo=true'
                f'&tip_amb_ite_codigo={tip_amb_ite_codigo}')
        _cache_campo[k] = [{'tip_det_des_codigo': x['tip_det_des_codigo'], 'tip_det_descricao': x['tip_det_descricao']}
                           for x in (r or []) if not x.get('deleted_at')]
    return _cache_campo[k]


def _como_form(v):
    """Serializa como o formulário do site (null -> "", true/false -> 1/0)."""
    if v is None:
        return ''
    if v is True:
        return 1
    if v is False:
        return 0
    if isinstance(v, dict):
        return {k: _como_form(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_como_form(x) for x in v]
    return v


def corpo_detalhe(det_des_codigo, amb_ite_codigo, tip_amb_ite_codigo, tip_det_codigo, tipo_detalhe, det_des_ordem,
                  relacoes, codigos, nomes, amb_pos=0, mod_padrao=False):
    """Corpo IDÊNTICO ao que o site envia ao marcar opções num campo (capturado em 22/10/2026).

    O essencial é `descricoes`: a lista COMPLETA de opções do campo. Sem ela o sistema guarda o campo sem
    opções e o app do telefone mostra o campo vazio de opções. Nunca envie só a opção escolhida.
    """
    lista = {}
    for c, n in zip(codigos, nomes):                       # marcadas primeiro, como o site
        lista[c] = n
    for r in relacoes or []:
        lista.setdefault(r['tip_det_des_codigo'], r['tip_det_descricao'])
    for o in sorted(opcoes_campo(tip_det_codigo, tip_amb_ite_codigo), key=lambda o: o['tip_det_descricao'].casefold()):
        lista.setdefault(o['tip_det_des_codigo'], o['tip_det_descricao'])
    descricoes = [{'tip_det_des_codigo': c, 'tip_det_descricao': n} for c, n in lista.items()]
    return _como_form({'det_des_codigo': det_des_codigo, 'amb_ite_codigo': amb_ite_codigo, 'cha_codigo': None, 'med_codigo': None,
                       'det_des_ordem': det_des_ordem, 'det_des_mod_padrao': mod_padrao, 'tip_det_codigo': tip_det_codigo,
                       'tipo_detalhe': tipo_detalhe, 'tipos_detalhes_descricoes': relacoes or [], 'startOpen': None,
                       'tip_det_des_codigo_array': list(codigos), 'descricoes': descricoes, 'path': f'ambientes.{amb_pos}.itens',
                       'tipoValue': tip_amb_ite_codigo, 'tipoLabel': 'tip_amb_ite_codigo'})


def valores(dd):
    """Valores atuais de um detalhe (lista de descrições)."""
    v = [r['tip_det_descricao'] for r in dd.get('relacoes_detalhes_descricoes_tipos') or []]
    if dd.get('det_des_input'):
        v.append(dd['det_des_input'])
    return v


def item_preenchido(it):
    """Um item conta como preenchido se algum detalhe já tem valor (não refazemos o que existe)."""
    return any(valores(dd) for dd in it.get('detalhe_descricao') or [])


def ambientes_ordenados(d):
    return sorted(d['ambientes'], key=lambda a: (a.get('amb_ordem') or 0, a['amb_codigo']))


def itens_ordenados(a):
    return sorted(a['ambientes_itens'], key=lambda x: (x.get('amb_ite_ordem') or 0, x['amb_ite_codigo']))
