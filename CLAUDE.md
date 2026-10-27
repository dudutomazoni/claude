# Plus Vistorias — preenchimento de vistorias no sistema Pleno

Usuário: Eduardo (Plus Vistorias, Balneário Camboriú/SC). Fale em **português simples** (não é técnico).
Portal: https://plusvistorias.sistemaspleno.com · API usada pelo site: https://api.sistemaspleno.com/api/vistoria/

## Autorizações (decididas pelo usuário em 09/10/2026)
- **Preenchimento dos itens** (material, cor, funcionamento, marca, estado, avarias, notas, campos que faltam, itens novos — inclusive
  itens de cômodos sem itens, como lavabos): **gravar direto no sistema, sem pedir aprovação**. Ele confere depois no sistema.
- **Nunca** sem ok explícito naquele momento: apagar qualquer coisa, sobrescrever campo já preenchido, lançar inconformidade,
  mexer em medidores, tipo da vistoria ou observação geral.
- Credenciais: variáveis de ambiente `PLENO_USER` / `PLENO_PASS` (configurações do ambiente — recomendado; os agentes precisam delas
  para relogar, porque o login do usuário no portal derruba o token). Alternativa só para a sessão atual: `~/.config/pleno/credenciais.json`
  (`{"usuario":..., "senha":...}`, chmod 600, fora do repositório). Nunca grave senha dentro do repositório.

## Regras pedidas pelo usuário (22/10/2026) — valem para TODOS os campos e cômodos
1. **Nunca apagar as demais opções de um campo.** Ao marcar uma opção (ex.: Cor "Branca"), a gravação tem de levar a lista
   completa de opções do campo (`descricoes`), exatamente como o site faz. Sem isso o sistema guarda o campo sem opções e o
   **app do telefone** fica sem opções para trocar. Grave sempre pelo `gravar.py` (usa `pleno.corpo_detalhe`); nunca monte o
   PUT na mão. Campos já gravados do jeito antigo se consertam com `reparar_opcoes.py <vis> --data AAAA-MM-DD`
   (a 190 já foi consertada: 491 campos, valores intactos).
   **Atualização 27/10/2026:** mandar a lista não resolveu o app, e a causa NÃO é o preenchimento. Teste com a 214 (chegou do app
   em 26/10, 908 campos, nenhum marcado, ninguém alterou pelo painel): ao baixar no app, as opções também sumiram. O app, ao
   **baixar** uma vistoria do painel, mostra só as opções marcadas (ou nenhuma). Problema do app/sistema da Pleno → suporte.
   Continue mandando a lista completa (é o que o site faz); não gaste tempo procurando outra causa no gravador.
2. **Vaso sanitário:** o Material pode ter as duas opções juntas — "louça" e "descarga caixa acoplada" (quando tem caixa acoplada).
3. **Vídeos:** sempre analisar quando houver. O `preparar.py` tira quadros de cada vídeo para os painéis e mede o som
   (`som_max_db`: campainha/interfone tocando dá som alto); o `zoom.py` abre quadros (`n:vK:segundos`).

## Processo enxuto (um cômodo por vez, retomável)
```bash
python3 vistorias/ferramentas/preparar.py <vis>          # lê em texto, pula o que já está preenchido, monta painéis; imprime ARGS_WORKFLOW
# Workflow: scriptPath vistorias/ferramentas/workflow_preencher.js, args = JSON do ARGS_WORKFLOW
python3 vistorias/ferramentas/status.py <vis> [--detalhe] # confere direto no sistema
```
- O sistema é a fonte da verdade: se a sessão cair, rode `preparar.py` de novo — ele só lista o que ainda falta.
- Por cômodo: modelo **leve** (haiku) nos itens padrão (tomada, interruptor, luminária, ralo...; lista em `vistorias/padrao/classes_itens.json`);
  modelo **forte** em paredes, tetos, pisos, portas, móveis, eletros, bancadas, gabinetes, box e louças, com zoom só onde há suspeita.
  Item padrão suspeito é devolvido pelo leve e reavaliado pelo forte.
- Sem a ferramenta Workflow: rode os mesmos prompts com o Agent tool, um cômodo por vez (leve: `model: haiku`).
- Regras e vocabulário dos agentes: `vistorias/padrao/regras_agente.md` (curto de propósito — não leia arquivos grandes nos agentes).
- Rotas de gravação (descobertas no código do site e testadas): ver `vistorias/README.md`.

## Economia de uso (o que mais pesa)
- O custo vem de **rodadas com muitas imagens no contexto** (cada rodada relê tudo). Agentes curtos por cômodo, todas as imagens lidas
  numa rodada só, zoom em lote (`zoom.py`, 4 fotos por imagem), sem revisor refazendo tudo.
- Comece **cada vistoria numa sessão nova** (contexto pequeno). Esta pasta tem tudo o que é preciso.
- Não monte planilha para o preenchimento; o resumo final vem do `status.py`.

## Padrão de preenchimento (resumo)
Termos exatos da lista do sistema (o `gravar.py` valida). Pintura sempre vazia. Funcionamento "funcionando" (testes do vistoriador).
Estado "Em bom estado" / "Em estado regular". Notas curtas com inicial maiúscula e ponto final, dizendo onde está a avaria.
Observação geral padrão (só com ok): "Testes elétricos realizados. Testes hidráulicos realizados."
Comparativo entrada × saída: processo separado, usado raramente (ver histórico da vistoria 189 no README).
