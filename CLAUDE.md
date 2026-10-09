# Plus Vistorias — preenchimento de vistorias no sistema Pleno

Usuário: Eduardo (Plus Vistorias, Balneário Camboriú/SC). Fale em **português simples** (não é técnico).
Portal: https://plusvistorias.sistemaspleno.com · API usada pelo site: https://api.sistemaspleno.com/api/vistoria/

## Autorizações (decididas pelo usuário em 09/10/2026)
- **Preenchimento dos itens** (material, cor, funcionamento, marca, estado, avarias, notas, campos que faltam, itens novos — inclusive
  itens de cômodos sem itens, como lavabos): **gravar direto no sistema, sem pedir aprovação**. Ele confere depois no sistema.
- **Nunca** sem ok explícito naquele momento: apagar qualquer coisa, sobrescrever campo já preenchido, lançar inconformidade,
  mexer em medidores, tipo da vistoria ou observação geral.
- Credenciais só por variável de ambiente `PLENO_USER` / `PLENO_PASS` (configurações do ambiente). Nunca grave senha em arquivo.

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
