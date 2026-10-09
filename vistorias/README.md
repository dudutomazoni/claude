# Ferramentas de vistoria (Pleno)

| Arquivo | O que faz |
|---|---|
| `ferramentas/login.js` | Login no portal (Playwright/Chromium) e captura do token da API. Chamado sozinho pelo `pleno.py` em 401. |
| `ferramentas/pleno.py` | Cliente da API: token, relogin automático, retry, cache da lista de termos. |
| `ferramentas/preparar.py <vis>` | Lê a vistoria, separa itens pendentes por cômodo, classifica padrão/atenção, baixa miniaturas e monta painéis. Somente leitura. |
| `ferramentas/zoom.py <vis> <idx> n:k ...` | Foto original em grade 2x2 (até 4 por imagem), com recorte opcional `n:k@x0,y0,x1,y1`. |
| `ferramentas/gravar.py <vis> <res.json>` | Grava um cômodo (detalhes, campos que faltam, notas, itens novos) e confere relendo do sistema. `--simular` não grava. |
| `ferramentas/status.py <vis>` | Situação por cômodo direto do sistema; `--detalhe` lista os valores. |
| `ferramentas/workflow_preencher.js` | Workflow: um cômodo por vez, leve + forte em paralelo, reavaliação dos suspeitos. |
| `padrao/regras_agente.md` | Regras e vocabulário curtos para os agentes. |
| `padrao/classes_itens.json` | Itens "padrão" (modelo leve). O resto é "atenção". |
| `padrao/tipos_itens.json` | Catálogo nome → código dos tipos de item (para criar itens novos). |

`trabalho/` (ignorado pelo git) guarda token, painéis, fotos e logs (`trabalho/<vis>/gravacao.jsonl`).

## Rotas da API (mesmas do site; testadas em 09/10/2026)
| Ação | Rota |
|---|---|
| Ler vistoria completa | `GET vistoria/{vis}/show` |
| Ler um item | `GET ambienteItem/{id}/show` |
| Termos aceitos (todos) | `GET tipoDetalheDescricao` |
| Termos sugeridos para um item | `GET tipoDetalheRelacao?tip_det_codigo=&tip_amb_ite_codigo=&tip_vis_codigo=&tip_amb_codigo=` |
| Tipos de item de um tipo de cômodo | `GET tipoAmbienteItem?tip_amb_codigo=&tip_vis_codigo=` |
| Gravar valor de um campo | `PUT detalheDescricao/{det_des_codigo}/update` `{det_des_codigo, amb_ite_codigo, det_des_ordem, tip_det_codigo, tipo_detalhe, tip_det_des_codigo_array:[códigos]}` |
| Criar campo que falta no item | `POST detalheDescricao/store` (mesmo corpo, `det_des_codigo: null`) |
| Criar item | `POST ambienteItem/storeMultiple` `[{amb_ite_quantidade, amb_codigo, tip_ite_codigo, tip_est_codigo:null, tip_vis_codigo}]` |
| Criar campos do item novo (já com valores) | `POST detalheDescricao/storeMultiple` `[{..., tip_det_des_codigo_array, uniqId}]` |
| Nota de item / de cômodo | `POST nota/store` `{amb_ite_codigo | amb_codigo, not_descricao:"<p>texto</p>", not_ordem}` |
| Apagar item (só com ok) | `DELETE ambienteItem/{id}/destroy` |
| Dados gerais da vistoria (só com ok) | `PUT vistoria/{vis}/update` com só os campos a mudar (ex.: `vis_observacoes`) |
| Inconformidade (só com ok) | `POST inconformidade/store` |

Medidores são salvos pelo botão "Salvar" da tela (`PUT vistoria/{vis}/update` com o formulário inteiro): **não automatizado**.
Códigos de campo: Material 1, Pintura 2, Cor 3, Funcionamento 4, Marca 5, Estado 6, Avarias 7.

## Histórico
- 189 (One Tower 3701, saída): comparativo entrada × saída com planilha; finalizada pela equipe.
- 190 (Brava Garden 1303 A, saída): 132 itens preenchidos e conferidos (processo antigo, ~2,2 M tokens novos e ~209 M relidos em cache);
  usada como piloto do processo novo nos itens que vieram sem campos.
