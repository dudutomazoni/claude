# Ferramentas de vistoria (Pleno)

| Arquivo | O que faz |
|---|---|
| `ferramentas/login.js` | Login no portal (Playwright/Chromium) e captura do token da API. Chamado sozinho pelo `pleno.py` em 401. |
| `ferramentas/pleno.py` | Cliente da API: token, relogin automático, retry, cache da lista de termos. |
| `ferramentas/preparar.py <vis>` | Lê a vistoria, separa itens pendentes por cômodo, classifica padrão/atenção, baixa miniaturas e monta painéis. Somente leitura. |
| `ferramentas/zoom.py <vis> <idx> n:k ...` | Foto original em grade 2x2 (até 4 por imagem), com recorte opcional `n:k@x0,y0,x1,y1`. |
| `ferramentas/gravar.py <vis> <res.json>` | Grava um cômodo (detalhes, campos que faltam, notas, itens novos) e confere relendo do sistema. `--simular` não grava. |
| `ferramentas/status.py <vis>` | Situação por cômodo direto do sistema; `--detalhe` lista os valores. |
| `ferramentas/reparar_opcoes.py <vis> --data AAAA-MM-DD` | Regrava (mesmos valores) campos gravados sem a lista de opções, para o app voltar a mostrar as opções. |
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
| Opções de um campo para um tipo de item (como o site) | `GET tipoDetalheDescricao?tip_det_codigo=&modelo=false&preferir_com_grupo=true&tip_amb_ite_codigo=` (a antiga `tipoDetalheRelacao` saiu na atualização de out/2026) |
| Tipos de item de um tipo de cômodo | `GET tipoAmbienteItem?tip_amb_codigo=&tip_vis_codigo=` |
| Gravar valor de um campo | `PUT detalheDescricao/{det_des_codigo}/update` com o corpo do site (capturado em 22/10/2026): `{det_des_codigo, amb_ite_codigo, cha_codigo:"", med_codigo:"", det_des_ordem, det_des_mod_padrao, tip_det_codigo, tipo_detalhe, tipos_detalhes_descricoes:[valores atuais], startOpen:"", tip_det_des_codigo_array:[códigos marcados], descricoes:[LISTA COMPLETA de opções {tip_det_des_codigo, tip_det_descricao}], path:"ambientes.N.itens", tipoValue:<tip_amb_ite_codigo>, tipoLabel:"tip_amb_ite_codigo"}` — sem `descricoes` o app do telefone fica sem opções. Montado por `pleno.corpo_detalhe`. |
| Criar campo que falta no item | `POST detalheDescricao/store` (mesmo corpo, `det_des_codigo` vazio) e em seguida o PUT acima |
| Criar item | `POST ambienteItem/storeMultiple` `[{amb_ite_quantidade, amb_codigo, tip_ite_codigo, tip_est_codigo:null, tip_vis_codigo}]` |
| Criar campos do item novo (já com valores) | `POST detalheDescricao/storeMultiple` `[{...corpo do site..., uniqId}]` e depois o PUT de cada campo marcado |
| Vídeos | `videos[].path` (mp4) em itens e cômodos; quadros e som extraídos com ffmpeg pelo `preparar.py` |
| Nota de item / de cômodo | `POST nota/store` `{amb_ite_codigo | amb_codigo, not_descricao:"<p>texto</p>", not_ordem}` |
| Apagar item (só com ok) | `DELETE ambienteItem/{id}/destroy` |
| Dados gerais da vistoria (só com ok) | `PUT vistoria/{vis}/update` com só os campos a mudar (ex.: `vis_observacoes`) |
| Inconformidade (só com ok) | `POST inconformidade/store` |

Medidores são salvos pelo botão "Salvar" da tela (`PUT vistoria/{vis}/update` com o formulário inteiro): **não automatizado**.
Códigos de campo: Material 1, Pintura 2, Cor 3, Funcionamento 4, Marca 5, Estado 6, Avarias 7.

## Lições do sistema (juntadas em 03/11/2026 das conversas de cada vistoria)
- Item novo de tipo **sem ligação com o tipo de cômodo**: o `ambienteItem/storeMultiple` responde erro mas às vezes cria o item
  (ex.: decoração, Maquina Lava e Seca na área de serviço, Rodapés/Guarda corpo/Chuveiro na área externa, Área Técnica). O `gravar.py`
  confere `tipoAmbienteItem` antes e, se mesmo assim der erro, localiza o item criado em vez de criar outro.
- Recusas vistas em out/2026 (Quarto sem Cabeceira/Criado mudo, Sala sem banquetas, Área de serviço sem Maquina Lava e Seca) já não
  valem: em 03/11/2026 todos os tipos de cômodo aceitam os 109 tipos de item. O `gravar.py` confere a lista ao vivo antes de criar.
  O que não puder ser item vai na nota do cômodo.
