export const meta = {
  name: 'preencher-vistoria',
  description: 'Preenche itens pendentes de uma vistoria do Pleno, um cômodo por vez: modelo leve nos itens padrão, modelo forte nos itens de atenção, gravação direta',
  whenToUse: 'Depois de rodar vistorias/ferramentas/preparar.py <vis>; passe o ARGS_WORKFLOW impresso como args.',
  phases: [
    { title: 'Cômodos', detail: 'um cômodo por vez; cada cômodo grava e confere antes do próximo' },
  ],
}

// args = { vis, base, comodos: [{ idx, ambiente, padrao, atencao, sem_itens, paineis }] }  (impresso pelo preparar.py)
const A = args || {}
const VIS = A.vis
const BASE = A.base
const FERR = `${BASE}/ferramentas`
const REGRAS = `${BASE}/padrao/regras_agente.md`
const TRAB = `${BASE}/trabalho/${VIS}`

const RESUMO = {
  type: 'object',
  properties: {
    itens_gravados: { type: 'integer' },
    novos_itens: { type: 'integer' },
    avarias: { type: 'array', items: { type: 'string' }, description: 'item: avaria (curto)' },
    suspeitas: { type: 'array', items: { type: 'object', properties: { amb_ite_codigo: { type: 'integer' }, item: { type: 'string' }, motivo: { type: 'string' } }, required: ['amb_ite_codigo', 'item', 'motivo'] }, description: 'só o agente leve: itens padrão NÃO gravados por possível avaria/dúvida' },
    verificar_no_local: { type: 'array', items: { type: 'string' } },
    saida_gravar: { type: 'string', description: 'última linha de resumo do gravar.py' },
  },
  required: ['itens_gravados', 'novos_itens', 'avarias', 'suspeitas', 'verificar_no_local', 'saida_gravar'],
}

const cab = (c, paineis) => `Vistoria ${VIS}, cômodo ${c.idx} (${c.ambiente}). Ferramentas: ${FERR}.
RODADA 1 — leia tudo de uma vez, na mesma resposta (chamadas Read em paralelo): ${REGRAS} (regras e formato), ${TRAB}/comodo_${c.idx}.json (itens pendentes e campos)${paineis.length ? ' e os painéis: ' + paineis.join(', ') : ''}.
No fim, salve e grave num ÚNICO comando Bash: cat > <arquivo> <<'EOF' ...json... EOF && python3 ${FERR}/gravar.py ${VIS} <arquivo>`

const leve = c => agent(`${cab(c, (c.p_padrao || []).concat(c.n_sem_foto ? (c.p_ambiente || []) : []))}
Você é o agente LEVE. Trate SOMENTE os itens com "classe": "padrao".
Se um item padrão tiver possível avaria ou dúvida que exija zoom, NÃO o inclua no JSON: liste em "suspeitas" (o modelo forte cuida).
Arquivo: ${TRAB}/res_${c.idx}_padrao.json.`,
  { label: `leve:${c.idx}-${c.ambiente}`, phase: 'Cômodos', schema: RESUMO, model: 'haiku', effort: 'low' })

const forte = c => agent(`${cab(c, (c.p_atencao || []).concat(c.p_ambiente || []))}
Você é o agente de ATENÇÃO. Trate SOMENTE os itens com "classe": "atencao"${c.sem_itens ? ' — este cômodo NÃO tem itens: crie todos os itens a partir das fotos do cômodo (novos_itens) e uma nota do cômodo só se necessário' : ''}.
Paredes, tetos, pisos, móveis, eletros, bancadas e gabinetes: procure avaria de verdade e confirme no zoom (uma chamada do zoom.py com todas as suspeitas) antes de marcar.
Arquivo: ${TRAB}/res_${c.idx}_atencao.json. "suspeitas": [].`,
  { label: `forte:${c.idx}-${c.ambiente}`, phase: 'Cômodos', schema: RESUMO })

const extra = (c, susp) => agent(`${cab(c, c.p_padrao || [])}
Você é o agente de ATENÇÃO para itens padrão que o agente leve marcou como suspeitos: ${JSON.stringify(susp)}.
Faça zoom só nessas fotos, decida e grave esses itens. Arquivo: ${TRAB}/res_${c.idx}_extra.json. "suspeitas": [].`,
  { label: `forte-extra:${c.idx}-${c.ambiente}`, phase: 'Cômodos', schema: RESUMO })

phase('Cômodos')
const resultado = []
for (const c of A.comodos || []) {
  const tarefas = []
  if (c.padrao > 0) tarefas.push(() => leve(c))
  if (c.atencao > 0 || c.sem_itens) tarefas.push(() => forte(c))
  const rs = (await parallel(tarefas)).filter(Boolean)
  const susp = rs.flatMap(r => r.suspeitas || [])
  if (susp.length) {
    const r = await extra(c, susp)
    if (r) rs.push(r)
  }
  const gravados = rs.reduce((s, r) => s + (r.itens_gravados || 0), 0)
  log(`${c.idx}. ${c.ambiente}: ${gravados} itens gravados, ${rs.reduce((s, r) => s + (r.novos_itens || 0), 0)} novos, ${susp.length} suspeitas reavaliadas`)
  resultado.push({ idx: c.idx, ambiente: c.ambiente, gravados, avarias: rs.flatMap(r => r.avarias || []), verificar_no_local: rs.flatMap(r => r.verificar_no_local || []), saidas: rs.map(r => r.saida_gravar) })
}
return resultado
