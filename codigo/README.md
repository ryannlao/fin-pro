# Fin Pro

Sistema local para **ler boletos em PDF ou foto** e lançar os dados em uma **planilha Excel** que funciona como banco de dados.

Para cada boleto, o sistema extrai:

| Campo | De onde vem |
|---|---|
| **Linha digitável / código de barras** | código de barras da imagem → texto do PDF → OCR → IA (sempre validado pelos dígitos verificadores FEBRABAN) |
| **Beneficiário** (e CPF/CNPJ) | texto do PDF ou OCR, localizado pela posição do rótulo na página |
| **Nº do documento** | texto do PDF ou OCR |
| **Vencimento** | fator de vencimento do código de barras (exato), conferido com a data impressa |
| **Valor** | valor do código de barras (exato), conferido com o valor impresso |
| **Data de lançamento** | gravada automaticamente na planilha |

> Documentação completa, módulo por módulo: [DOCUMENTACAO_FIN_PRO.md](DOCUMENTACAO_FIN_PRO.md).
> Especificação técnica para desenvolver ou reconstruir: [docs/especificacao/](docs/especificacao/00-LEIA-ME.md).

## Para quem vai mexer no sistema

Sistema financeiro de um escritório pequeno (3 pessoas): boletos, Pix, comprovantes, caixa, diesel, gastos, empresas a prazo e
avisos. O dono não é técnico; mudanças precisam ser explicadas em português simples.

**Tecnologia:** Python 3.12 (funciona a partir do 3.10) com FastAPI e Uvicorn; SQLite (3 bancos) com planilhas Excel geradas a
partir dele; telas em HTML/CSS/JavaScript puro (módulos ES, **sem build**); aplicativo Windows com pywebview e pystray; OCR local
(RapidOCR). Node.js só para o ESLint. Não há banco de dados externo nem etapa de compilação.

| Para | Comando (Windows, na pasta do projeto) |
|---|---|
| Instalar e abrir o sistema real (porta 8000, pasta `dados/`) | `iniciar.bat` |
| Demonstração com dados de exemplo (porta 8010, pasta `dados_demo/`, envios bloqueados) | `demonstracao.bat` |
| Verificação completa: Ruff + ESLint + testes (≈5 min) | `verificar.bat` (com `telas`, inclui os testes no navegador) |
| Um arquivo de teste | `.venv\Scripts\python -m pytest tests/test_x.py` |
| Guardar uma versão (roda os testes, grava `VERSOES.md`, commit e etiqueta) | `versoes.bat nova "Título" -m "o que mudou"` |
| Linux ou Mac (só servidor, sem o aplicativo) | `./iniciar.sh` ou `iniciar.command` |

