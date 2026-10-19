# Fin Pro

> Escopo do produto. O uso detalhado de cada tela está no [manual](DOCUMENTACAO_FIN_PRO.md); as regras técnicas, na
> [especificação](docs/especificacao/00-LEIA-ME.md). Atualize este documento quando objetivo, escopo, restrições ou critérios mudarem.

## Problema e objetivo

Um escritório paga boletos e Pix, controla dinheiro em espécie, o diesel comprado no posto para as máquinas e recebe de empresas
que compram a prazo. Antes, isso dependia de digitar linhas digitáveis, lembrar vencimentos, procurar comprovantes e manter
planilhas separadas, o que gerava juros por atraso e retrabalho no fechamento do mês.

O Fin Pro faz o escritório **digitar o mínimo**: quase tudo entra por PDF, foto, e-mail ou Telegram, o sistema lê e confere, uma
pessoa revisa e lança, e depois ele avisa os vencimentos, dá baixa pelo comprovante (com juros e desconto) e guarda tudo.

## Público e papéis

- **Dono do escritório** (administrador, não técnico): lança boletos, acompanha o painel, configura o sistema.
- **Equipe do escritório**: paga as contas e tem os comprovantes; lança conforme as permissões que o administrador liberar.
- **Pessoas na rua** (motoristas, compras): mandam canhotos de diesel, cupons e notas pelos bots do Telegram.
- Perfis: administrador e comum, com 9 permissões (lançar, dar baixa, editar/excluir, gastos, empresas, caixa, diesel, avisos,
  configurações). Detalhes no manual, seção 16.

## Fluxos essenciais

| Fluxo | Entrada | Resultado esperado |
|---|---|---|
| Lançar boleto | PDF, foto, linha colada, e-mail ou Telegram | Boleto lido e conferido (dígitos verificadores, valor e vencimento do código), revisado e gravado |
| Pagar e dar baixa | Comprovante do banco | Lançamento certo marcado como pago, com valor pago, juros/multa e desconto |
| Ser avisado | Vencimentos próximos ou passados | Lembretes no Windows, Telegram e e-mail nos horários configurados; resumos de segunda e sexta |
| Pix a pagar | Copia e Cola, QR code ou chave | Pix na mesma fila dos boletos |
| Caixa | Entrada ou foto do cupom | Movimento do dinheiro em espécie com saldo |
| Diesel | Comprovante de compra e canhotos | Saldo em reais no posto, consumo por máquina e relatórios em três níveis |
| Empresas a prazo | Nota fiscal, cheque, comprovante de recebimento | Fechamento por empresa (dia 20) com baixa automática |
| Fechar o mês | Lançamentos do mês | Pacote para o contador (PDF, Excel e comprovantes) |
| Proteger os dados | Backup diário | Cópia total (dados, comprovantes, configurações, código, versões) restaurável com dois cliques |

## Escopo atual

Painel, Ler boletos, Boletos lançados, Pagamentos Pix, Comprovantes, Caixa, Diesel, Gastos, Empresas, Notificações e
Configurações; 4 bots do Telegram; acesso pelo celular na rede local; versão de demonstração; backup total e controle de versão;
site de apresentação (`site/`). Situação de cada item: [VERSOES.md](VERSOES.md).

## Fora do escopo por enquanto

- **Central de Relatórios no menu:** pronta e testada, aguardando autorização para editar `web/js/app.js`.
- **Versão online** (VPS Hostinger KVM 2, Ubuntu 24.04): decidida, ainda não contratada nem preparada (login obrigatório, HTTPS,
  backup fora do servidor, fuso horário).
- **Horas extras:** aguardando a regra de cálculo.
- **IA na leitura:** existe, mas fica desligada sem chave da Anthropic.

## Requisitos e restrições

- Português do Brasil; datas `dd/mm/aaaa`; valores em reais.
- Roda no Windows do escritório, sem depender de internet para ler boletos; os dados ficam no computador.
- A planilha Excel continua existindo e é gerada a partir do banco; edições feitas no Excel voltam para o sistema.
- Nada é lançado às cegas: o que a leitura ou os bots não têm certeza vai para conferência.
- Senhas só em hash; permissões conferidas no servidor; tokens mascarados nas telas.
- Pilha mantida: Python/FastAPI, SQLite, JavaScript sem build. Não há banco PostgreSQL, ORM ou framework de interface.

## Suposições e decisões pendentes

- Se as compras de diesel entram em Gastos ou se o posto já é pago como boleto/Pix: **decisão do usuário pendente**.
- Sugestão automática de centro de custo para os boletos sem centro: ideia registrada, não decidida.
- Nomes que parecem de clientes reais na demonstração: troca sugerida, aguardando o usuário.

## Critérios de aceite do produto

- Um boleto válido lido de PDF ou foto chega com linha, valor e vencimento iguais aos do código; uma linha inválida é sinalizada
  e não é lançada sem revisão.
- Um comprovante dá baixa no lançamento certo ou mostra as opções quando há dúvida; nunca escolhe às cegas.
- Lembretes param quando o lançamento é pago.
- O backup restaura o sistema inteiro em outra pasta, e a restauração recusa sobrescrever dados existentes.

## Próxima entrega

A próxima mudança do produto depende do usuário (Relatórios no menu, versão online ou horas extras). Mudanças de ferramenta e
harness ficam em [docs/setup.md](docs/setup.md).
