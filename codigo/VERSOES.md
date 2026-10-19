# Histórico de versões do Fin Pro

> Cada versão é um ponto guardado do sistema, com tudo o que mudou. Dá para ver, comparar e voltar a qualquer uma.
> Este arquivo é atualizado pela ferramenta `ferramentas/versao.py` (não precisa editar à mão).
> Numeração: **X.Y.Z** — X muda em reformulações grandes, Y em funções novas, Z em correções.

## v1.12.1 — 19/10/2026 — Correções de segurança da revisão de 19/10
- Sem senha e sem usuários, nenhum aparelho de fora entra mais (antes, uma VPS nova ou um backup sem usuários deixava os dados abertos para a internet).
- Trocar o servidor do e-mail de avisos sem digitar a senha apaga a senha guardada: ela não pode mais ser enviada para um servidor de outra pessoa.
- Planilha completa (tem o Caixa), prévia do resumo semanal e cancelar gravação agora respeitam as permissões de cada pessoa.
- Senha errada bloqueia só aquele usuário naquele endereço: na VPS, um erro não tranca mais o escritório inteiro.
- As telas não podem mais ser embutidas dentro de outro site (proteção contra cliques enganados).
- Biblioteca urllib3 atualizada (falhas conhecidas na 2.7.0).

## v1.12.0 — 19/10/2026 — Versão do computador e versão online juntas
- Trazido da versão online (VPS): Dockerfile, docker-compose.yml para o EasyPanel, requirements.vps.txt e iniciar.sh/iniciar.command para Linux e Mac.
- Na VPS, o backup passa sozinho para a pasta do servidor e o aviso do Windows é desligado fora do Windows; a Saúde do sistema não acusa mais falha de canal desligado.
- Corrigido o "Not Found" ao abrir comprovantes no Caixa, no Diesel e nas Empresas.
- docker-compose.yml com LEITOR_URL=https://fin.fabbiol.tech, exigido pela proteção contra outros sites da v1.11.
- Mantida a tela de Configurações original (a versão online tinha sido refeita às pressas porque a pasta sumiu do Git).
- Versões listadas pelo número (antes, duas guardadas no mesmo segundo podiam sair fora de ordem).

## v1.11.0 — 19/10/2026 — Ferramentas para agentes de IA e correções de segurança
- Instruções para agentes (`AGENTS.md`, `CLAUDE.md`), `PRODUCT.md` e documentos de arquitetura, telas, preparo, qualidade e setup, ligados à especificação existente.
- Ferramentas integradas: Superpowers, Ponytail, Context7, Chrome DevTools MCP (no projeto), RTK, Graphify e agent-browser (no computador); roteiros de revisão de segurança e de melhoria do harness.
- Verificação única `verificar.bat`: Ruff (Python) e ESLint (telas) adotados com medição, mais os testes.
- Segurança: o sistema recusa pedidos vindos de outros sites (DNS rebinding e pedido forjado) e anexos SVG/HTML não abrem mais como página ativa.
- Correções: o carnê não gera mais um boleto fantasma nem perde uma segunda linha colada a símbolos; o bot volta a funcionar com Python 3.10; a chave "pedir login" de Configurações não dá mais erro depois de salvar.
- Testes de tela consertados (título antigo e espera fixa); 273 testes.

## v1.10.0 — 12/10/2026 — Site de apresentação do Fin Pro
- Site de apresentação (`site/index.html`), no estilo de página de venda: todos os módulos, bots do Telegram, celular, usuários, segurança, backup, ficha técnica, evolução e perguntas frequentes.
- Leitor de linha digitável que funciona na própria página, com as mesmas regras de conferência do sistema.
- Telas tiradas do sistema com dados de exemplo e nomes inventados; `site/capturar_telas.py` refaz as capturas e `site/montar.py` remonta a página.

## v1.9.1 — 12/10/2026 — Ajustes visuais em Gastos e no histórico de versões
- Gastos: os valores dos seis cartões do topo não ficam mais cortados em telas menores.
- Fechamento do mês: o quadro **Por centro de custo** voltou a ocupar a largura toda do cartão.
- Versão do sistema: o histórico mostra o negrito corretamente.

