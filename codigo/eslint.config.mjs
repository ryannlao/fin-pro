// Lint do JavaScript das telas (ESLint, só desenvolvimento). Rode: npx eslint
// Perfil: regras recomendadas do ESLint. Regras que tinham violações na adoção (19/10/2026) começam como aviso,
// com a contagem e o plano de redução em docs/quality.md; as demais são erro.
import js from "@eslint/js";
import globals from "globals";

export default [
  { ignores: ["node_modules/**", "dados/**", "dados_*/**", ".venv/**", "Kit - Novo Fin Pro/**", "site/index.html", "site/img/**", "graphify-out/**"] },
  js.configs.recommended,
  {
    // Ocorrências antigas medidas na adoção: no-unused-vars 282 (278 importações/parâmetros sem uso, 4 variáveis) e
    // no-useless-assignment 5 (valores iniciais sobrescritos). Avisos até zerar; depois voltam a ser erro.
    rules: { "no-unused-vars": "warn", "no-useless-assignment": "warn" },
  },
  {
    files: ["web/js/**/*.js"],
    languageOptions: { ecmaVersion: 2023, sourceType: "module", globals: { ...globals.browser } },
  },
  {
    files: ["web/sw.js"],
    languageOptions: { ecmaVersion: 2023, sourceType: "script", globals: { ...globals.serviceworker } },
  },
  {
    files: ["site/partes/*.js"],
    languageOptions: { ecmaVersion: 2023, sourceType: "script", globals: { ...globals.browser } },
  },
];
