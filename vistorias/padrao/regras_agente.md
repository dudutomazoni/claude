# Regras do preenchimento (para os agentes de cada cômodo)

Você preenche itens de UM cômodo de uma vistoria do sistema Pleno olhando as fotos e grava direto no sistema com `gravar.py`.
O dono autorizou gravar o preenchimento sem aprovação prévia. Nunca apague nada, nunca lance inconformidade, não mexa em medidores.

## Economia (obrigatório — o custo vem do número de rodadas com imagens no contexto)
- Rodada 1: leia o arquivo do cômodo. Rodada 2: leia TODOS os painéis que você vai usar de uma vez (várias chamadas Read na mesma resposta). Não releia imagens.
- Zoom só onde houver suspeita de avaria, marca para ler ou dúvida de material: UMA chamada
  `python3 <ferramentas>/zoom.py <vis> <idx> n:k n:k a:k ...` (até 8 fotos; recorte: `n:k@x0,y0,x1,y1` em frações 0-1),
  e leia todas as grades impressas de uma vez. No máximo 2 rodadas de zoom.
- Não abra show.json, fotos.json nem outros arquivos grandes. Não baixe fotos por conta própria.
- Meta: terminar em até 10 rodadas.

## Painéis
Rótulo de cada miniatura: `n.Item fk` = foto k do item n (use `n:k` no zoom); `amb fk` = foto k do cômodo (use `a:k`).
Itens com mais de 30 fotos aparecem em mosaico menor: procure close-ups (o vistoriador fotografa de perto onde há defeito) e confirme no zoom.

## Campos (preencha só os que o item tem em `campos`; Pintura nunca)
- **Material**: plástico, madeira, MDF, MDF embutido sob medida, porcelanato, Revestimento de porcelanato, gesso, led, metal, metal cromado, inox,
  alvenaria, esquadria de alumínio e vidro, vidro, vidro liso, vidro e alumínio, louça, marmore, granito, quartzo, alumínio, vinílico, laminado,
  couro, courino, tecido, Tecido estofado, tecido com espuma, espuma tipo box, tela de lcd, metal com vidro.
- **Cor**: Branca, bege, prata, preta, cinza, bronze, marrom, rosa, dourado, azul, verde (feminino; só "Branca" com maiúscula).
- **Funcionamento**: "funcionando" (padrão: os testes são do vistoriador). Se a FOTO mostrar defeito: "não funcionando" ou "funcionando parcialmente".
- **Marca**: só se legível na foto (Midea, Samsung, LG, Electrolux, Brastemp, Consul, Fischer, Agratto, Gree, Rinnai, Intelbrás, Deca, Docol, Lorenzetti, Tramontina...).
- **Estado**: "Em bom estado" ou "Em estado regular" (regular = avarias relevantes ou espalhadas).
- **Avarias**: manchas, riscos, lascados, rachaduras, fissuras, furos, sinais de umidade, amassados, oxidação, sujeira, trincado, descascando,
  marcas, puxador solto, parte solta, bamba, gordura acumulada. Sem avaria: "".
- Vários valores separados por vírgula ("MDF, marmore"). O gravar.py recusa termo inexistente no sistema: troque por um da lista e rode de novo.

## Notas (frase curta, inicial maiúscula, ponto final)
- O que os campos não dizem: onde está a avaria, descrição do móvel, quantidade. Ex.: "Riscos escuros horizontais e marcas pontuais em algumas paredes." ·
  "Manchas/resíduos de calcário no piso do box." · "4 cadeiras em madeira preta com encosto em X." · "Pequeno amassado na lateral."
- Item sem foto própria: procure nos painéis do cômodo; se não achar, só a nota "Item sem fotos registradas." (campos vazios).
- Item não avaliável: "Colchão embalado em plástico; não foi possível avaliar."
- Reflexo, sombra e sujeira de foto não são avaria. Avaria duvidosa: não marque; escreva na nota "verificar no local".

## Itens novos (só o agente de atenção)
- Cômodo SEM itens (ex.: lavabo): crie os itens a partir das fotos do cômodo (porta, piso, parede, teto, luminária, interruptor, tomada,
  balcão da pia, cuba, torneira, espelho, vaso sanitário, ralo, porta papel...).
- Cômodo com itens: crie item só para objeto relevante visível e não cadastrado (máquina de lavar, banheira, mesa de cabeceira, poltrona...). Utensílios e pertences: não.
- `tipo` precisa ser um destes: Aparador, Aquecedor, Ar condicionado, Armário, Armário aéreo, Balcão, Balcão da pia, Balcão do tanque, Banheira, Banqueta,
  banquetas, Box, Cabeceira, Cadeira, Caixa disjuntora, Cama de casal, Cama de solteiro, Campainha, Cervejeira, Churrasqueira, Chuveiro, Colchão,
  Cortina, Cortina de vidro, Criado mudo, Cuba, decoração, Depurador/coifa, Ducha higiênica, Espelho, Exaustor, Fechadura, Fogão, Forno elétrico,
  Geladeira, Guarda corpo, Interfone, Interruptor, Janela, Luminária, Maquina Lava e Seca, Mesa, Mesa de Centro, Microondas, Parede, Persiana,
  Piso, poltrona, Porta papel, Porta shampoo, Porta, batentes e guarnições, Portão, Prendedor de porta, puff, Rack para tv, Ralo, Rede de proteção,
  Registro de água, Rodapés, Saboneteira, Saída de ar, Sifão, Sofá, Soleira, Suporte para cortina, Tampo da pia, Tampo do tanque, Tanque, Tapete,
  Televisão, Teto, Tomada, Torneira, Trilho para cortina, Varal, Vaso sanitário, Ventilador de teto.
  Objeto sem tipo na lista: descreva na nota do item mais próximo ou na nota do cômodo.

## Resultado e gravação
Salve o JSON em `trabalho/<vis>/res_<idx>_<sufixo>.json` (caminho indicado na tarefa):
```json
{"amb_codigo": 1966,
 "itens": [{"amb_ite_codigo": 40339, "Material": "madeira", "Cor": "Branca", "Funcionamento": "funcionando", "Marca": "",
            "Estado": "Em bom estado", "Avarias": "", "nota": ""}],
 "nota_ambiente": "",
 "novos_itens": [{"tipo": "Vaso sanitário", "qtd": 1, "Material": "louça", "Cor": "Branca", "Funcionamento": "funcionando",
                  "Estado": "Em bom estado", "Avarias": "", "nota": "Vaso com caixa acoplada."}]}
```
Depois rode `python3 <ferramentas>/gravar.py <vis> <arquivo>`. Saída 0 = ok; 2 = termo/tipo rejeitado (corrija o JSON e rode de novo — é seguro,
só grava o que falta); 1 = erro (relate). Responda apenas com o resumo pedido.
