# Telas e acessibilidade

## Direção

Público não técnico, em português, no computador do escritório e no celular. Telas densas de informação, mas legíveis, com a
ação principal sempre visível. Detalhes de cada tela: [manual](../DOCUMENTACAO_FIN_PRO.md).

## Sistema existente

- **Tokens e estilos:** `web/css/app.css` é a fonte da verdade (variáveis em `:root`, como `--marca: #0d7a64`, e tema escuro com
  `data-theme="dark"`). Não mantenha valores concorrentes aqui.
- **Componentes e telas:** `web/js/ui.js` (cartões, modais, toasts, formatação) e `web/js/views/<tela>/`. Descrição:
  [10-front-end-e-desktop](especificacao/10-front-end-e-desktop.md) e [A5-front-end](especificacao/A5-front-end.md).
- **Site de apresentação:** identidade própria em `site/partes/00-estilo.css`, derivada das cores do sistema.
- Não há biblioteca de componentes (nem shadcn, nem React).

## Interação

HTML semântico, navegação por teclado, foco visível (`:focus-visible` com a cor da marca), contraste adequado, campos com rótulo,
erros ao lado do campo, progresso e resultado nas operações demoradas (toasts e esqueletos), respeito a movimento reduzido.
Atalhos: `Ctrl+V`, arrastar arquivos, `/` para buscar, `Alt+1…7`, `Esc` (manual, seção 23).

## Layout e revisão

- Menu lateral no computador; no celular, menu recolhido e o botão "Tirar foto do boleto" em destaque.
- Estados de vazio, erro e carregamento existem nas listas principais.
- Mudança visual se confere no navegador embutido com a demonstração (porta 8010), em computador e celular, claro e escuro.
- Os testes de tela (`tests/test_telas.py`) abrem todas as telas no Edge e falham com erro no console.

## Manutenção

Mudou uma regra visual: atualize `web/css/app.css` e, se a regra for nova, este documento.
