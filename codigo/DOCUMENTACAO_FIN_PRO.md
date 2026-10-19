# Fin Pro — Documentação completa do sistema

> Tudo o que foi construído e implantado no Fin Pro, módulo por módulo, do primeiro pedido até hoje.
> Atualizado em 19/10/2026 (versão 1.12.1).

> **Para quem vai desenvolver ou reconstruir o sistema:** este é o manual de uso (o que cada tela faz). A especificação
> técnica completa — regras de cálculo, todas as rotas da API, todos os campos, mapa do código, testes e o roteiro de
> reconstrução — está em [`docs/especificacao/`](docs/especificacao/00-LEIA-ME.md).

---

## Sumário

1. [O que é o Fin Pro](#1-o-que-é-o-fin-pro)
2. [Como o sistema foi construído (linha do tempo)](#2-como-o-sistema-foi-construído-linha-do-tempo)
3. [Visão geral: telas, bots e onde ficam os dados](#3-visão-geral-telas-bots-e-onde-ficam-os-dados)
4. [Painel](#4-painel)
5. [Ler boletos (leitura de PDF e foto)](#5-ler-boletos-leitura-de-pdf-e-foto)
6. [Boletos lançados](#6-boletos-lançados)
7. [Pagamentos Pix](#7-pagamentos-pix)
8. [Comprovantes](#8-comprovantes)
9. [Caixa (entradas e saídas em dinheiro)](#9-caixa-entradas-e-saídas-em-dinheiro)
10. [Diesel](#10-diesel)
11. [Gastos](#11-gastos)
12. [Relatórios (central)](#12-relatórios-central)
13. [Empresas (vendas a prazo)](#13-empresas-vendas-a-prazo)
14. [Notificações](#14-notificações)
15. [Configurações](#15-configurações)
16. [Usuários, perfis e permissões](#16-usuários-perfis-e-permissões)
17. [Os bots do Telegram](#17-os-bots-do-telegram)
18. [Versão de demonstração](#18-versão-de-demonstração)
19. [Banco de dados, planilhas, arquivos e backup](#19-banco-de-dados-planilhas-arquivos-e-backup)
20. [Segurança](#20-segurança)
21. [Sistema online](#21-sistema-online)
22. [Pendências e próximos passos](#22-pendências-e-próximos-passos)
23. [Referência rápida](#23-referência-rápida)

---

## 1. O que é o Fin Pro

O Fin Pro (antes chamado **Leitor de Boletos**) é o sistema financeiro do escritório. Ele roda no próprio computador como um
**aplicativo de Windows**, com janela própria, e também pode ser usado pelo celular na rede Wi-Fi. Cuida de:

| Área | O que controla |
|---|---|
| **Contas a pagar** | Boletos e Pix: leitura automática, vencimentos, pagamentos, juros, comprovantes |
| **Dinheiro em espécie** | Caixa: entradas e saídas, com o bot do caixa |
| **Combustível** | Diesel: compras no posto, abastecimentos de cada máquina, saldo em R$, consumo e relatórios |
| **Contas a receber** | Empresas que compram a prazo: notas fiscais, cheques pré-datados, Pix/TED, fechamento todo dia 20 |
| **Análise** | Gastos por centro de custo, fechamento do mês para o contador, relatórios |
| **Avisos** | Notificações no Windows, Telegram e e-mail; resumos de segunda e sexta |

Tudo foi pensado para **digitar o mínimo**: quase tudo entra por foto, PDF, e-mail ou Telegram, e o sistema lê, preenche e
deixa para alguém só conferir.

---

## 2. Como o sistema foi construído (linha do tempo)

| Data | Pedido | O que foi feito |
|---|---|---|
| 14/09 | Ler boletos em PDF ou foto e guardar numa planilha | Leitor completo (código de barras, texto do PDF, OCR), planilha Excel como banco de dados, telas de leitura e de boletos |
| 14/09 | Testar com boletos reais e melhorar os pontos soltos | Ajustes com os PDFs reais (HIPER JN, BOL. NF 134668 etc.), modo scanner para fotos, correção automática de dígitos |
| 14/09 | Avisar quando um boleto vai vencer, 3× no dia, com horários configuráveis | Tela Notificações com lembretes, horários e canais (Windows, Telegram, e-mail) |
| 14/09 | Melhorias gerais e acesso pela rede | Gravação em lote, leitura em segundo plano, calendário, acesso pelo celular com senha |
| 14/09 | Abrir junto com o Windows, ser um App, centro de custo e aba Pix | Aplicativo de desktop com ícone na bandeja, centro de custo e o módulo Pagamentos Pix |
| 15/09 | Importar boletos de outro sistema, só para o administrador | Importação de Excel/CSV/TXT em Configurações, protegida por senha de administrador |
| 15/09 | Notificações não sumiam do sininho | Sininho com "visto" e "dispensado" |
| 16/09 | Outras pessoas do escritório recebendo o Telegram | Vários destinatários no Telegram (pessoas e grupos) |
| 16/09 | Lista de melhorias: 1, 2, 3, 5, 6 e 7 | Backup fora do computador, login por pessoa com histórico de quem fez o quê, comprovante opcional, receber boletos por e-mail e Telegram, fechamento do mês para o contador, organização do código |
| 17/09 | Lançar o comprovante e o sistema dar baixa sozinho, com juros | Leitura de comprovantes, baixa automática, colunas Valor Pago, Juros/Multa e Desconto |
| 17/09 | Painel não mostrava os Pix vencidos | Painel passou a somar boletos e Pix em tudo |
| 17/09 | Bot com comandos, previsão de saídas, banco de dados, logs, saúde, telas | Comandos do bot, previsão de saídas, troca da planilha por banco SQLite (a planilha continua sendo gerada), rotação do log, Saúde do sistema, Configurações em abas, testes automáticos das telas |
| 18/09 | Módulo Empresas / Fechamentos | Bot de notas fiscais, fechamento por empresa no formato da planilha da Prospera, cheques, baixa automática, importação do fechamento em andamento |
| 18/09 | Acesso de administrador e permissões | Usuários com perfil e permissões; pedir usuário e senha ao abrir o App |
| 18/09 | Almir também mandar notas, cheques e comprovantes | Bot de notas aceita várias pessoas |
| 18/09 | Cheque com "Bom para" e pedidos no verso; escolher o mês do fechamento da nota | Leitura detalhada do cheque e campo *Fechamento* na nota |
| 18/09 | Ao escolher um mês, mostrar só aquele mês | Filtro por mês nos fechamentos |
| 22/09 | Caixa: entrada e saída, relatórios e um bot | Módulo Caixa com relatórios, terceiro bot e integração com Gastos |
| 22/09 | Arrumar o sininho e o cabeçalho do fechamento | Correções visuais |
| 22/09 | Resumo da semana na segunda e na sexta | Resumos de segunda (o que vence) e sexta (o que foi pago, com juros) |
| 22–24/09 | "A opção de juros sumiu" | Juros e multas visíveis nas listas, no calendário, no Painel, em Gastos e no resumo de sexta |
| 22/09 | Novo nome, copiar a linha só com números e versão para clientes | Nome **Fin Pro**; cópia da linha digitável só com dígitos; versão de demonstração |
| 24/09 | Um lugar para buscar comprovantes | Menu Comprovantes com filtros e download em ZIP |
| 24/09 | Comprovante de depósito de cheque não reconhecido | Reconhece o depósito de cheque e dá baixa no cheque certo |
| 29/09 | Controle de diesel | Módulo Diesel com bot, máquinas, médias e relatórios automáticos |
| 29/09 | Preço do litro, reconhecer combustível, enviar pela tela, dois combustíveis | Preços, combustíveis, canhoto com várias linhas e envio pela tela |
| 29/09 | Saldo do diesel errado | Saldo único para S10 e comum; posto lido do favorecido do comprovante |
| 02/10 | Relatórios "sumiram"; revisar tudo desde o começo | Central de Relatórios (pronta, aguardando liberação para entrar no menu) e revisão das pendências |
| 02–06/10 | Colocar o sistema online | Estudo de opções; escolhida a VPS Hostinger KVM 2 |
| 06/10 | Saldo do diesel em R$ | Saldo do diesel passou a ser em reais |
| 06/10 | Relatório do diesel mais simples, sem perder o detalhe | Relatório do diesel em três níveis: Simples, Detalhado e Completo |
| 07/10 | Documentar tudo | Manual, especificação técnica e kit de reconstrução (v1.8.0) |
| 10/10 | Não perder nada e saber o que mudou | Controle de versão e backup total fora do computador (v1.9.0) |
| 12/10 | Sistema no ar e site de apresentação | Versão online em `fin.fabbiol.tech` e site do Fin Pro (v1.10.0) |
| 19/10 | Organizar o projeto e revisar a segurança | Ferramentas para agentes de IA, versão do computador e online juntas, duas revisões de segurança (v1.11.0 a v1.12.1) |

---

## 3. Visão geral: telas, bots e onde ficam os dados

### 3.1 Menu lateral

| Item | Para que serve | Permissão necessária |
|---|---|---|
| Painel | Visão geral do que pagar, vencidos, previsão de saídas | Todos |
| Ler boletos | Enviar PDFs/fotos de boletos, Pix e comprovantes | Lançar |
| Boletos lançados | Lista, calendário, baixa, edição | Todos (ações conforme permissão) |
| Pagamentos Pix | Pix a pagar | Todos (ações conforme permissão) |
| Comprovantes | Buscar e baixar comprovantes de tudo | Todos (cada um vê o que pode) |
| Caixa | Dinheiro em espécie | Caixa |
| Diesel | Combustível das máquinas | Diesel |
| Gastos | Análise por centro de custo e fechamento do mês | Gastos |
| Relatórios | Central de relatórios (pronta, aguardando liberação) | Todos (cada parte conforme permissão) |
| Empresas | Vendas a prazo, notas, cheques, recebimentos | Empresas |
| Notificações | Lembretes e resumos | Avisos |
| Configurações | Aplicativo, usuários, backup, integrações, saúde | Configurações / administrador |

O menu também mostra **contadores**: arquivos recebidos esperando conferência (Ler boletos, Caixa, Diesel, Empresas) e
alertas (Notificações). No rodapé do menu aparecem o estado da **planilha**, do **OCR**, da **IA**, do **backup** e o
usuário conectado.

### 3.2 Os cinco bots do Telegram

| Bot | Para que serve |
|---|---|
| **Bot dos boletos** (o das notificações) | Lembretes, receber boletos e comprovantes, comandos `/vencidos`, `/hoje` etc. |
| **Bot de notas** (Empresas) | Notas fiscais, cheques, comprovantes de recebimento, prints de fechamento |
| **Bot do caixa** | Fotos de cupons e notas de compras em dinheiro |
| **Bot do diesel** | Canhotos de abastecimento e comprovantes de compra no posto |
| (Resumos de segunda e sexta) | Saem pelo bot dos boletos |

Cada bot tem o seu próprio token, criado no @BotFather. Quem pode usar os bots do caixa e do diesel vem automaticamente das
pessoas cadastradas no bot dos boletos e no bot de notas.

### 3.3 Onde ficam os dados (pasta `dados`)

| Arquivo | Conteúdo |
|---|---|
| `boletos.db` | Banco de dados de boletos, Pix e caixa |
| `boletos.xlsx` | Planilha gerada automaticamente (abas Boletos, Pix, Caixa, Centros de Custo, Resumo, Histórico) |
| `empresas.db` / `fechamentos.xlsx` | Empresas, notas fiscais, cheques e recebimentos |
| `diesel.db` / `diesel.xlsx` | Máquinas, compras e abastecimentos de diesel |
| `diesel_precos.json` | Preço do litro de cada combustível |
| `arquivos\` | PDFs e fotos originais (boletos, comprovantes, cupons, canhotos, cheques, notas) |
| `usuarios.json` | Usuários e senhas (somente em hash) |
| `admin.json` | Senha de administrador (somente em hash) |
| `notificacoes.json` | Lembretes, canais e histórico de avisos |
| `caixa_bot.json`, `diesel_bot.json`, `empresas.json`, `entrada.json`, `entrada_notas.json` | Configuração dos bots e caixas de entrada |
| `backup.json`, `rede.json`, `app.json` | Backup, acesso pela rede e preferências do aplicativo |
| `backups\` | Cópia diária interna (30 dias) |
| `leitor.log` | Registro de funcionamento (gira a cada 2 MB, guarda 5 arquivos) |

---

## 4. Painel

A primeira tela do sistema. Soma **boletos e Pix juntos** em tudo.

### 4.1 Indicadores (cartões do topo)

| Cartão | O que mostra | Clicar leva para |
|---|---|---|
| **A pagar** | Valor e quantidade de pendentes (boletos e Pix) | Boletos pendentes |
| **Vencidos** | Valor em atraso, separando quantos boletos e quantos Pix | Boletos vencidos (com atalhos para Boletos e Pix) |
| **Vencem em 7 dias** | Valor e quantidade que vencem na próxima semana | Boletos a vencer |
| **Pagos no mês** | Valor pago no mês e **quanto foi de juros** ("R$ 87,30 de juros (2)") ou "sem juros" | Boletos pagos |

### 4.2 Previsão de saídas

- Quanto vai sair em cada uma das **próximas 8 semanas** (boletos + Pix pendentes), começando hoje.
- O que **já está em atraso** aparece separado.
- Totais de **7 dias** e **30 dias**.
- Clicar numa semana mostra os lançamentos dela.

### 4.3 Outros quadros

- **Vencimentos por mês**: gráfico com pago, vencido e a vencer, mês a mês.
- **Próximos vencimentos** e **Vencidos**, com atalhos.
- **Maiores beneficiários**.
- **Lançados neste mês**: quantos lançamentos e o valor.

### 4.4 Sininho (topo da tela)

- Mostra os boletos e Pix que vencem hoje, os próximos e os vencidos.
- Cada aviso pode ser marcado como **visto** ou **dispensado** e some da contagem.
- Se a situação do boleto mudar (por exemplo, de "vence amanhã" para "vence hoje"), o aviso volta, porque é uma informação nova.

---

## 5. Ler boletos (leitura de PDF e foto)

### 5.1 Como enviar

- **Arrastar** arquivos para a tela (de qualquer tela do sistema).
- **Escolher arquivos**.
- **Colar** com `Ctrl+V` (imagem ou linha digitável).
- **Tirar foto** (no celular, o botão "Tirar foto do boleto" fica em destaque).
- **Digitar ou colar a linha digitável** à mão.
- **Preencher manualmente**, quando não há arquivo.
- Também chegam por **e-mail** e pelo **Telegram** (veja 5.6).

### 5.2 O que o sistema lê

| Campo | Como é obtido |
|---|---|
| **Linha digitável / código de barras** | Código de barras da imagem → texto do PDF → OCR → IA (opcional). Sempre conferido pelos dígitos verificadores FEBRABAN |
| **Beneficiário** e CPF/CNPJ | Texto do PDF ou OCR, pela posição do rótulo na página |
| **Nº do documento** | Texto do PDF ou OCR |
| **Vencimento** | Fator de vencimento do código de barras (exato), conferido com a data impressa |
| **Valor** | Do código de barras (exato), conferido com o valor impresso |
| **Data de lançamento** | Gravada automaticamente |

### 5.3 Tipos de documento aceitos

- PDFs digitais, PDFs escaneados e fotos (JPG, PNG, WEBP e HEIC do iPhone).
- Carnês e PDFs com vários boletos (um por página ou vários na mesma página).
- Boletos **bancários** (47 dígitos) e de **arrecadação**: contas de luz, água, telefone e tributos (48 dígitos).
- **Guias de tributos** (DAS, DARF, GPS, FGTS, IPVA, IPTU, DETRAN): o beneficiário é o órgão arrecadador.
- **Contas de consumo** sem o rótulo "Beneficiário": o nome da empresa vem do cabeçalho.
- Novo ciclo do fator de vencimento (reiniciado em 22/02/2025).

### 5.4 Recursos para fotos difíceis

- **Modo scanner**: recorta o papel, corrige a perspectiva e uniformiza a luz.
- Fotos de lado são endireitadas pela orientação do código de barras.
- Várias tentativas para ler códigos de barras borrados.
- **Correção automática** de dígito lido errado (um por campo), priorizando as confusões típicas do OCR (8↔3, 5↔6…) e
  desempatando pelo valor e vencimento impressos.
- PDFs escaneados com texto ruim recebem OCR complementar.
- Datas por extenso ("10 de outubro de 2026", "10/OUT/2026").
- **IA opcional (Claude)**: botão *Analisar com IA* / *Tentar com IA* para fotos muito difíceis. A linha sugerida pela IA
  também passa pela validação. (Hoje a IA está **desligada**; para ligar é preciso uma chave da Anthropic.)

### 5.5 Revisão e lançamento

- Leitura em **segundo plano**, com fila, barra de progresso por página e até 2 leituras ao mesmo tempo.
- Cada boleto aparece como um cartão. Os campos com **baixa confiança ficam em amarelo**.
- Selos: linha **Válida/Inválida** e de onde veio cada campo (Código de barras, Texto de PDF, OCR).
- **Alertas**: linha inválida, valor ou vencimento divergentes, boleto vencido, campo faltando e **boleto já lançado**
  (duplicados são bloqueados).
- Escolha do **centro de custo** em cada boleto.
- **Lançar na planilha** (um a um) ou **Lançar todos** de uma vez, numa única gravação.
- Arquivo **sem boleto, mas com QR code Pix** → botão **Lançar como Pix**.
- Se o arquivo for um **comprovante de pagamento**, o sistema não trata como boleto: ele acha o boleto/Pix correspondente e
  oferece **Registrar pagamento** (veja 6.6).
- Um arquivo já lido de novo sai do **cache** (não refaz o OCR).

### 5.6 Recebidos por e-mail e Telegram

- Quadro **Recebidos por e-mail e Telegram** na tela Ler boletos, com contador azul no menu.
- Nada é lançado sem conferência: **Revisar** abre o boleto lido; dá para lançar ou **Descartar**.
- Arquivos repetidos são ignorados e boletos já lançados saem sozinhos da caixa.
- Comprovantes que chegam por esses canais dão **baixa automática**.

---

## 6. Boletos lançados

### 6.1 Lista

- **Busca** por beneficiário, documento ou linha (atalho `/`).
- **Filtros de situação**: Todos, Pendentes, A vencer, Vencidos (atrasados), Pagos, Cancelados.
- **Filtro de período** por *Vencimento* ou *Lançado em*.
- **Filtro de centro de custo**.
- Ordenação por coluna, paginação.
- **Resumo da lista** (cartões): valor total, pendente, pago e **"Juros e multas pagos"** dos boletos filtrados.
- Cada linha mostra o selo de situação (Pendente, Vence hoje, Atrasado, Pago, Cancelado). Nos pagos com juros aparece
  **"+ R$ x juros"** logo abaixo do valor.

### 6.2 Ações em cada boleto

| Botão | O que faz |
|---|---|
| **Copiar linha digitável** | Copia **só os números**, sem pontos, traços ou espaços (pronto para colar no banco) |
| **Marcar como pago** | Dá baixa (com data, opcionalmente valor pago, juros e comprovante) |
| **Editar** | Altera os campos: beneficiário, documento, vencimento, valor, situação, centro de custo, observações, valor pago, juros/multa, desconto |
| **Ver arquivo original** | Abre o PDF/foto do boleto |
| **Histórico e comprovante** (relógio) | Quem lançou, quem pagou, todas as alterações, e o comprovante (ver, anexar, trocar ou remover) |

### 6.3 Ações em lote (selecionando vários)

**Marcar pagos**, **Marcar pendentes**, **Cancelar**, **Centro de custo** (atribuir de uma vez), **Excluir** e **Limpar seleção**.

### 6.4 Calendário de vencimentos

- Botão **Calendário** ao lado de **Lista**.
- Visão do mês com o **total por dia** e cores: vencido, vence hoje, a vencer e pago.
- Resumo do mês, incluindo os juros pagos.
- Clicar num dia permite **marcar como pago**, **copiar a linha** ou **editar**.

### 6.5 Exportar

- **Exportar** para Excel ou CSV (com os filtros atuais).
- **Planilha completa** (o arquivo `boletos.xlsx` inteiro): só aparece para quem tem a permissão **Caixa**, porque o
  arquivo leva também a aba do Caixa.
- Atalho **Comprovantes** que abre a busca já filtrada nos comprovantes de boletos.
- Ícone "Aguardando gravação" quando a planilha está aberta em outro programa (o sistema grava quando ela for fechada).

### 6.6 Baixa automática pelo comprovante

1. O sistema **percebe que é um comprovante** (não um boleto) e lê: valor pago, valor do documento, juros/multa, desconto,
   data do pagamento, vencimento, beneficiário, CNPJ, chave Pix e a linha digitável (quando o banco imprime).
2. **Descobre de qual lançamento é**: linha digitável igual resolve na hora; sem ela, compara valor, CNPJ, nome e datas.
3. **Marca como pago** com a data do comprovante e grava Valor Pago, Juros/Multa e Desconto. Se o comprovante não detalha,
   a diferença entre o pago e o valor do boleto vira juros (a mais) ou desconto (a menos).
4. **Dúvida** (ex.: parcelas iguais sem linha digitável): o sistema não chuta; mostra os lançamentos possíveis para alguém
   escolher e clicar em **Registrar pagamento**.
5. Comprovante de **agendamento** não dá baixa (o pagamento ainda não aconteceu).
6. Logo depois da baixa pela tela aparece **Desfazer**.

Onde mandar o comprovante: Ler boletos, bot do Telegram, e-mail ou o botão de relógio da lista. O bot responde, por exemplo:

> ✅ Pagamento registrado: CLA AUTO PECAS MIRASSOL LTDA
> Valor do boleto: R$ 270,35 · Valor pago: R$ 275,75 em 15/10/2026
> Juros/multa: R$ 5,40 (5 dia(s) de atraso)

### 6.7 Importar boletos de outro sistema

Fica em **Configurações → Usuários e acesso** e é **área restrita** (senha de administrador):

1. Exporte as contas a pagar do outro sistema em **Excel (.xlsx ou .xls), CSV ou TXT**.
2. As colunas são reconhecidas pelo nome, inclusive sinônimos ("Fornecedor", "Cedente", "Vencto", "Valor Título",
   "Cód. Barras", "Situação", "C. Custo"…). Dá para ajustar, escolher a aba e a linha dos títulos.
3. A **prévia** confere cada linha: dígitos verificadores, valor e vencimento contra o código de barras, boletos já lançados e
   repetidos no próprio arquivo. Linhas de total são ignoradas.
4. **Importar** grava tudo de uma vez.

- Situações "Pago", "Liquidado", "Baixado" (ou com data de pagamento) entram como pagos.
- As colunas escolhidas ficam salvas para a próxima vez. Há uma **planilha modelo** para baixar.

---

## 7. Pagamentos Pix

Funciona como os boletos (lembretes, baixa, comprovante, exportação, centro de custo), com os dados próprios do Pix.

### 7.1 Campos

| Campo | Detalhe |
|---|---|
| **Tipo da chave** | CNPJ/CPF, Celular, E-mail e chave aleatória |
| **Chave** | Com máscara e validação (dígitos do CPF/CNPJ, DDD do celular, formato do e-mail) |
| **Valor do Pix** | — |
| **Recebedor** | — |
| **Data prevista** | Usada como "vencimento" nos lembretes |
| **Centro de custo** e **descrição** | — |
| **Pix Copia e Cola** | Guardado para pagar depois |

### 7.2 Formas de lançar

- **Novo pagamento Pix** (formulário).
- **Colar um Pix Copia e Cola** em qualquer tela (`Ctrl+V`): abre o Pix já preenchido (chave, valor, recebedor, identificador).
- **QR code**: enviar print, foto ou PDF da cobrança. Na tela Ler boletos, arquivo sem boleto mas com QR Pix oferece
  **Lançar como Pix**.
- Pix repetido (mesmo Copia e Cola) é bloqueado.

### 7.3 Lista e ações

- Mesmos filtros e resumo da lista de boletos (inclui **Juros e multas pagos** nos Pix).
- **Copiar chave Pix**, **QR code e Pix Copia e Cola** (para pagar no app do banco), **Marcar como pago**, **Editar**,
  **Histórico e comprovante**.
- Atalho **Comprovantes** para os comprovantes dos Pix.
- Os Pix **vencidos** entram no Painel, no sininho e nos lembretes.

---

## 8. Comprovantes

Menu **Comprovantes**: todos os comprovantes do sistema num lugar só.

### 8.1 O que aparece

| Tipo | De onde vem |
|---|---|
| **Boleto** | Comprovante de pagamento anexado ao boleto |
| **Pix** | Comprovante do Pix pago |
| **Cheque** | Foto do cheque (Empresas) |
| **Recebimento** | Comprovante de Pix/TED/depósito recebido das empresas |
| **Caixa** | Cupom ou nota das saídas em dinheiro |
| **Nota fiscal** | NF das empresas |
| **Diesel** | Canhotos de abastecimento e comprovantes de compra no posto |

Cada pessoa só vê os tipos das telas que tem permissão (por exemplo, Caixa, Empresas e Diesel).

### 8.2 Filtros

- **Busca** por nome: beneficiário, empresa, recebedor, pedido, material (atalho `/`).
- **Tipos** (chips).
- **Período** com atalhos: Hoje, Esta semana, Este mês, Mês passado, Últimos 30 dias, Últimos 90 dias, Este ano, Qualquer data.
- **Valor** exato (o valor do documento ou o valor pago com juros).
- **Mais filtros**: faixa de valor (de/até), **centro de custo**, **quem** pagou/lançou, ordenação (mais recentes, mais
  antigos, maior/menor valor, nome).
- **Nº**: número do cheque, NF, pedido, documento, ID da transação ou trecho da linha digitável (para a linha, pelo menos 8
  dígitos, para não confundir com números curtos).
- **Situação**: *Com comprovante*, *Pagos sem comprovante*, *Todos os lançamentos*.

### 8.3 Ações

- **Ver**: abre o comprovante na tela com os dados ao lado; as setas ‹ › (ou as do teclado) passam para o próximo.
- **Baixar comprovantes (.zip)**: todos os filtrados, com nomes como
  `2026-09-21 - Boleto - IMPORCATE - n2.715.287 - R$ 956,70.pdf`, separados em pastas por tipo.
- **Pagos sem comprovante**: lista o que foi pago e ainda não tem comprovante, com o botão **Anexar**.
- Atalhos nas telas de Boletos, Pix, Caixa, Empresas (Cheques e Recebimentos) e Diesel abrem a busca já filtrada.

---

## 9. Caixa (entradas e saídas em dinheiro)

Abas: **Movimento**, **Relatórios**, **Conferência**, **Bot do caixa**. Permissão: **Caixa**.

### 9.1 Movimento

- **+ Entrada**: valor, data e o campo **O que foi pedido**.
- **Saída**: valor, data, o que foi comprado, **onde foi gasto**, **centro de custo** e **quem gastou**, com foto do cupom.
- Períodos **Dia · Semana · Mês · Ano**, setas ‹ › e botão **Hoje**.
- Cartões: **Entradas**, **Saídas**, **Saldo do período** e **Saldo em caixa** (o que deveria ter no caixa no fim do período).
- Editar, cancelar e ver o histórico de cada lançamento.

### 9.2 Relatórios do caixa

- Onde mais se gastou (por loja/fornecedor), por **centro de custo**, **quem mais gastou**, **entradas por pedido**.
- Gasto médio por saída, maior saída, entrada média, comparação das saídas com o período anterior.
- Gráficos de entradas e de saídas por dia (ou por mês, na visão do ano).
- **Excel** do período com o resumo e todos os lançamentos.

### 9.3 Bot do caixa

1. A pessoa manda a **foto do cupom ou da nota**.
2. O bot lê o **valor a pagar** (nunca o dinheiro entregue nem o troco), a data e a loja. Sem valor legível, ele pergunta.
3. Pergunta **onde foi gasto** (com botão para usar o nome da loja).
4. Mostra os **centros de custo como botões**, com **➕ Cadastrar um novo centro de custo**.
5. O gasto aparece em **Caixa → Conferência** já preenchido: **Lançar** com um clique ou **Revisar**.

Comandos: `/resumo` (entradas e saídas de hoje e do mês), `/cancelar`, `/ajuda`.

### 9.4 Integração com Gastos

As saídas em dinheiro entram na **Análise de gastos** (cartão *Dinheiro (caixa)*, coluna *Dinheiro*, filtro *Só dinheiro*),
no **Fechamento do mês para o contador** (com a foto do cupom no ZIP) e no **resumo de sexta-feira**.

---

## 10. Diesel

Controle do diesel comprado no posto (cerca de **1.000 L por semana**, S10 e comum) e de cada abastecimento das máquinas.
Abas: **Painel**, **Máquinas**, **Relatórios**, **Conferência**, **Bot do diesel**. Permissão: **Diesel**.

### 10.1 Como funciona o saldo (em reais)

A compra da semana funciona como um **crédito no posto** que serve tanto para o **Diesel S10** quanto para o **Diesel comum**,
e cada um tem um preço. Por isso o saldo é **em dinheiro**:

> **Saldo = total pago nas compras − valor de cada abastecimento (litros × preço do combustível abastecido)**

Exemplo real (Posto City 2): pagos R$ 7.450 pelos 1.000 L; saem 200 L de comum × R$ 6,75 (R$ 1.350) e 200 L de S10 × R$ 7,45
(R$ 1.490) → **saldo R$ 4.610,00**.

- Abaixo do saldo aparece **quantos litros ele ainda compra** de cada combustível pelo preço atual
  (ex.: "≈ Diesel S10 884 L · ≈ Diesel comum 976 L").
- **Última compra**: valor pago e quanto já foi abastecido desde então, com barra de progresso. Compras de S10 e comum no
  mesmo dia contam como uma só.
- Abastecimento sem valor no canhoto usa o preço da tabela; sem tabela, o preço médio das compras.

### 10.2 Combustíveis e preços

- Reconhece **Diesel S10**, **Diesel comum (S500)**, **Gasolina**, **Etanol** e **Arla 32**, mesmo escrito grudado ("DIESELS10").
- Cartão **Preço do litro** no painel: toque para informar o preço de cada combustível (ex.: S10 R$ 7,45; comum R$ 6,75).
- Se o canhoto traz o preço, vale o dele; senão, vale o do cartão. Em todo formulário, **litros × preço** preenche o total.
- Cada máquina tem o **combustível que usa**, que completa a linha do canhoto que não diz qual é.

### 10.3 Painel do diesel

- Períodos **Semana · Quinzena · Mês · Ano**, setas e **Hoje**.
- Cartões: **Saldo do diesel** (R$, litros equivalentes, última compra), **Comprado no período** (R$ e litros),
  **Abastecido no período** (R$, litros, litros/dia e a divisão S10/comum), **Preço do litro**.
- **Consumo por máquina**: barras com litros, R$, % do total, número de abastecimentos e consumo (L/h ou km/L).
- **Lançamentos**: compras e abastecimentos com data, hora, máquina/posto, nº do pedido, combustível, litros, horímetro/km,
  valor, preço por litro, quem abasteceu e quem lançou. Ações: ver canhoto/comprovante, histórico, editar e cancelar.
- Botões: **Enviar canhoto ou comprovante**, **Abastecimento**, **Compra**, **Comprovantes**, **Excel**.

### 10.4 Lançar sem o bot (pela tela)

- **Enviar canhoto ou comprovante** (ou arrastar o arquivo para a tela do Diesel).
- O sistema lê e abre o formulário **já preenchido** para conferir e lançar.
- **Canhoto com várias linhas**: cada linha (combustível, litros, preço, total, máquina, horímetro/km) vira um abastecimento,
  e cada uma pode ir para uma **máquina diferente**. Dá para acrescentar ou remover linhas.
- O leitor confere **litros × preço = total** em cada linha e acerta os números tortos da foto pelos **totais do rodapé**
  (testado com a foto real do Posto City 2: "200006", "1.496", "7.450" foram corrigidos para 200 L, 7,45 e 1.490).
- **Compra**: o posto vem do **nome do favorecido** do comprovante do banco, nunca do rodapé do banco ("Demais telefones") nem
  da própria Prospera.

### 10.5 Máquinas

- Cadastro com nome, tipo (Caminhão, Máquina, Veículo, Gerador, Outro), placa/prefixo, medidor (horímetro, hodômetro ou
  nenhum), combustível, situação e observações.
- Mostra a **média dos últimos 30 dias** de cada máquina.

### 10.6 Bot do diesel

- **Canhoto**: o bot lê combustíveis e litros (e data, posto, placa, horímetro/km quando aparecem) e manda a foto para o
  **responsável** ("Quem escolhe a máquina"). Para cada linha ele pergunta *"Linha 1 de 2 — Diesel comum · 200 L: de qual
  máquina?"*, com as máquinas em botões (as que usam aquele combustível primeiro; o caminhão da placa já vem marcado).
  Depois pede o horímetro/km (ou **Pular**). Há botões para **cadastrar máquina nova**, **corrigir os litros** e escolher o
  combustível quando o canhoto não diz.
- A resposta traz o lançamento, o **saldo em R$** e a **média da máquina**:
  > ✅ 180 L de Diesel S10 em Escavadeira PC200 · horímetro 4.520
  > 🛢️ Saldo do diesel: R$ 4.911,80
  > 📊 Média da Escavadeira PC200: 385 L/semana · 55 L/dia
- Quem mandou o canhoto também é avisado.
- **Comprovante de compra**: lê valor, litros e combustível (botão rápido de "1.000 L") e soma ao saldo.
- **Aviso de diesel acabando** quando o saldo fica abaixo de **R$ 1.000** (configurável).
- Comandos: `/saldo`, `/medias`, `/relatorio` (com período e nível, veja 10.7), `/maquinas`, `/cancelar`, `/ajuda`.
- **Conferência**: canhotos que ficaram sem resposta no Telegram podem ser concluídos na tela.

### 10.7 Relatórios do diesel (três níveis)

Escolha no topo do relatório; o sistema lembra a última escolha.

| Nível | O que mostra |
|---|---|
| **Simples** (padrão) | Resumo em frases ("Foram abastecidos R$ 4.020,77 (574,7 L)…", "−38% em relação à semana anterior", "Saldo no posto R$ …, dá para uns 12 dias", "Quem mais gastou: …"); 4 números (abastecido, abastecimentos, saldo, quantos dias dura); quanto cada máquina gastou; botão "X pontos de atenção" quando há algo errado |
| **Detalhado** | Tudo do simples + **pontos de atenção** + **comparação** com o período anterior (valor, litros, abastecimentos, R$ médio por litro) + **gráfico do valor por dia** (por mês na visão anual), separado por combustível + **tabela por máquina** (litros, R$, R$/L, %, abastecimentos, litros/dia, média por abastecimento, consumo L/h ou km/L, antes, variação, último) + por combustível + compras |
| **Completo** | Tudo do detalhado + **cada abastecimento agrupado por máquina** (data, hora, combustível, litros, preço, valor, horímetro/km, **consumo do trecho** desde o abastecimento anterior, pedido, posto, quem abasteceu, link do canhoto) + **dia a dia** + **por posto** + **quem abasteceu** |

**Pontos de atenção** que o sistema aponta sozinho:
- Saldo **negativo** (foi abastecido mais do que pago — falta lançar compra?) ou **abaixo do limite**.
- Máquina que consumiu **bem acima do costume** dela (pela média dos até 90 dias anteriores; só depois de 14 dias de
  histórico; tolerância de 50% na semana, 40% na quinzena e 30% no mês/ano).
- Abastecimentos **sem horímetro/km** em máquinas que usam medidor (sem eles não há consumo real).
- Abastecimentos **sem preço** (valor estimado pela tabela).
- Máquinas **sem abastecimento** no período.

**Filtros** (Detalhado e Completo): por máquina e por combustível; valem para as tabelas.

**Previsão**: no período atual, quantos dias o saldo dura no ritmo dos últimos 30 dias e em que data acaba.

**No Telegram**:
- **Enviar no Telegram** manda o relatório no nível que está na tela.
- `/relatorio` (semana, simples), `/relatorio mes`, `/relatorio quinzena detalhado`, `/relatorio ano completo`.
- **Automáticos**: semanal (toda segunda), quinzenal (dias 1 e 16) e mensal (dia 1), no horário configurado (padrão 07:00) e no
  nível escolhido em *Bot do diesel* (padrão Simples). Mensagens longas demais são cortadas com "continua no Excel".

**Excel do período** (sempre completo): Resumo, Máquinas, Por dia (ou Por mês), Combustíveis, Por posto, Por pessoa,
Abastecimentos (com leitura anterior, rodado e consumo do trecho), Compras e Pontos de atenção.

---

## 11. Gastos

Abas: **Análise de gastos**, **Fechamento do mês**, **Centros de custo**. Permissão: **Gastos**.

### 11.1 Análise de gastos

- Filtros: **período** (este mês, mês passado, 3 meses, 12 meses, este ano, ano passado, todo o período, personalizado),
  **qual data** (vencimento, pagamento ou lançamento), **tipo** (boletos, Pix e dinheiro; só boletos; só Pix; só dinheiro) e
  **situação** (pagos e pendentes, pagos, pendentes).
- Cartões: **Total gasto**, **Boletos**, **Pix**, **Dinheiro (caixa)**, **Juros e multas** (quantos pagos com atraso) e
  **Sem centro de custo**.
- **Por centro de custo**: total, %, quantidade, e quanto foi boleto, Pix e dinheiro.
- **Gráfico por mês**, empilhado por centro de custo.
- Maiores beneficiários e detalhamento.
- **Exportar Excel**.

### 11.2 Fechamento do mês (para o contador)

- Mês escolhido com setas e duas bases: **Tudo que vence no mês** ou **Só o que foi pago no mês**.
- Cartões: **Total**, **Pago**, **Juros e multas** (e quantos com atraso), **Descontos**, **Em aberto**, **Em atraso**,
  **Comprovantes** (quantos têm).
- **Por centro de custo** (pago, em aberto, total, lançamentos).
- **Pagos**: vencimento, beneficiário, centro, valor, **juros/multa**, desconto, **valor pago**, pago em (com dias de atraso),
  pago por e comprovante.
- **Em aberto**: com a situação (atrasado/a vencer).
- Inclui boletos, Pix e **saídas do caixa**.
- Downloads: **Excel**, **PDF** e **Pacote para o contador (.zip)** com o PDF, a planilha e os comprovantes. Os pagos sem
  comprovante vão listados num arquivo `SEM-COMPROVANTE.txt`.

### 11.3 Centros de custo

- Criar, **renomear** (os lançamentos antigos acompanham) e desativar.
- Escolhidos na leitura, na edição, em lote, no caixa e pelo bot do caixa (com cadastro na hora).

---

## 12. Relatórios (central)

Uma tela única com **todos os relatórios** e um **relatório geral do mês**. Está **pronta e testada**, mas ainda **não aparece no
menu**: para ligá-la é preciso liberar a leitura do arquivo `web/js/app.js` (veja Pendências).

O que ela mostra, sempre do mês escolhido:

- **Pagamentos do mês** (pela data em que foram pagos): total pago, separado em **boletos, Pix e dinheiro**, **juros e
  multas**, descontos, quantos pagos com atraso, o que ainda está em aberto, em atraso e a **previsão de 7 e 30 dias**.
- **Juros e multas pagos**: tabela com beneficiário, vencimento, pago em, dias de atraso, valor, juros, valor pago, centro e
  quem pagou.
- **Últimos 12 meses** lado a lado: boletos, Pix, dinheiro, total pago, juros/multa, pagos com atraso, com barra comparativa.
- **Onde mais se pagou** (centros de custo).
- Quadros de **Caixa** (entradas, saídas, saldos), **Diesel** (comprado, abastecido, custo, saldo no posto) e **Empresas**
  (faturado, falta receber, recebido no mês, cheques em carteira).
- **Todos os relatórios**: atalhos com downloads para o Fechamento do mês, Análise de gastos, Previsão de saídas, Caixa,
  Diesel, Fechamento das empresas, Comprovantes e a prévia dos **resumos de segunda e sexta**.
- **Excel do relatório geral**: Resumo, Juros e multas, Últimos 12 meses.
- Cada pessoa só vê as partes das telas que tem permissão.

---

## 13. Empresas (vendas a prazo)

Enquanto o resto do sistema cuida do que a empresa **paga**, este módulo cuida do que ela **recebe** dos clientes que compram a
prazo (por **Pix/TED** ou **cheque pré-datado**). Abas: **Fechamentos**, **Notas fiscais**, **Cheques**, **Recebimentos**,
**Conferência**, **Bot de notas**. Permissão: **Empresas**.

### 13.1 Bot de notas (Telegram exclusivo)

Reconhece sozinho o que é cada arquivo:

| O que chega | O que o sistema faz |
|---|---|
| **Nota fiscal** (XML da NF-e, DANFE em PDF ou foto) | Identifica a empresa (CNPJ, nome ou apelido), lança **uma linha por material** no fechamento (data, material, unidade, quantidade, valor unitário, total, NF e pedido) e responde com o total e quanto falta |
| **Cheque escaneado** (frente e verso) | Lê a foto nas quatro orientações; entende o **"Bom p/ 24/09/26"** escrito à mão (canto inferior direito); lê valor, banco, agência, **cooperativa**, conta e número pela linha **CMC-7**; descobre a empresa pelo CNPJ; pega a **lista de pedidos escrita no verso** |
| **Comprovante de Pix, TED ou depósito** | Dá **baixa automática** nas notas citadas e responde quanto ainda falta |
| **Comprovante de depósito de cheque** | Reconhece que é um depósito de cheque (ex.: Bradesco "Depósito de cheque", cheque 616, R$ 4.287,60), acha o cheque pelo número/valor e **compensa o cheque certo**, sem confundir com o cheque do dia |
| **Print do fechamento em andamento** | Lê a tabela linha por linha para conferir e importar |

- Várias pessoas podem mandar (você, o Almir e quem mais estiver cadastrado).
- Comandos: `/fechamento <empresa>`, `/empresas`, `/cheques`, `/notas <empresa>`, `/ajuda`.

### 13.2 Fechamentos

- Cada empresa fecha no **dia 20** (ou no dia escolhido para ela). O fechamento de agosto vai de **21/07 a 20/08**.
- **Escolher o mês**: mostra **só aquele fechamento** (não o apanhado geral).
- Cartão por empresa com total, recebido, **o que falta**, em cheque e atrasados de fechamentos anteriores.
- Relatório em **Excel e PDF no formato da planilha da Prospera**: cabeçalho "Prospera Industria E Serviços LTDA
  03.880.985/0001-85", "Fechamento <Empresa>", colunas DATA, MATERIAL, UNIDADE, QUANT., VALOR UNI., VALOR TOTAL, NOTA FISCAL,
  Nº PEDIDO e o total no rodapé.
- **No dia do fechamento**, o bot envia sozinho o resumo de cada empresa.
- **Mudar o fechamento de uma nota** (lápis → campo *Fechamento*), movendo todas as linhas da mesma NF de uma vez (ex.: NF 7120
  que chegou depois → fechamento setembro/outubro).

### 13.3 Baixa automática

- O valor recebido é dividido entre as notas citadas, **da mais antiga para a mais nova**.
- Sem número de NF: baixa as mais antigas em aberto.
- Valor que não cobre tudo: a nota fica **Parcial** e o fechamento mostra a diferença.
- Dinheiro que chega **antes da nota** vira **crédito da empresa** e baixa sozinho quando a nota chega.
- Qualquer recebimento pode ser **desfeito** (as notas voltam a ficar em aberto).

### 13.4 Cheques pré-datados

- Guardados com número, vencimento (data do depósito), banco, agência, cooperativa, conta, emitente, valor e o CMC-7.
- As notas dos pedidos do cheque ficam **Em cheque**.
- Entram nos **mesmos avisos** dos boletos ("Cheque para depositar hoje").
- **Depositei**: botão que pede a data e, opcionalmente, o comprovante; o cheque é compensado e as notas viram Recebido.
- Ao lançar um recebimento à mão, dá para escolher **"Cheque depositado"** (o sistema sugere o cheque certo).

### 13.5 Notas, Recebimentos e Conferência

- **Notas fiscais**: lista com filtros por empresa, fechamento e situação; editar, mover de fechamento, excluir.
- **Recebimentos**: Pix/TED/depósito com NF, pedidos, pagador, data e hora, valor e ID da transação; desfazer.
- **Conferência**: o que o robô não teve certeza; você confere e confirma ou descarta. É aqui também que se importa o print
  do fechamento.
- **Bot de notas**: token, quem pode enviar, a sua empresa (nome e CNPJ) e o dia do fechamento.

Dados em `dados\empresas.db`, com a planilha `fechamentos.xlsx` (abas Empresas, Notas Fiscais, Cheques, Recebimentos e Histórico).

---

## 14. Notificações

### 14.1 Lembretes

| Lembrete | Padrão |
|---|---|
| **No dia do vencimento** | 3 vezes: 08:00, 12:00 e 16:00 (atalhos para 1, 3 ou 5 vezes; horários livres) |
| **Antes do vencimento** | 1 dia e 3 dias antes, às 09:00 (crie quantos quiser) |
| **Depois de vencido** | Todo dia às 09:00, por até 30 dias (0 = até pagar) |

- Cada lembrete tem os seus **canais**; escolha também os **dias da semana** dos avisos.
- Valem para **boletos**, **Pix** (pela data prevista) e **cheques a depositar**.
- Param quando o lançamento é pago — inclusive pelo botão **Já paguei** da notificação do Windows.
- O sistema confere a cada minuto. Se o computador estava desligado, manda só o lembrete mais recente (não acumula).
- Vencimento no fim de semana avisa que pode ser pago no próximo dia útil.
- **Próximos lembretes**: agenda dos próximos 7 dias.
- **Histórico de avisos**: cada envio registrado.
- **Enviar agora** para testar.

### 14.2 Canais

| Canal | Como configurar |
|---|---|
| **Windows** | Já vem ligado; clicar abre a tela certa |
| **Telegram** | Token do bot; cada pessoa manda `/start` (ou adicione o bot ao grupo); **Procurar pessoas e grupos** e marcar quem recebe — várias pessoas do escritório |
| **E-mail** | Provedor (Gmail, Outlook, Yahoo), usuário, **senha de app** e destinatários |

Ao trocar o **servidor, a porta, a segurança ou o usuário** do e-mail, digite a **senha de novo**: por segurança, a senha
guardada é apagada quando a conexão muda sem ela.

As mensagens trazem a **linha digitável só com números** e o **Pix Copia e Cola**, prontos para pagar pelo celular.

### 14.3 Resumos da semana

| Resumo | Padrão | O que traz |
|---|---|---|
| **Segunda-feira** | 08:00 | Boletos e Pix que vencem na semana, vencidos em aberto, cheques a depositar, fechamentos das empresas que caem na semana, quanto as empresas devem e o saldo do caixa |
| **Sexta-feira** | 17:00 | Quanto foi pago na semana em **boletos, Pix e saídas do caixa**, os maiores pagamentos, os **juros e multas** (quais e com quantos dias de atraso), descontos, onde mais se gastou, o que entrou (caixa e empresas) e o que ficou pendente |

Cada resumo tem horário e canais próprios, sai uma vez no dia (ou assim que o sistema abrir, se o computador estava desligado),
com **Ver como fica** e **Enviar agora**.

---

## 15. Configurações

Quatro abas: **Geral**, **Usuários e acesso**, **Backup e recebimento**, **Saúde do sistema**.

### 15.1 Geral

- **Aplicativo no computador**: iniciar junto com o Windows (opcional: minimizado na bandeja), fechar no X esconde na bandeja,
  **Criar atalhos** (Área de Trabalho e Menu Iniciar). Clicar numa notificação traz o App na tela certa.
- **Banco de dados e planilha**: caminho da planilha, **Abrir planilha**, **Abrir pasta de dados**, **Baixar cópia**.
  Pode deixar a planilha aberta no Excel; edições feitas no Excel em lançamentos existentes voltam para o sistema.
- **Recursos de leitura**: código de barras, texto de PDF, OCR local, fotos HEIC, comprovantes, IA.
- **Como a leitura funciona** e **Atalhos de teclado**: `Ctrl+V`, arrastar arquivos, `/` para buscar, `Alt+1…7` para as telas,
  `Esc` para fechar.
- **Versão do sistema**: versão em uso, data, quantas versões estão guardadas, o que mudou em cada uma e se há
  alterações ainda não guardadas (veja 19.2).
- **Sobre**: versão.

### 15.2 Usuários e acesso

- **Importar boletos de outro sistema** (área do administrador, veja 6.7).
- **Usuários do escritório** (veja 16).
- **Acesso pelo celular (rede Wi-Fi)**: senha de acesso, chave liga/desliga, **QR code** para abrir no celular, lista de
  aparelhos conectados com **Sair deste aparelho**. Reabre sozinho se o endereço do computador mudar.

### 15.3 Backup e recebimento

- **Backup total fora do computador**: pasta do OneDrive, Google Drive, Dropbox, pen drive ou HD externo; horário diário.
  Leva **tudo**: bancos de dados e planilhas (uma cópia por dia, 30 dias), boletos e comprovantes (só os novos), todas as
  configurações, o **código-fonte** e o **histórico de versões**. Botões **Fazer backup agora**, **Gerar pacote completo
  (.zip)** e **Verificar backup**. O menu mostra **Backup em dia**, **atrasado** ou **desligado** (detalhes em 19.1).
- **Receber boletos por e-mail e Telegram**: caixa de e-mail IMAP com senha de app (verificada a cada 5 minutos, sem apagar nem
  marcar como lido; filtro de remetentes opcional) e recebimento pelo bot dos boletos.

### 15.4 Saúde do sistema

Diagnóstico de banco de dados e planilha, lembretes, backup, recebimento por e-mail/Telegram, gravações pendentes, leitura
(OCR/IA), espaço em disco e acesso pela rede. Cada item fica **Funcionando**, **Atenção**, **Problema** ou **Desligado**, com
os botões **Atualizar a planilha agora** e **Limpar os logs**.

### 15.5 Configurações dentro dos módulos

| Onde | O que se configura |
|---|---|
| Notificações | Lembretes, canais, Telegram, e-mail, resumos |
| Caixa → Bot do caixa | Token e ligar/desligar |
| Diesel → Bot do diesel | Token, quem escolhe a máquina, aviso de saldo baixo (R$), horário e tipos dos relatórios automáticos, **nível** dos relatórios (Simples, Detalhado, Completo) |
| Diesel → Preço do litro | Preço de cada combustível |
| Empresas → Bot de notas | Token, quem pode enviar, a sua empresa e o dia do fechamento |

---

## 16. Usuários, perfis e permissões

- **Administrador**: pode tudo, inclusive cadastrar usuários e mudar permissões.
- **Comum**: só o que estiver marcado. Painel, boletos e Pix são liberados para todos.

| Permissão | O que libera |
|---|---|
| Lançar | Ler arquivos e lançar boletos e Pix |
| Dar baixa | Marcar como pago e anexar comprovante |
| Editar/excluir | Editar e excluir lançamentos |
| Gastos | Análise de gastos e fechamento do mês |
| Empresas | Notas fiscais, cheques, recebimentos e fechamentos |
| Caixa | Entradas e saídas em dinheiro |
| Diesel | Compras, abastecimentos, máquinas e relatórios do diesel |
| Avisos | Configurar os lembretes |
| Configurações | Backup, bots, importação e acesso pela rede |

- Quem não tem a permissão **nem vê** a opção, e o servidor **recusa** mesmo que tentem pelo endereço.
- Nunca fica **sem administrador** (o último não pode ser excluído, desativado ou rebaixado).
- **Pedir usuário e senha toda vez que o aplicativo abrir** (ligado a pedido).
- Celulares ficam conectados por 30 dias. Desativar ou trocar a senha de alguém desconecta os aparelhos dessa pessoa.
- A planilha registra **Lançado por** e **Pago por**, e o **Histórico** tem a coluna Usuário.
- Cada pessoa troca a própria senha no menu lateral.

---

## 17. Os bots do Telegram

| Bot | Quem usa | Recebe | Comandos |
|---|---|---|---|
| **Boletos** | Pessoas cadastradas em Notificações → Telegram | Boletos (PDF/foto) e comprovantes | `/vencidos`, `/hoje`, `/semana`, `/previsao`, `/resumo`, `/buscar <nome>`, `/ajuda` |
| **Notas** | Quem está em Empresas → Bot de notas | Notas fiscais, cheques, comprovantes, depósito de cheque, print de fechamento | `/fechamento <empresa>`, `/empresas`, `/cheques`, `/notas <empresa>`, `/ajuda` |
| **Caixa** | Pessoas dos bots de boletos e notas | Cupons e notas de compras em dinheiro | `/resumo`, `/cancelar`, `/ajuda` |
| **Diesel** | Pessoas dos bots de boletos e notas | Canhotos e comprovantes de compra | `/saldo`, `/medias`, `/relatorio [semana\|quinzena\|mes\|ano] [simples\|detalhado\|completo]`, `/maquinas`, `/cancelar`, `/ajuda` |

Regras comuns:
- Arquivos de quem **não está cadastrado** são recusados.
- Arquivos **repetidos** são reconhecidos.
- Nada é lançado às cegas: o que o robô não tem certeza vai para a **Conferência** da tela.

---

## 18. Versão de demonstração

- Dois cliques em **`demonstracao.bat`** abrem um Fin Pro completo, com dados de exemplo, na porta **8010**, ao mesmo tempo
  que o sistema de verdade (porta 8000). A janela mostra o selo *Versão de demonstração*.
- Dados em `dados_demo`: boletos pagos, pendentes e atrasados (com juros), Pix, caixa, três empresas com notas, cheques e
  recebimentos, centros de custo, **diesel** (5 máquinas, 9 semanas de compras S10 e comum e canhotos), usuários e permissões,
  lembretes e resumos ligados.
- **Nada é enviado para fora**: Telegram e e-mail aparecem configurados, mas o envio é bloqueado.
- Abre sem senha; para mostrar as permissões, entre com **demo / demo1234** (administrador), **almir / demo1234** ou
  **juliana / demo1234**.
- `demonstracao.bat --refazer` monta os dados do zero. Os dados reais nunca são tocados.

---

## 19. Banco de dados, planilhas, arquivos e backup

- Os dados ficam em **bancos SQLite** (`boletos.db`, `empresas.db`, `diesel.db`): gravação instantânea e segura.
- As **planilhas Excel** continuam existindo e são geradas sozinhas poucos segundos depois de cada alteração.
- **Planilha aberta no Excel não trava nada**: é atualizada quando o arquivo for fechado.
- **Edições feitas no Excel** em lançamentos existentes voltam para o sistema, sem desfazer o que foi gravado nesse meio-tempo.
- Cada lançamento guarda o **arquivo original** (link clicável na planilha) e o **histórico** de alterações com quem fez.
- **Backups**: cópia diária interna (30 dias) + **backup total fora do computador** (OneDrive, Google Drive, pen drive…).

### 19.1 Backup total

O backup deixou de ser só dos dados: ele leva **tudo o que é preciso para reerguer o Fin Pro em outro computador**.
Dentro da pasta escolhida é criada a pasta `Leitor de Boletos - Backup` com:

| Parte | O que guarda | Como é copiada |
|---|---|---|
| `planilha` | Os três bancos de dados (boletos, empresas, diesel) e as planilhas Excel | Uma cópia por dia; guarda os últimos 30 dias (ajustável) |
| `arquivos` | Boletos, comprovantes, cupons do caixa, canhotos do diesel, fotos | Só o que é novo ou mudou |
| `configuracoes` | Todas as configurações (lembretes, usuários, bots, preços, modelos de importação) e o `.env` | Sempre |
| `codigo` | O código-fonte do sistema | Só o que mudou; o que saiu do sistema sai do backup |
| `versoes` | Todo o histórico de versões num arquivo (`finpro.bundle`) e a versão em uso (`VERSAO.txt`) | A cada backup |
| `pacotes` | **Pacote completo**: tudo acima num único arquivo `.zip` | Toda semana ou todo mês (ou pelo botão); guarda os últimos 4 |
| `manifesto.json` | A lista de todos os arquivos com a impressão digital de cada um | A cada backup |
| `RESTAURAR.bat`, `LEIA-ME.txt` | Restauração com dois cliques e o passo a passo | A cada backup |

- **Conferência automática**: depois de cada backup o sistema abre os bancos copiados, confere se estão íntegros, se
  nenhum comprovante ficou de fora e se o código e as versões estão lá. O botão **Verificar backup** faz a conferência
  completa, arquivo por arquivo (compara a impressão digital). Se algo não bater, o cartão mostra o que foi e a **Saúde
  do sistema** fica em **Problema**.
- **Pacote completo (.zip)**: bom para levar num pen drive ou guardar fora do escritório. Sai sozinho (semanal ou
  mensal) ou pelo botão **Gerar pacote completo (.zip)**.
- **Restaurar**: num computador novo, instale o Python, abra a pasta do backup (ou tenha um pacote `.zip`) e dê dois
  cliques em `RESTAURAR.bat`. Ele monta o sistema inteiro — programa, dados, comprovantes, configurações e versões — numa
  pasta nova. Se a pasta escolhida já tiver dados do Fin Pro, ele **para** em vez de sobrescrever. Depois é só abrir o
  `iniciar.bat`. Os bots do Telegram só devem ser ligados no computador novo depois de desligar o antigo.
- **Cuidado**: a pasta do backup contém os tokens dos bots e as senhas de e-mail. Guarde-a num lugar de confiança.
- Foi testado de ponta a ponta: backup, pacote, conferência, restauração a partir do `.zip` e o sistema restaurado
  abrindo com os mesmos números.

### 19.2 Controle de versão

O **programa** (código-fonte) fica guardado em versões, como "fotografias" numeradas. Isso é separado dos dados.

- Cada versão tem **número** (ex.: v1.9.0), **data** e a **lista do que mudou**, no arquivo `VERSOES.md`.
- Em **Configurações → Geral → Versão do sistema** aparecem a versão em uso, o histórico e o selo **Tudo guardado** ou
  **N alteração(ões) ainda sem versão**.
- Dá para **comparar** duas versões e **voltar** a qualquer uma. Voltar não apaga nada: o código antigo vira uma versão
  nova, e os dados (boletos, comprovantes, configurações) **não são tocados**.
- As versões ficam **só neste computador** (repositório git local, sem servidor) e **não contêm dados, senhas nem
  tokens**. Quem leva o histórico para fora é o backup total (pasta `versoes`).
- Guardar e voltar versões é feito com a ferramenta `versoes.bat`:

| Comando | O que faz |
|---|---|
| `versoes.bat situacao` | Mostra a versão em uso e o que mudou desde a última versão guardada |
| `versoes.bat nova "Título" -m "o que mudou"` | Roda os testes e guarda uma versão nova |
| `versoes.bat listar` | Lista todas as versões |
| `versoes.bat comparar v1.8.0 v1.9.0` | Mostra os arquivos que mudaram entre duas versões |
| `versoes.bat voltar v1.8.0` | Volta o programa para aquela versão |

- Numeração: **correção** aumenta o último número (1.9.0 → 1.9.1), **melhoria** o do meio (1.9.0 → 1.10.0) e
  **mudança grande** o primeiro (1.9.0 → 2.0.0).

---

## 20. Segurança

- Senhas (usuários, administrador, acesso pela rede) guardadas **somente em hash** (PBKDF2-SHA256).
- **5 senhas erradas = 5 minutos de bloqueio** daquele usuário naquele aparelho (os outros usuários continuam entrando).
- Área de administrador fecha sozinha após 20 minutos sem uso.
- Permissões conferidas **no servidor**, não só na tela.
- Sem usuários e sem senha de acesso, **nenhum aparelho de fora entra** (só o próprio computador).
- Pedidos vindos de outros sites são recusados, e as telas não podem ser abertas dentro de outro site.
- Arquivos recebidos que não são PDF nem imagem comum (ex.: SVG) só são baixados, nunca abertos na tela.
- Tokens dos bots aparecem mascarados nas telas.
- Os arquivos de configuração com tokens e senhas de app ficam na pasta `dados`: o computador precisa estar protegido.
- Apenas a análise com IA (quando ligada e acionada) envia um arquivo para fora (API da Anthropic).

---

## 21. Sistema online

**Situação (19/10/2026):** no ar em `https://fin.fabbiol.tech`, numa VPS com EasyPanel, exigindo login de todos. É uma
instalação **separada** da do computador do escritório, com os próprios dados. O código publicado vem da pasta `codigo/` do
repositório `ryannlao/fin-pro` no GitHub. Para publicar uma mudança: seção "Versão online" do `README.md`. Abaixo, o plano
original, mantido como histórico.

### 21.1 Decisão

| Item | Escolha |
|---|---|
| Hospedagem | **VPS Hostinger KVM 2**: 2 vCPU, 8 GB de RAM, 100 GB NVMe, 8 TB de banda |
| Preço | R$ 43,99/mês no plano de 24 meses (**R$ 1.055,76** à vista), renovando por R$ 77,99/mês |
| Sistema operacional | **Ubuntu 24.04 LTS**, aba "SO simples", sem painel de controle |
| Localização | Brasil (São Paulo), se disponível |
| Domínio | Grátis no 1º ano com o plano (ou `.com.br` no registro.br, ~R$ 40/ano) |
| Orçamento | Até R$ 200/mês; o total previsto fica em torno de R$ 85 a 145/mês com backups e domínio |

**Alternativas avaliadas**:
- Magalu Cloud, Locaweb e KingHost (no Brasil, em reais).
- Vultr e Akamai (São Paulo, cobrança em dólar).
- Hetzner e Contabo (Europa, mais baratas).
- Oracle Cloud gratuita (instável).
- **Mini PC próprio** (i5-3210M, 8 GB, SSD 256 GB): funciona, mas depende da luz e da internet do escritório. Precisaria de
  nobreak, cabo de rede e backup externo, e quem cuida da máquina é a empresa. Por isso ficou como segunda opção.

### 21.2 Ajustes que o sistema precisa antes de ir para a internet

1. **Login obrigatório para todos**: hoje o próprio computador entra sem senha; atrás de um servidor, todo acesso pode parecer
   "local".
2. **HTTPS** (cadeado) com o domínio.
3. **Backup automático diário fora do servidor**.
4. **Horário de Brasília** no servidor, para lembretes e resumos.
5. Os avisos do Windows deixam de existir no servidor; continuam Telegram e e-mail. No computador, o Fin Pro abre como
   aplicativo instalado pelo Chrome/Edge.
6. **Mudança dos dados** num horário combinado, com o App local desligado (dois bots ligados ao mesmo tempo disputariam as
   mensagens do Telegram).

A senha do servidor é criada e guardada por você e **nunca deve ser enviada pelo chat**.

---

## 22. Pendências e próximos passos

| # | Item | Situação |
|---|---|---|
| 1 | **Menu Relatórios** (central) | Pronto e testado; falta liberar a leitura de `web/js/app.js` para colocar no menu |
| 2 | **Colocar online** | Aguardando a contratação da VPS; depois, os ajustes do item 21.2 e a instalação |
| 3 | **Horas extras** | Citadas junto com o caixa; aguardando a planilha ou um print e a regra de cálculo (por pessoa, valor da hora, 50%/100%) |
| 4 | **Diesel em Gastos** | Decidir se as compras de diesel contam em Gastos ou se o posto já é pago como boleto/Pix |
| 5 | **Cheque 616** | Continua "Em carteira" nos dados reais; confirmar a baixa |
| 6 | **Posto da compra de 1.000 L** | Ainda como "Demais telefones" nos dados reais; trocar para "Pereira da Silva & Ferreira da Silva" |
| 7 | **Comprovante do caixa no Fechamento do mês** | O botão "Ver" das saídas em dinheiro aponta para o endereço dos boletos; corrigir |
| 8 | **Centro de custo** | Cerca de 72 boletos sem centro de custo; possível sugestão automática |
| 9 | **IA (Claude)** | Opcional; ligar com uma chave da Anthropic, com limite de gasto mensal |
| 10 | **Atalho da demonstração** | Atalho na Área de Trabalho para a versão de demonstração |

---

## 23. Referência rápida

### Como começar o dia

1. Abra o **Painel**: vencidos, o que vence em 7 dias e a previsão de saídas.
2. Veja o **sininho** e os contadores azuis do menu (arquivos esperando conferência).
3. Pague pelo celular com a **linha digitável** (só números) que chega no Telegram e mande o **comprovante** para o bot: a baixa
   é automática, com juros.

### Fim do mês

1. **Gastos → Fechamento do mês → Pacote para o contador (.zip)**.
2. **Comprovantes → Pagos sem comprovante**, para completar o que faltar.
3. **Diesel → Relatórios → Mês** (Simples para ver rápido; Completo ou Excel para guardar).
4. **Empresas → Fechamentos** (o bot já envia no dia 20).

### Atalhos

| Tecla | Ação |
|---|---|
| `Ctrl` + `V` | Colar imagem, linha digitável ou Pix Copia e Cola |
| Arrastar arquivo | Ler boletos/comprovantes (no Diesel, canhotos e comprovantes do posto) |
| `/` | Buscar (boletos, comprovantes) |
| `Alt` + `1`…`7` | Painel, Ler, Boletos, Pix, Gastos, Notificações, Configurações |
| `Esc` | Fechar janelas |
| ‹ › (teclado) | Passar comprovantes no visualizador |

### Arquivos para abrir o sistema

| Arquivo | O que faz |
|---|---|
| `iniciar.bat` | Abre o Fin Pro de verdade (porta 8000) |
| `demonstracao.bat` | Abre a versão de demonstração (porta 8010) |
| `demonstracao.bat --refazer` | Recria os dados de demonstração |