**Onde fica cada coisa:** `app/` servidor e regras (`app/rotas/` é a API, uma pasta por módulo: `boleto/`, `empresas/`, `caixa/`,
`diesel/`, `notificacoes/`); `web/` telas; `tests/` testes; `ferramentas/` versões, restauração e especificação; `dados/` os
dados reais (fora do Git). Mapa completo em [docs/architecture.md](docs/architecture.md) e na seção [Estrutura](#estrutura).

**Regras que não podem ser quebradas:**

- `dados/` tem os dados reais, tokens e senhas de app: não versione, não copie, não teste ali. Teste na demonstração ou com
  uma pasta temporária (`LEITOR_DADOS_DIR`). Nunca apague a planilha do usuário.
- O sistema real roda o dia todo na porta 8000. Para aplicar código novo: `POST http://127.0.0.1:8000/api/app/sair` e depois
  `.venv\Scripts\pythonw.exe -m app`. Nunca mate o processo.
- Testes nunca enviam de verdade (Telegram, e-mail, IMAP). Dois sistemas com o **mesmo token do Telegram** disputam as
  mensagens: não ligue os bots em duas instalações ao mesmo tempo.
- Toda permissão é conferida **no servidor** (`app/acesso.py`, `permissao_da_rota`); esconder um botão não basta. Rota nova
  que junta dados de várias telas precisa conferir cada parte com `acesso.pode`.
- Cada mudança entregue vira uma versão (`versoes.bat nova`). `web/js/app.js` (rotas e permissões das telas) só se mexe com
  autorização do dono.

**Documentação:**

- [Produto e escopo](PRODUCT.md) · [Manual de uso de cada tela](DOCUMENTACAO_FIN_PRO.md) · [O que mudou em cada versão](VERSOES.md)
- [Preparar e rodar](docs/onboarding.md) · [Código e arquitetura](docs/architecture.md) · [Telas e acessibilidade](docs/design.md)
- [Especificação técnica completa](docs/especificacao/00-LEIA-ME.md) (regras, todas as rotas, campos, decisões e lições)
- [Acesso e segurança](docs/especificacao/09-acesso-e-seguranca.md) · [Verificações e revisão](docs/quality.md)
- [Instruções para agentes de IA](AGENTS.md) ([CLAUDE.md](CLAUDE.md) importa as mesmas) · [Ferramentas e evidências do setup](docs/setup.md)

## Versão online (fin.fabbiol.tech)

São **duas instalações separadas** do mesmo código, e cada uma tem os **próprios dados** (não há sincronização entre elas):

| | Computador do escritório | VPS (online) |
|---|---|---|
| Endereço | `http://127.0.0.1:8000` e celulares no Wi-Fi | `https://fin.fabbiol.tech` |
| Como roda | Aplicativo Windows (`iniciar.bat`) | Docker no EasyPanel (`Dockerfile`, `docker-compose.yml`, `requirements.vps.txt`) |
| Dados | `dados/` nesta pasta | `/opt/finpro/dados` no servidor (backup em `/opt/finpro/backup`) |
| Login | Livre no próprio computador, a menos que o administrador exija | Sempre: tudo chega pelo proxy (Traefik), que não é "local" |
| Código vem de | Esta pasta (Git local, etiquetas `vX.Y.Z`) | Pasta `codigo/` do repositório GitHub `ryannlao/fin-pro` |

Variáveis obrigatórias na VPS (aba **Environment** do EasyPanel, se ele não usar o `docker-compose.yml`):
`LEITOR_URL=https://fin.fabbiol.tech` (sem ela toda chamada é recusada com 403 `origem_recusada`) e, enquanto não houver
usuários cadastrados, `LEITOR_SENHA_ACESSO` (sem senha e sem usuários, ninguém de fora entra). Nunca use
`FORWARDED_ALLOW_IPS="*"` no Uvicorn: o endereço falso do cabeçalho passaria a valer como "computador principal".

**Publicar uma mudança:**

1. Aqui: `verificar.bat` e depois `versoes.bat nova "Título" -m "o que mudou"` (cria a etiqueta, ex.: `v1.12.1`).
2. Num clone do repositório do GitHub, num ramo novo, troque a pasta `codigo/` pela versão guardada:
   ```bash
   git rm -rq codigo && mkdir codigo
   git -C "<pasta deste projeto>" archive v1.12.1 | tar -x -C codigo
   git add -A codigo && git commit -m "Atualiza para o Fin Pro v1.12.1"
   git push -u origin <ramo>
   ```
3. No GitHub, abra o Pull Request para o `main` de `ryannlao/fin-pro` (num fork, confira o **base repository**) e aceite.
4. No EasyPanel, clique em **Deploy**. Os dados do servidor não são tocados; só o programa é trocado.

Detalhes da hospedagem e o plano original: [especificação, 11.7](docs/especificacao/11-backup-rede-demonstracao.md).

## Como usar

1. Dê dois cliques em **`iniciar.bat`**.
   Na primeira vez ele cria o ambiente Python e instala as dependências (alguns minutos).
2. O **aplicativo** abre numa janela própria (não é uma aba do navegador) e ganha um ícone perto do relógio.
3. Em **Configurações → Aplicativo no computador**, clique em **Criar atalhos** (Área de Trabalho e Menu Iniciar)
   e ligue **Iniciar junto com o Windows**.
4. Em **Ler boletos**, arraste PDFs/fotos, clique em *Escolher arquivos*, use *Tirar foto* (no celular) ou cole com `Ctrl+V`.
5. Confira os campos (os de baixa confiança ficam em amarelo), escolha o **centro de custo** e clique em **Lançar na planilha**.

A planilha fica em `dados\boletos.xlsx`.

## Aplicativo de desktop

- Janela própria com o motor do Microsoft Edge (WebView2, já presente no Windows 10/11) e ícone na bandeja
  (perto do relógio) com atalhos para Ler boletos, Boletos, Pix, Gastos e Sair.
- **Fechar a janela (X) esconde o aplicativo na bandeja**: os lembretes continuam chegando. Para encerrar,
  clique com o botão direito no ícone → **Sair**. Dá para mudar isso em Configurações.
- **Iniciar junto com o Windows** (opcional: **minimizado na bandeja**). Abrir o atalho com o app já aberto só traz a janela para a frente.
- Clicar numa notificação do Windows traz o aplicativo para a frente, já na tela certa.
- Modo antigo, pelo navegador: `python -m app --navegador`. O registro de funcionamento fica em `dados\leitor.log`.

## Pagamentos Pix

Aba **Pagamentos Pix**, com o mesmo fluxo dos boletos (lembretes de vencimento, marcar como pago, exportar):

- **Tipo da chave**: CNPJ/CPF, Celular, E-mail (e chave aleatória), com máscara e validação (dígitos do CPF/CNPJ, DDD do celular…)
- **Valor do Pix**, recebedor, data prevista, **centro de custo** e descrição
- **Pix Copia e Cola**: cole o código (em qualquer tela, com `Ctrl+V`) e chave, valor, recebedor e identificador são preenchidos
- **QR code**: envie o print, a foto ou o PDF da cobrança; na tela *Ler boletos*, arquivos sem boleto mas com QR Pix
  oferecem **Lançar como Pix**
- Para cada Pix lançado, o botão de QR code mostra o QR e o Copia e Cola para pagar no app do banco
- Pix repetido (mesmo Copia e Cola) é bloqueado, como os boletos duplicados

## Importar boletos de outro sistema

Fica em **Configurações → Importar boletos de outro sistema** e é uma **área restrita**:

- Na primeira vez, crie a **senha de administrador** (só pode ser criada e trocada no próprio computador; trocar exige a senha atual).
- A senha é conferida no servidor: sem ela, a importação não funciona nem acessando a API diretamente.
- Após 5 senhas erradas, o aparelho fica bloqueado por 5 minutos. A área se fecha sozinha após 20 minutos sem uso
  (ou no botão **Bloquear**), e trocar a senha bloqueia os aparelhos que estavam liberados.
- A senha fica guardada com hash em `dados\admin.json`. Esqueceu? Feche o sistema, apague esse arquivo e crie outra.

Com a área liberada:

1. Exporte as contas a pagar / boletos do outro sistema para **Excel (.xlsx ou .xls), CSV ou TXT** e envie o arquivo.
2. As colunas são reconhecidas pelo nome, inclusive com sinônimos comuns ("Fornecedor", "Cedente", "Vencto",
   "Valor Título", "Cód. Barras", "Situação", "C. Custo"…). Confira e ajuste o que precisar; dá para escolher a aba
   e a linha dos títulos, além do centro de custo e da situação para quando o arquivo não informar.
3. A **prévia** confere cada linha: linha digitável (dígitos verificadores), valor e vencimento (e se batem com o
   código de barras), boletos **já lançados** na planilha e **repetidos** no próprio arquivo. Linhas de total são ignoradas.
4. Clique em **Importar**: tudo é gravado de uma vez (também funciona com a planilha aberta no Excel).

- Situações como "Pago", "Liquidado" ou "Baixado" (ou uma data de pagamento) entram como pagos; "Em aberto" como pendente.
- As colunas escolhidas ficam salvas (`dados\importacao_modelos.json`) e são reconhecidas sozinhas na próxima vez.
- Há uma **planilha modelo** para download, útil quando o outro sistema permite escolher as colunas exportadas.
- Dica: exporte a linha digitável como **texto** — em formato de número, o Excel arredonda os dígitos.

## Centros de custo e análise de gastos

- Cada boleto e cada Pix pode ter um **centro de custo** — onde o dinheiro foi gasto (uma obra, um setor, um veículo…).
  Escolha na revisão da leitura, na edição, em lote (selecione vários boletos → *Centro de custo*) ou crie um novo na hora.
- Aba **Gastos → Análise de gastos**: total por centro de custo (boletos + Pix), gráfico por mês, detalhamento com
  pagos/pendentes, maiores beneficiários e exportação para Excel. Filtre por período, data (vencimento, pagamento ou
  lançamento), situação e tipo.
- Aba **Gastos → Centros de custo**: criar, renomear (os lançamentos antigos acompanham) e desativar.
- Aba **Gastos → Fechamento do mês**: resumo do mês para o contador (total, pago, em aberto, em atraso, por centro de custo,
  quem pagou e se tem comprovante). Base: *tudo que vence no mês* ou *só o que foi pago no mês*. Baixe em **Excel**, **PDF**
  ou o **pacote para o contador (.zip)**, com o PDF, a planilha e os comprovantes anexados.

## Banco de dados e planilha Excel

- Os dados ficam num **banco de dados** (SQLite) em `dados\boletos.db`: gravação instantânea, mesmo com muitos lançamentos.
- A **planilha `boletos.xlsx` continua existindo**, no mesmo formato, e é gerada automaticamente poucos segundos depois de
  cada alteração (abas Boletos, Pix, Centros de Custo, Resumo e Histórico).
- **Pode deixar a planilha aberta no Excel:** nada fica esperando; a planilha é atualizada quando o arquivo for fechado.
- **Editou no Excel e salvou?** As alterações em lançamentos que já existem (status, centro de custo, observações…) voltam
  para o sistema sozinhas, sem desfazer o que o sistema gravou nesse meio-tempo. Para lançar ou excluir, use o sistema.
- Cópia diária do banco e da planilha em `dados\backups` (30 dias), além do backup fora do computador.

## Saúde do sistema

Em **Configurações → Saúde do sistema**: um diagnóstico do que roda sozinho — banco de dados e planilha, lembretes,
backup, recebimento por e-mail/Telegram, gravações pendentes, leitura (OCR/IA), espaço em disco e acesso pelo celular.
Cada item mostra "Funcionando", "Atenção", "Problema" ou "Desligado", com botões para **atualizar a planilha agora** e
**limpar os logs**. O arquivo `dados\leitor.log` gira sozinho a cada 2 MB (guarda 5 arquivos).

## Previsão de saídas

No **Painel**: quanto vai sair em cada uma das próximas 8 semanas (boletos + Pix pendentes), com o que já está em atraso
à parte e os totais de 7 e 30 dias. Clique numa semana para ver os lançamentos dela.

## Empresas, notas fiscais e fechamentos (vendas a prazo)

Enquanto o resto do sistema cuida do que a empresa **paga**, este módulo cuida do que ela **recebe** dos clientes
que compram a prazo. Tudo chega por um **bot do Telegram só para isso** (outro token, criado no @BotFather), que
reconhece sozinho o que é cada arquivo:

| O que você manda | O que o sistema faz |
| --- | --- |
| **Nota fiscal** (XML da NF-e, DANFE em PDF ou foto) | identifica a empresa, lança cada material como uma linha do fechamento (data, material, unidade, quantidade, valor unitário, total, NF e pedido) e responde com o total do fechamento |
| **Cheque escaneado** (frente e verso) | lê a foto nas quatro orientações, entende o **"Bom p/ 24/09/26"** escrito à mão, o valor, banco, agência, cooperativa, conta e número do cheque, descobre a empresa pelo CNPJ impresso e pega a **lista de pedidos escrita no verso** |
| **Comprovante** de Pix, TED ou depósito | dá **baixa automática** nas notas citadas e responde quanto ainda falta daquele fechamento |
| **Print do fechamento** que já estava em andamento | lê a tabela linha por linha para você conferir e importar (é assim que o módulo começa a operar) |

**Fechamento** — cada empresa fecha no **dia 20** (ou no dia escolhido para ela). O fechamento de agosto, por
exemplo, vai de 21/07 a 20/08: a nota entra pelo dia em que foi emitida. Dá para **mudar o fechamento de uma nota**
(lápis na linha → campo *Fechamento*), inclusive movendo todas as linhas da mesma NF de uma vez — útil quando a nota
chega depois de você já ter fechado o mês. No dia do fechamento, o bot envia sozinho
o resumo de cada empresa. O relatório sai em **Excel e PDF no mesmo formato da planilha usada hoje** (cabeçalho com
a sua empresa e o CNPJ, "Fechamento <Empresa>" e as colunas DATA, MATERIAL, UNIDADE, QUANT., VALOR UNI., VALOR
TOTAL, NOTA FISCAL e Nº PEDIDO, com o total no rodapé).

**Baixa automática** — o valor recebido é dividido entre as notas citadas no comprovante, da mais antiga para a
mais nova. Sem o número da NF, baixa as mais antigas em aberto. Quando o valor não cobre tudo, a nota fica
*Parcial* e o fechamento mostra quanto falta; o que sobra vira **crédito da empresa** e baixa sozinho quando a
próxima nota chega. Dá para desfazer qualquer recebimento (as notas voltam a ficar em aberto).

**Cheques pré-datados** — ficam guardados com número, banco, agência, cooperativa, conta, valor e a data do
depósito. As notas dos pedidos citados ficam *Em cheque* (o dinheiro ainda não entrou) e o cheque entra nos
**mesmos avisos de vencimento** dos boletos e Pix ("Cheque para depositar hoje"). Quando o cheque compensa — pelo
comprovante do depósito ou pelo botão *Compensou* — vira um recebimento e as notas recebem baixa.

**Comandos do bot de notas** (só para quem está cadastrado): `/fechamento <empresa>`, `/empresas`, `/cheques`,
`/notas <empresa>` e `/ajuda`.

Na tela **Empresas**: Fechamentos (cartão por empresa com o total, o recebido e o que falta), Notas fiscais,
Cheques, Recebimentos, Conferência (o que o robô não teve certeza) e Bot de notas (token, quem pode enviar, a sua
empresa e o dia do fechamento). Os dados ficam em `dados\empresas.db`, com a planilha `fechamentos.xlsx` gerada
automaticamente (abas Empresas, Notas Fiscais, Cheques, Recebimentos e Histórico) e backup diário.

## Caixa (dinheiro que entra e que sai)

- Em **Caixa**, lance **entradas** (com o campo *O que foi pedido*) e **saídas** (o que foi comprado, onde foi gasto e o
  centro de custo). Veja tudo por **dia, semana, mês ou ano**, navegando pelas setas ‹ ›.
- Cartões com **entradas, saídas, saldo do período e saldo em caixa** (tudo o que entrou menos tudo o que saiu até o
  fim do período). O Excel do período traz o resumo e todos os lançamentos.
- **Relatórios**: onde mais se gastou (por loja/fornecedor), por centro de custo, quem mais gastou, entradas por pedido,
  gasto médio, maior saída, comparação com o período anterior e os gráficos de entradas e saídas.
- As **saídas em dinheiro entram na aba Gastos** (filtro *Só dinheiro (caixa)*, coluna *Dinheiro*) e no **fechamento
  do mês para o contador**, com a foto do cupom no ZIP.
- **Bot do caixa** (Telegram, um terceiro bot, token em Caixa → Bot do caixa): quem já está no bot dos boletos ou no bot
  de notas manda a **foto do cupom ou da nota**. O bot lê o valor (o *a pagar*, nunca o troco), a data e a loja,
  pergunta **onde foi gasto**, mostra os **centros de custo como botões** — com a opção de **cadastrar um novo** — e deixa
  tudo preenchido em **Caixa → Conferência** para revisar e lançar. Comandos: `/resumo`, `/cancelar` e `/ajuda`.
- Os lançamentos ficam na aba **Caixa** da planilha `boletos.xlsx`, com histórico e backup. Permissão: **Caixa**.

## Diesel (compras no posto e abastecimentos das máquinas)

Menu **Diesel**. O saldo é **em reais**: o que foi pago nas compras menos o valor de cada abastecimento (litros × preço do
combustível). A compra da semana serve para S10 e comum; o painel mostra quantos litros de cada um o saldo ainda compra.

- **Bot do diesel** (Telegram, mais um bot — token em Diesel → Bot do diesel). Quem já está no bot dos boletos ou no
  bot de notas manda para ele:
  - a **foto do canhoto** de cada abastecimento: o bot lê os litros (pergunta a quem mandou, se não conseguir) e manda
    a foto para o **responsável** com as máquinas em botões. Ele toca na máquina, informa o horímetro/km (ou pula) e os
    litros saem do saldo. O bot responde com o **saldo** e a **média da máquina**; quem mandou o canhoto é avisado.
    O caminhão com a placa cadastrada já vem marcado. Dá para **cadastrar uma máquina nova** e **corrigir os litros**
    pelos botões.
  - o **comprovante de pagamento** da compra (botão rápido de 1.000 L): os litros entram no saldo.
  - Comandos: `/saldo`, `/medias`, `/relatorio` (`/relatorio mes`, `/relatorio mes detalhado`, `/relatorio ano completo`), `/maquinas`.
- **Relatórios automáticos** no Telegram do responsável: **semanal** (segunda), **quinzenal** (dias 1 e 16) e
  **mensal** (dia 1), com o consumo de cada máquina, no nível escolhido (Simples, Detalhado ou Completo). Aviso quando o
  saldo fica abaixo de um limite (padrão R$ 1.000).
- **Consumo de verdade:** com o horímetro (máquinas, geradores) ou o km (caminhões) em cada canhoto, o sistema calcula
  **litros por hora** ou **km por litro**. Sem eles, mostra litros por dia, por semana e por abastecimento.
- Na tela: **Painel** (saldo, comprado x abastecido, preço médio do litro, lançamentos), **Máquinas** (cadastro e média
  de 30 dias), **Relatórios** (semana, quinzena, mês ou ano, com Excel e "Enviar no Telegram"), **Conferência** (o que
  ficou sem resposta no Telegram) e **Bot do diesel**.
- **Mandar pela tela, sem o bot:** botão **Enviar canhoto ou comprovante** no Diesel (ou arraste o arquivo para a tela).
  O sistema lê e abre o formulário já preenchido para conferir e lançar.
- **Vários combustíveis no mesmo canhoto:** cada linha (ex.: 200 L de Diesel comum a R$ 6,75 e 200 L de Diesel S10 a
  R$ 7,45) vira um abastecimento, e cada uma pode ir para uma **máquina diferente**. O leitor confere a conta
  (litros × preço = total) e acerta os números tortos da foto pelos totais do rodapé. No bot, o responsável escolhe a
  máquina de cada linha.
- **Combustível:** reconhecido no canhoto (Diesel S10, Diesel comum/S500, Gasolina, Etanol, Arla 32). Cada máquina tem o
  seu (completa a linha que não diz qual é e aparece primeiro na lista).
- **Preço do litro:** cartão *Preço do litro* no painel — o que vocês pagam em cada combustível. Vale para o canhoto que
  não traz o preço; quando o canhoto ou a compra trazem, vale o deles. O custo de cada máquina usa o valor real.
- Os dados ficam em `dados\diesel.db` e na planilha `dados\diesel.xlsx` (abas Máquinas, Compras e Abastecimentos), com
  histórico e backup. Canhotos e comprovantes aparecem na busca de **Comprovantes**. Permissão: **Diesel**.

## Comprovantes (buscar e baixar)

No menu **Comprovantes** ficam os arquivos de todas as partes do sistema num lugar só: comprovantes de **boletos** e
**Pix**, fotos dos **cheques**, comprovantes dos **recebimentos** das empresas (Pix, TED, depósito), cupons do **caixa**
e **notas fiscais**.

- Filtros: busca por nome (beneficiário, empresa, recebedor, pedido, material), **tipo**, **período** (com atalhos:
  hoje, esta semana, este mês, mês passado…), **valor** (o valor do boleto ou o valor pago com juros) ou faixa de valor,
  **número** (cheque, NF, documento, pedido, ID da transação ou um trecho da linha digitável), centro de custo e quem pagou.
- **Ver**: abre o comprovante na tela com os dados ao lado; as setas ‹ › (ou do teclado) passam para o próximo.
- **Baixar comprovantes (.zip)**: baixa todos os que estão filtrados, com nomes como
  `2026-09-21 - Boleto - IMPORCATE - n2.715.287 - R$ 956,70.pdf`, separados em pastas por tipo.
- **Pagos sem comprovante**: lista o que já foi pago e ainda não tem comprovante, com o botão **Anexar**.
- Atalhos em Boletos lançados, Pagamentos Pix, Caixa e Empresas (Cheques e Recebimentos) já abrem a busca filtrada.
- Cada pessoa só vê os comprovantes das partes que tem permissão (Empresas, Caixa).

## Versão de demonstração (para mostrar a clientes)

Dê dois cliques em **`demonstracao.bat`**. Abre um Fin Pro completo, com dados de exemplo, na porta **8010** —
pode ficar aberto ao mesmo tempo que o sistema de verdade (porta 8000).

- Os dados ficam em `dados_demo` (boletos pagos, pendentes e atrasados, Pix, caixa, três empresas com notas,
  cheques e recebimentos, centros de custo, usuários e permissões, lembretes e resumos da semana ligados).
- **Nada é enviado para fora:** Telegram e e-mail aparecem configurados nas telas, mas o envio fica bloqueado.
  A janela mostra o selo *Versão de demonstração*.
- Abre direto, sem pedir senha. Para mostrar as permissões, entre com **demo / demo1234** (administrador),
  **almir / demo1234** ou **juliana / demo1234**.
- Para montar os dados do zero de novo: `demonstracao.bat --refazer`.
- Os dados reais (pasta `dados`) nunca são tocados.

## Usuários, administrador e permissões

- Em **Configurações → Usuários e acesso** cadastre cada pessoa com login e senha (a primeira vez pede a senha de
  administrador; depois, quem tem o perfil de **administrador** entra com o próprio usuário e gerencia tudo).
- Cada pessoa tem um **perfil**:
  - **Administrador** — pode tudo, inclusive cadastrar usuários e mudar as permissões dos outros;
  - **Comum** — só o que estiver marcado. Ver o painel, os boletos e os Pix é liberado para todo mundo.
- **Permissões** (botão 🛡 na lista de usuários):

  | Permissão | O que libera |
  | --- | --- |
  | Lançar | Ler arquivos e lançar boletos e Pix |
  | Dar baixa | Marcar como pago e anexar comprovante |
  | Editar/excluir | Editar e excluir lançamentos |
  | Gastos | Análise de gastos e fechamento do mês |
  | Empresas | Notas fiscais, cheques, recebimentos e fechamentos dos clientes |
  | Caixa | Entradas e saídas em dinheiro e o bot do caixa |
  | Avisos | Configurar os lembretes de vencimento |
  | Configurações | Backup, bots, importação e acesso pela rede |

  Quem não tem a permissão nem vê a opção no menu, e o servidor recusa a ação mesmo que alguém tente pelo endereço.
- O sistema não deixa ficar **sem nenhum administrador** (não dá para excluir, desativar ou rebaixar o último).
- Com usuários cadastrados, os aparelhos da rede pedem **usuário e senha** (a senha única de acesso deixa de valer).
  Neste computador o login é opcional — quem não entra aparece como "Computador principal" —, a menos que você ligue
  **Pedir login também neste computador**.
- **Pedir usuário e senha toda vez que o aplicativo abrir**: ao abrir o Fin Pro, quem estava conectado neste
  computador entra de novo. Celulares e outros aparelhos continuam conectados por 30 dias.
- A planilha registra **Lançado por** e **Pago por**, e a aba **Histórico** ganhou a coluna **Usuário**.
- Nas listas de boletos e Pix, o botão com relógio abre **Histórico e comprovante**: quem lançou, quem pagou e todas as alterações.
- Cada pessoa troca a própria senha no menu lateral. Desativar ou trocar a senha de alguém desconecta os aparelhos dessa pessoa.
- Senhas guardadas só em hash (`dados\usuarios.json`); após 5 senhas erradas, o aparelho espera 5 minutos.

## Comprovantes de pagamento (baixa automática)

Envie o comprovante (PDF ou foto) e o sistema faz a baixa sozinho:

- **Reconhece** que é um comprovante (e não um boleto) e lê: valor pago, valor do documento, juros/multa, desconto,
  data do pagamento, vencimento, beneficiário, CNPJ, chave Pix e a linha digitável (quando o banco imprime).
- **Descobre de qual lançamento é**: linha digitável igual resolve na hora; senão compara valor, CNPJ, nome, vencimento
  e data. Quando há dúvida (ex.: parcelas iguais), mostra os lançamentos possíveis para alguém escolher.
- **Marca como pago** com a data do comprovante e grava **Valor Pago**, **Juros/Multa** e **Desconto** (colunas novas da
  planilha). Se o comprovante não detalhar, a diferença entre o valor pago e o do boleto vira juros (a mais) ou desconto (a menos).
- Comprovante de **agendamento** não dá baixa (o pagamento ainda não aconteceu).

Onde enviar: em **Ler boletos** (arrastar, escolher ou colar), pelo **bot do Telegram**, por **e-mail**, ou no botão com
relógio/clipe da lista (**Histórico e comprovante → Anexar comprovante**). Na tela há **Desfazer** logo após a baixa.

O bot do Telegram responde, por exemplo: "✅ Pagamento registrado: CLA AUTO PECAS · Valor do boleto R$ 270,35 · Valor pago
R$ 275,75 em 15/10/2026 · Juros/multa R$ 5,40 (5 dia(s) de atraso)".

O **Fechamento do mês** soma o valor efetivamente pago, os juros e multas, os descontos e quantos foram pagos com atraso.

## Receber boletos por e-mail e Telegram

Em **Configurações → Receber boletos por e-mail e Telegram** (senha de administrador):

- **E-mail:** informe a caixa (IMAP — Gmail, Outlook, Yahoo, UOL…) com uma **senha de app**. A cada 5 minutos o sistema lê
  os PDFs e fotos anexados. Os e-mails não são apagados nem marcados como lidos. Na primeira vez, olha os últimos 7 dias.
  Opcional: aceitar só alguns remetentes (ex.: `energisa.com.br`).
- **Telegram:** as pessoas cadastradas em Notificações → Telegram encaminham a foto ou o PDF do boleto para o bot, que
  responde com o que leu. Arquivos de quem não está cadastrado são recusados.
- **Comandos do bot** (só para quem está cadastrado; aparecem no menu "/" do Telegram):
  `/vencidos`, `/hoje`, `/semana`, `/previsao`, `/resumo`, `/buscar <nome>` e `/ajuda`. As listas trazem a **linha digitável**
  (e o **Pix Copia e Cola**) prontos para copiar e pagar pelo celular — depois é só mandar o comprovante para o bot dar baixa.
- Tudo o que chega aparece em **Ler boletos → Recebidos por e-mail e Telegram** (com contador azul no menu).
  Boletos não são lançados sem conferência: clique em **Revisar**, confira e lance — ou descarte. Arquivos repetidos são
  ignorados e boletos que já estavam lançados saem sozinhos da caixa.
- **Comprovantes** que chegam por e-mail ou Telegram dão baixa automática no boleto/Pix certo (veja acima).

## Backup total fora do computador

Em **Configurações → Backup total fora do computador** (senha de administrador) escolha uma pasta do **OneDrive**,
**Google Drive**, **Dropbox**, um **pen drive** ou **HD externo**. Todo dia, no horário escolhido (ou assim que o computador
ligar, se passou da hora), o sistema copia **tudo** para a pasta `Leitor de Boletos - Backup`:

| Pasta / arquivo | O que guarda |
|---|---|
| `planilha\` | os três bancos de dados (boletos, empresas, diesel) e as planilhas — uma cópia por dia (30 dias, ajustável) |
| `arquivos\` | PDFs, fotos, comprovantes, cupons e canhotos (só o que é novo ou mudou) |
| `configuracoes\` | todas as configurações (lembretes, usuários, bots, preços, modelos) e o `.env` |
| `codigo\` | o **código-fonte** do sistema, espelhado |
| `versoes\` | o **histórico de versões** inteiro (`finpro.bundle`) e a versão em uso (`VERSAO.txt`) |
| `pacotes\` | **pacote completo** num único `.zip` — toda semana ou todo mês; guarda os últimos 4 (ajustável) |
| `manifesto.json` | a lista de tudo, com a impressão digital (SHA-256) de cada arquivo |
| `RESTAURAR.bat` · `LEIA-ME.txt` | restauração com dois cliques e o passo a passo |

- **Fazer backup agora**, **Gerar pacote completo (.zip)** e **Verificar backup** ficam no mesmo cartão.
- **Conferência**: depois de cada backup o sistema confere se os bancos abrem, se não falta nenhum comprovante e se o
  código e as versões estão lá. O botão **Verificar backup** confere arquivo por arquivo. Se algo falhar, aparece no
  cartão e na **Saúde do sistema**.
- **Restaurar em outro computador**: instale o Python, abra a pasta do backup e dê dois cliques em `RESTAURAR.bat`
  (ou `python restaurar_backup.py <backup ou pacote.zip> <pasta de destino>`). Volta o sistema inteiro: programa, dados,
  comprovantes, configurações e versões. Se o destino já tiver dados, ele para em vez de sobrescrever.
- A pasta do backup guarda os tokens dos bots e as senhas de e-mail: mantenha-a num lugar de confiança.

O menu lateral mostra **Backup em dia**, **Backup atrasado** (mais de 2 dias) ou **Backup desligado**. A cópia diária
interna em `dados\backups` continua existindo.

## Controle de versão

O código do sistema fica guardado em **versões** (repositório git local, só neste computador — sem dados, senhas ou
tokens). Cada versão tem número, data e a lista do que mudou, em [VERSOES.md](VERSOES.md). Em **Configurações → Geral**,
o cartão **Versão do sistema** mostra a versão em uso, o histórico e se há alterações ainda não guardadas.

| Comando (na pasta do sistema) | O que faz |
|---|---|
| `versoes.bat situacao` | versão em uso e o que mudou desde a última versão guardada |
| `versoes.bat nova "Título" -m "o que mudou"` | roda os testes e guarda uma versão nova (`--tipo correcao`, `melhoria` ou `grande`) |
| `versoes.bat listar` | todas as versões |
| `versoes.bat comparar v1.8.0 v1.9.0` | arquivos que mudaram entre duas versões |
| `versoes.bat voltar v1.8.0` | volta o **programa** para aquela versão (vira uma versão nova; os dados não são tocados) |

As versões guardam só o programa; quem protege os dados é o backup — que também leva o código e este histórico.

## Site de apresentação

A pasta `site\` tem uma página que explica o Fin Pro inteiro, no estilo de página de venda: todos os módulos, os bots,
segurança, backup, ficha técnica, perguntas frequentes e um **leitor de linha digitável** que funciona na própria página.
Abra `site\index.html` no navegador, ou copie a pasta `site` (o `index.html` e a pasta `img`) para qualquer hospedagem.

| Arquivo | Para que serve |
|---|---|
| `site\index.html` | A página pronta |
| `site\img\` | As telas, tiradas do sistema com dados de exemplo e nomes inventados |
| `site\partes\` | Os pedaços de onde a página é montada (estilo, cada grupo de seções e o script) |
| `python site\montar.py` | Junta os pedaços e gera o `index.html` de novo |
| `python site\capturar_telas.py` | Refaz as capturas de tela a partir do sistema atual (usa o Microsoft Edge) |

Para mudar um texto, edite o pedaço em `site\partes` e rode `python site\montar.py`.

> Requisito: Python 3.10 ou superior (<https://www.python.org/downloads/>), com a opção "Add to PATH" marcada.

## Funcionalidades

**Leitura**
- PDFs digitais, PDFs escaneados e fotos (JPG, PNG, WEBP, HEIC do iPhone)
- Vários arquivos de uma vez, com fila, progresso e até 2 leituras simultâneas
- Carnês/PDFs com vários boletos (um por página ou vários na mesma página)
- Boletos **bancários** (47 dígitos) e de **arrecadação**: contas de consumo e tributos (48 dígitos)
- OCR local com modelo **latino** (PP-OCRv5): lê acentos e espaços do português
- **Modo scanner** para fotos de papel: recorta o papel, corrige a perspectiva e uniformiza a iluminação
- Fotos giradas são endireitadas pela orientação do código de barras
- Várias estratégias para ler códigos de barras borrados (binarizações, escalas, reforço das barras)
- **PDFs escaneados** com texto ruim do scanner recebem OCR complementar para preencher o que faltar
- **Guias de tributos** (DAS, DARF, GPS, FGTS, IPVA, IPTU, DETRAN): o beneficiário é o órgão arrecadador
- **Contas de consumo** sem rótulo "Beneficiário": o nome da empresa é lido do cabeçalho
- Correção automática de dígitos lidos errados (um por campo), priorizando confusões típicas de OCR (8↔3, 5↔6…)
  e desempatando pelo valor e vencimento impressos
- Datas por extenso ("10 de outubro de 2026", "10/OUT/2026") e ligaduras tipográficas de PDF
- Novo ciclo do fator de vencimento (reiniciado em 22/02/2025)
- Alertas: linha inválida, valor ou vencimento divergente, boleto vencido, campos ausentes, **boleto já lançado**
- Digitação/colagem manual da linha digitável
- **IA opcional (Claude)** para fotos difíceis. A linha digitável sugerida pela IA também passa pela validação dos DVs.

**Planilha (banco de dados)**
- Aba *Boletos* com cabeçalho formatado, filtros, lista de status e vencidos destacados (inclui a coluna *Centro de Custo*)
- Aba *Pix* com tipo e chave, valor, recebedor, data prevista, centro de custo e Copia e Cola
- Aba *Resumo* com fórmulas: pendentes, vencidos, próximos 7 dias e pagos (boletos e Pix)
- Aba *Centros de Custo* com os centros cadastrados (planilhas antigas ganham as abas novas automaticamente)
- Aba *Histórico* com cada lançamento, edição, pagamento e exclusão (data/hora e o que mudou)
- **Planilha aberta no Excel não trava o sistema:** lançamentos e mudanças de status ficam numa fila
  (`dados\gravacao_pendente.json`) e são gravados sozinhos, de uma vez, quando o arquivo é fechado
- Lançamento de vários boletos numa única gravação; gravação atômica e backup diário automático (`dados\backups`)
- Arquivo original de cada boleto guardado e vinculado ao registro (link clicável na planilha)

**Telas**
- **Painel**: indicadores (a pagar, vencidos, próximos 7 dias, pagos no mês), gráfico por mês, próximos vencimentos, vencidos e maiores beneficiários
- **Ler boletos**: leitura em segundo plano com barra de progresso por página (PDFs escaneados) e cache do OCR
- **Boletos lançados**: busca, filtros por situação e período, ordenação, paginação, ações em lote (pagar, cancelar, excluir), edição e exportação para Excel/CSV
- **Calendário de vencimentos**: visão do mês com total por dia e cores por situação; clique no dia para pagar, copiar a linha ou editar
- **Pagamentos Pix** e **Gastos** (análise por centro de custo), descritos acima
- **Empresas**: fechamento por cliente no formato da planilha usada hoje, notas fiscais, cheques pré-datados,
  recebimentos com baixa automática e conferência do que chega pelo bot de notas
- **Configurações**: aplicativo (iniciar com o Windows, bandeja, atalhos), acesso pelo celular, planilha e ajuda
- Tema claro/escuro, layout responsivo e atalhos de teclado

## Notificações de vencimento

Na tela **Notificações** você cadastra os **lembretes**, cada um com seus horários e canais:

| Lembrete | Padrão |
|---|---|
| **No dia do vencimento** | 3 vezes: 08:00, 12:00 e 16:00 (atalhos para 1, 3 ou 5 vezes; adicione/remova horários à vontade) |
| **Antes do vencimento** | 1 dia antes e 3 dias antes, às 09:00 (crie quantos quiser: 2, 5, 7 dias…) |
| **Depois de vencido** | Todo dia às 09:00, por até 30 dias (0 = até pagar) |

Também dá para escolher os dias da semana em que os avisos são enviados. A tela mostra a **agenda dos próximos
lembretes** com os boletos atuais. Os lembretes param quando o boleto é marcado como pago — inclusive pelo botão
**Já paguei** da notificação do Windows. Canais:

| Canal | Como configurar |
|---|---|
| **Windows** | Já vem ligado. A notificação aparece no canto da tela; clicar abre os boletos pendentes. |
| **Telegram** (celular) | Crie um bot no @BotFather e cole o token. Cada pessoa do escritório abre o bot e envia `/start` (ou adicione o bot ao grupo do escritório); clique em *Procurar pessoas e grupos* e marque quem recebe. |
| **E-mail** | Escolha o provedor (Gmail, Outlook, Yahoo), informe usuário, **senha de app** e destinatários. |

- O sistema confere os lembretes a cada minuto. Cada boleto é avisado uma vez em cada horário; se o computador
  estava desligado e um horário passou, só o lembrete mais recente é enviado (sem acumular).
- Boletos com vencimento no fim de semana trazem o lembrete de que podem ser pagos no próximo dia útil.
- Os lembretes valem também para os **Pix** pendentes (pela data prevista).
- Ligue **Iniciar junto com o Windows** (Configurações → Aplicativo) para receber os avisos sem abrir o sistema.
- O sininho no topo mostra os boletos a vencer a qualquer momento; o histórico registra cada envio.
- Configurações e histórico ficam em `dados\notificacoes.json` (inclui token/senha — guarde o computador com segurança).

### Resumos da semana

No cartão **Resumos da semana** (tela Notificações), cada resumo tem o seu horário e os seus canais:

- **Segunda-feira** (padrão 08:00): boletos e Pix que vencem na semana, os vencidos em aberto, os cheques a
  depositar, os fechamentos das empresas que caem na semana, quanto as empresas ainda devem e o saldo do caixa.
- **Sexta-feira** (padrão 17:00): quanto foi pago na semana em **boletos, Pix e saídas do caixa**, os maiores
  pagamentos, os **juros e multas pagos** (quais boletos/Pix e com quantos dias de atraso) e os descontos, onde mais se gastou (centro de custo), o que entrou (caixa e recebimentos das empresas) e o que ficou
  pendente (vencidos, o resto da semana, a semana que vem e os cheques).
- Cada resumo sai uma vez no dia; se o computador estava desligado no horário, sai assim que o sistema abrir.
  **Ver como fica** mostra o resumo com os números de agora e **Enviar agora** manda na hora.

## Ativando a IA (opcional)

1. Crie uma chave em <https://console.anthropic.com/>.
2. Copie `.env.example` para `.env` e preencha `ANTHROPIC_API_KEY=...`.
3. Reinicie o sistema. O botão **Analisar com IA** aparece na revisão de cada boleto.
   Com `LEITOR_IA_AUTOMATICA=1`, a IA é chamada sozinha quando a leitura local tem baixa confiança.

## Usar pelo celular (rede Wi-Fi)

Tudo pela tela **Configurações → Acesso pelo celular**, sem editar arquivos nem reiniciar:

1. **Defina uma senha** (mínimo 6 caracteres). Ela é guardada com hash em `dados\rede.json`.
2. **Ligue a chave** "Acesso pelo celular". Na primeira vez, o Windows pergunta se o Python pode acessar a rede:
   marque **Redes privadas** e clique em **Permitir acesso**.
3. **Leia o QR code** com a câmera do celular (conectado ao mesmo Wi-Fi) e digite a senha uma vez — vale por 30 dias.

No celular, a tela de leitura mostra o botão **Tirar foto do boleto** em destaque. Outros detalhes:

- No próprio computador o acesso continua livre; desligar a chave fecha o acesso da rede na hora.
- Após 5 senhas erradas, o aparelho fica bloqueado por 5 minutos. Trocar a senha desconecta todos os aparelhos.
- A tela mostra os aparelhos que acessaram (sistema, navegador, IP e horário) e cada aparelho tem **Sair deste aparelho**.
- Se o endereço do computador mudar (roteador reiniciou), o acesso é reaberto sozinho em até 1 minuto.
- Ligar a chave, trocar a senha e abrir a planilha só podem ser feitos no próprio computador.
- Alternativa avançada: `LEITOR_HOST=0.0.0.0` + `LEITOR_SENHA_ACESSO` no `.env`.

## Estrutura

```
app/
  boleto/
    codigo.py      # FEBRABAN: DVs, conversão linha ↔ barras, fator de vencimento, correção
    texto.py       # extração espacial de campos, busca de linha no texto, segmentação do OCR
    leitores.py    # PDF (pypdfium2), imagens e código de barras (zxing-cpp)
    ocr.py         # OCR local (RapidOCR, modelo latino)
    imagem.py      # modo scanner: recorte e correção de perspectiva de fotos
    extrator.py    # orquestra a leitura, consolida campos, confiança e alertas
  rotas/           # API separada por assunto (boletos, pix, leitura, gastos, usuários, backup, entrada, saúde...)
  contexto.py      # objetos compartilhados (banco, repositórios, serviços)
  banco.py         # banco de dados SQLite + geração da planilha Excel (e edições feitas no Excel)
  planilha.py      # formato da planilha Excel (openpyxl): colunas, abas, formatação e histórico
  usuarios.py      # usuários do escritório, login e sessões
  backup.py        # backup total (dados, arquivos, configurações, código e versões), pacote .zip e conferência
  versao.py        # controle de versão: número, histórico (VERSOES.md) e consulta ao git
  entrada.py       # caixa de entrada: boletos recebidos por e-mail (IMAP) e Telegram
  fechamento.py    # fechamento do mês em Excel, PDF e ZIP
  comprovante.py   # leitura de comprovantes e escolha do boleto/Pix correspondente
  bot.py           # comandos do bot do Telegram
  empresas/        # módulo Empresas (vendas a prazo): notas fiscais, cheques, recebimentos e fechamento
    modelos.py     #   abas do banco das empresas (empresas, notas, cheques, recebimentos)
    servico.py     #   regras: período do fechamento, baixa automática, cheques e saldos
    leitura.py     #   reconhece NF-e (XML/DANFE), cheque (CMC7), comprovante e print do fechamento
    relatorio.py   #   fechamento em Excel e PDF no formato usado hoje
    entrada.py     #   bot de notas fiscais (Telegram) e envio do fechamento no dia 20
    bot.py         #   comandos do bot de notas
  saude.py         # diagnóstico do sistema
  registro_log.py  # arquivo de log com limite de tamanho
  pix.py           # chaves Pix, leitura/geração do Copia e Cola (BR Code) e QR code
  servicos.py      # filtros, painel, análise de gastos e exportação
  desktop.py       # aplicativo: janela (pywebview/WebView2) e ícone na bandeja (pystray)
  inicializacao.py # iniciar junto com o Windows
  atalhos.py       # atalhos na Área de Trabalho e no Menu Iniciar
  ia.py            # integração opcional com Claude
  arquivos.py      # armazenamento dos arquivos enviados
  main.py          # junta as rotas, inicia os serviços e serve o front-end
web/               # front-end (HTML, CSS e JavaScript, sem etapa de build)
  js/views/<tela>/ # telas grandes divididas por assunto (leitura, boletos, pix, empresas, configuracoes)
ferramentas/       # versao.py (guardar/voltar versões), restaurar_backup.py, gerar_especificacao.py
site/              # site de apresentação (index.html, imagens e os pedaços de onde ele é montado)
tests/             # testes automatizados + gerador de boletos de exemplo
VERSOES.md         # o que mudou em cada versão
```

## API

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/status` | Recursos disponíveis |
| POST | `/api/leituras` | Envia um arquivo (multipart `arquivo`) e devolve os boletos lidos |
| POST | `/api/leituras/linha` | Analisa uma linha digitável digitada |
| POST | `/api/leituras/{arquivo_id}/ia` | Reanalisa o arquivo com IA |
| GET/POST | `/api/boletos` | Lista (com filtros) / lança na planilha |
| GET/PUT/DELETE | `/api/boletos/{id}` | Consulta / edita / exclui |
| PATCH | `/api/boletos/{id}/status` | Pendente, Pago ou Cancelado |
| GET/POST | `/api/pix` | Lista / lança Pix (`/api/pix/{id}`, `/status`, `/qrcode.svg`, `/copia-e-cola`) |
| POST | `/api/pix/ler-codigo` · `/api/pix/ler-arquivo` | Lê um Pix Copia e Cola / QR code de imagem ou PDF |
| GET/POST/PUT | `/api/centros` | Centros de custo (com totais de uso) |
| GET | `/api/gastos` · `/api/gastos/exportar` | Análise de gastos por centro de custo |
| GET/PUT/POST | `/api/app` · `/api/app/preferencias` · `/api/app/atalhos` | Aplicativo de desktop |
| POST/GET/DELETE | `/api/boletos/{id}/comprovante` · `/api/pix/{id}/comprovante` | Comprovante de pagamento |
| GET | `/api/boletos/{id}/historico` · `/api/pix/{id}/historico` | Quem fez cada alteração |
| POST | `/api/comprovantes/registrar` · `/api/boletos/{id}/desfazer-pagamento` · `/api/entrada/{id}/registrar` | Baixa por comprovante |
| POST | `/api/usuarios/entrar` · `/api/usuarios/sair` · `/api/usuarios/minha-senha` | Login por pessoa |
| GET/POST/PUT/DELETE | `/api/usuarios` · `/api/usuarios/{id}` · `/api/usuarios/config` | Usuários, perfis e permissões (administrador) |
| GET/PUT/POST | `/api/backup` · `/api/backup/config` · `/api/backup/agora` · `/api/backup/pacote` · `/api/backup/verificar` | Backup total fora do computador |
| GET | `/api/versao` | Versão em uso, histórico e alterações ainda sem versão |
| GET/POST/PUT | `/api/entrada` · `/api/entrada/{id}` · `/api/entrada/descartar` · `/api/entrada/verificar` · `/api/entrada/config` | Caixa de entrada (e-mail e Telegram) |
| GET | `/api/relatorios/fechamento` · `/api/relatorios/fechamento/arquivo?formato=pdf\|xlsx\|zip` | Fechamento do mês |
| GET/POST/PUT/DELETE | `/api/empresas` · `/api/empresas/{id}` | Empresas que compram a prazo |
| GET | `/api/empresas/{id}/fechamento` · `/fechamento/arquivo?formato=xlsx\|pdf` | Fechamento da empresa |
| GET/POST/PUT/DELETE | `/api/notas` · `/api/cheques` · `/api/recebimentos` | Notas fiscais, cheques e recebimentos |
| POST | `/api/recebimentos/{id}/cancelar` · `/api/empresas/fechamento/enviar` | Desfazer baixa / enviar fechamentos |
| GET/POST | `/api/empresas/entrada` · `/api/empresas/entrada/{id}/confirmar` · `/descartar` · `/verificar` | Bot de notas fiscais |
| POST | `/api/empresas/analisar` · `/api/empresas/importar-fechamento` | Ler arquivo e importar o fechamento atual |
| GET/POST | `/api/empresas/config` · `/api/empresas/config/chats` | Minha empresa, dia do fechamento e bot de notas |
| GET | `/api/painel` · `/api/previsao` | Indicadores do painel e previsão de saídas |
| GET/POST | `/api/saude` · `/api/saude/atualizar-planilha` · `/api/saude/limpar-logs` | Saúde do sistema |
| GET | `/api/exportar?formato=xlsx\|csv\|planilha` | Exportação |

Documentação interativa: `http://localhost:8000/docs`.

## Testes

```bash
.venv\Scripts\python -m pytest
```

Incluem testes das telas no navegador (`tests\test_telas.py`, com Playwright usando o Microsoft Edge já instalado):
abrem todas as telas, leem um boleto, dão baixa por comprovante e conferem o painel. Sem o Playwright, esses testes são pulados.

Para gerar boletos de exemplo em `exemplos\`: `.venv\Scripts\python tests\gerar_boleto_exemplo.py`.

`tests\corpus.py` gera um corpus variado (layout com rótulos na linha, conta de consumo, DAS, carnê,
PDF escaneado e fotos de papel com perspectiva) usado nos testes de regressão.

> Na primeira execução, o OCR baixa os modelos de leitura (~20 MB) uma única vez. Sem internet nesse
> momento, o sistema usa o modelo básico, que já vem instalado.