- Cômodos integrados (sala/cozinha/sacada): o agente tende a criar de novo objetos do cômodo vizinho (ex.: cortina) — conferir.
- Nunca apagar itens vazios ou repetidos que sobraram: o Eduardo ajusta manualmente (ou dá o ok para apagar).
- Baixar a vistoria no app mostra só as opções marcadas, mesmo sem nenhum preenchimento nosso (teste com a 214 em 27/10/2026): é do app.

## Histórico
- 189 (One Tower 3701, saída): comparativo entrada × saída com planilha; finalizada pela equipe.
- 190 (Brava Garden 1303 A, saída): 132 itens preenchidos e conferidos (processo antigo, ~2,2 M tokens novos e ~209 M relidos em cache);
  usada como piloto do processo novo nos itens que vieram sem campos; opções regravadas com a lista completa em 22/10.
- 191 (Riviera Concept 1901, saída): 8 cômodos, 138 itens; lavabo criado do zero (14 itens); 3 itens sem foto só com nota.
- 192 (Alameda Jardins 2004): 12 cômodos, 175 itens, 11 sem foto (só nota). Pendências com ok do Eduardo: 2 itens vazios na Sala,
  Janela duplicada na Área de serviço (ele ajusta manualmente).
- 193 (Brava Breeze 702, entrada): 153 itens.
- 194 (Marinas Residence 3301, entrada): 15 cômodos, 267 itens (37 novos, inclusive Área Técnica e lavabo sem itens); 7 sem foto só com nota.
- 195 (Porto Primavera 101, saída, 14/10): 12 cômodos, 182 itens; ficaram 3 itens vazios repetidos (41918, 41919, 41920) e a nota de
  cômodo 1432 dizendo que não foi possível cadastrar: apagar só com ok.
- 196 (Ed San Martin 921, entrada): 63 itens, 0 erros.
- 205 (Ed Roma 803, entrada): 138 itens e 5 novos; tomada e porta papel do banheiro 6 (sem fotos) e colchão do quarto 8 (coberto) só com nota.
- 209 (Ed. Amanda Carolina 103, 21/10): 112 de 113 itens, 9 criados na Área externa e na Área de serviço; a tomada do corredor não
  aparece em nenhuma foto. (Depois foi baixada e reenviada pelo app, o que recria os campos e apaga o rastro das gravações.)
- 210 (Casa Rua Mata Atlântica 5243, entrada): 93 itens (17 criados: Escada, Depósito e Área externa vieram sem itens); ~1,4 M tokens.
- 212 (Ed La Salle 201, entrada, 26/10): 11 cômodos, 185 itens, 182 preenchidos, 3 sem foto só com nota.
- 214 (Império das Ondas 2402, saída, 27/10): 213 itens; lavabo criado do zero (17 itens), 3 novos (persiana, 2 duchas higiênicas).
- 219 (Ed Paris 1101 Bloco B, entrada, 28–29/10): 171 itens, 7 novos (4 na garagem, que veio sem itens), 848 gravações sem erro;
  2 colchões cobertos pela roupa de cama só com nota. Nesta data o portal trocou o botão de login para "Entrar".
- 223 (Porto Rotterdam 601, entrada, 04/11): 13 cômodos, 207 itens (6 criados na Área Técnica, que veio sem itens), 206 preenchidos,
  0 erros; tomada do banheiro 5 sem foto só com nota. O Material de Parede no site só lista Alvenaria, alvenaria com azulejos,
  drywall, gesso e Madeira; para papel de parede existe o termo "Papel de parede" (agora no vocabulário dos agentes).
- 224 (Res Maria Regina Vanzo 1701, entrada, 05/11): 14 cômodos, 260 itens, 258 preenchidos, 1220 gravações sem erro; 9 criados
  (8 na Área Técnica, que veio sem itens, e um prendedor de porta no quarto 13); tomada do quarto 5 e saboneteira do banheiro 6 sem
  foto, só com nota. Bidê (sem tipo no sistema) descrito na nota do vaso nos banheiros 12 e 14; tapete de sisal gravado como "tecido".
- 225 (Residencial Dona Anna 1101, 05/11): 9 cômodos, 152 itens (a Sala já veio preenchida, menos a decoração), 149 preenchidos,
  612 gravações sem erro; 2 criados (criado-mudo no quarto 8, porta shampoo de mármore no banheiro 9). Interruptor e armário aéreo
  da área de serviço e espelho do quarto 6 sem foto, só com nota. Janelas brancas contra a luz tinham saído "preta"/"cinza":
  trocadas para "Branca" com ok do Eduardo (a da cozinha é preta de verdade; a da sacada é cortina de vidro prata).