## v1.9.0 — 10/10/2026 — Controle de versão e backup total
- Controle de versão do código: cada versão fica guardada com número, data e a lista do que mudou (`VERSOES.md`); dá para comparar e voltar a qualquer uma sem tocar nos dados (`versoes.bat`).
- Cartão **Versão do sistema** em Configurações → Geral: versão em uso, histórico e alterações ainda não guardadas.
- Backup total: além dos bancos, planilhas e comprovantes, leva todas as configurações, o código-fonte e o histórico de versões.
- Pacote completo num único arquivo .zip (semanal ou mensal, ou pelo botão), guardando os últimos 4.
- Conferência do backup: bancos íntegros, nenhum comprovante faltando e cada arquivo igual ao que foi copiado (botão **Verificar backup**); falha aparece na Saúde do sistema.
- Restauração do sistema inteiro em outro computador com dois cliques (`RESTAURAR.bat`), a partir da pasta do backup ou de um pacote .zip.
- Documentação, especificação técnica e kit atualizados; 273 testes.

## v1.8.0 — 07/10/2026 — Documentação completa, especificação técnica e kit de reconstrução
- Manual de uso do sistema inteiro (`DOCUMENTACAO_FIN_PRO.md`).
- Especificação técnica em 27 documentos, com anexos gerados do próprio código.
- Kit para reconstruir o Fin Pro do zero em outra conversa.
- Início do controle de versão: este é o primeiro ponto guardado.

## v1.7.0 — 06/10/2026 — Diesel em reais, relatório em três níveis e relatório geral
- Saldo do diesel passou a ser em reais (compras pagas menos o valor de cada abastecimento).
- Relatório do diesel em três níveis: Simples, Detalhado e Completo, na tela, no Telegram e no Excel.
- Pontos de atenção do diesel, comparação com o período anterior e consumo de cada trecho.
- Relatório geral do mês (central de Relatórios), com juros, últimos 12 meses, caixa, diesel e empresas.

## v1.6.0 — 29/09/2026 — Controle de diesel
- Módulo Diesel: compras no posto, abastecimentos por máquina, médias e consumo (L/h e km/L).
- Bot do diesel no Telegram, com relatórios automáticos semanal, quinzenal e mensal.
- Preço do litro, reconhecimento do combustível, envio de canhoto pela tela e canhoto com dois combustíveis.
- Correção do saldo do diesel e do nome do posto lido no comprovante.

## v1.5.0 — 24/09/2026 — Juros à vista, central de comprovantes e depósito de cheque
- Juros e multas visíveis nas listas, no calendário, no Painel e em Gastos.
- Menu Comprovantes: busca com filtros em todas as partes do sistema e download em ZIP.
- Comprovante de depósito de cheque reconhecido; leitura do número do cheque corrigida.

## v1.4.0 — 22/09/2026 — Caixa, resumos da semana, nome Fin Pro e demonstração
- Módulo Caixa (entradas e saídas em dinheiro), com relatórios e bot do caixa.
- Resumos de segunda (o que vence) e de sexta (o que foi pago, com juros).
- Nome do sistema mudou para Fin Pro; linha digitável copiada só com números.
- Versão de demonstração para mostrar a clientes.

## v1.3.0 — 18/09/2026 — Empresas, cheques e permissões
- Módulo Empresas: notas fiscais, cheques pré-datados, recebimentos e fechamento no dia 20.
- Bot de notas fiscais, baixa automática e importação do fechamento em andamento.
- Administrador, perfis e permissões por pessoa; login ao abrir o aplicativo.
- Leitura do cheque com "bom para" e pedidos do verso; escolha do fechamento de cada nota.

## v1.2.0 — 17/09/2026 — Backup, usuários, comprovantes e banco de dados
- Backup fora do computador, login por pessoa e histórico de quem fez o quê.
- Baixa automática pelo comprovante, com valor pago, juros e desconto.
- Boletos recebidos por e-mail e Telegram; comandos no bot.
- Fechamento do mês para o contador; previsão de saídas; Saúde do sistema.
- Dados em banco SQLite, com a planilha Excel gerada automaticamente.

## v1.1.0 — 16/09/2026 — Importação, administrador e avisos para várias pessoas
- Importar boletos de outro sistema, em área protegida por senha de administrador.
- Sininho com avisos vistos e dispensados.
- Avisos do Telegram para várias pessoas e grupos.

## v1.0.0 — 14/09/2026 — Leitor de boletos
- Leitura de boletos em PDF e foto (código de barras, texto e OCR) com planilha como banco de dados.
- Lembretes de vencimento no Windows, Telegram e e-mail, com horários configuráveis.
- Aplicativo de desktop que inicia com o Windows; acesso pelo celular na rede.
- Centros de custo, análise de gastos e Pagamentos Pix.
