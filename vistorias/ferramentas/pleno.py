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
