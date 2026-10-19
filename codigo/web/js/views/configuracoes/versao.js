// Configurações · Versão do sistema: qual versão está em uso, o que mudou em cada uma e se há algo ainda não guardado.
import { icone } from "../../icons.js";
import { dataBR, dataHoraBR, esc } from "../../ui.js";

const VISIVEIS = 4; // versões que aparecem sem precisar abrir "ver todas"

/** Texto do histórico: escapa, mostra os trechos entre crases (nomes de arquivos) como código e **assim** em negrito. */
const texto = (t) => esc(t).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

function htmlVersoes(lista, emUso) {
  return lista.map((v) => `<details class="versao-item" ${v.versao === emUso ? "open" : ""}>
      <summary><span class="chip ${v.versao === emUso ? "ok" : ""}" ${v.versao === emUso ? 'title="Versão em uso"' : ""}>v${esc(v.versao)}</span>
        <strong>${texto(v.titulo)}</strong><span class="sutil">${dataBR(v.data)}</span></summary>
      ${v.itens.length ? `<ul class="lista-info">${v.itens.map((i) => `<li>${texto(i)}</li>`).join("")}</ul>` : ""}
    </details>`).join("");
}

export function htmlVersao(v) {
  if (!v) return "";
  const historico = v.historico || [];
  let situacao;
  if (!v.disponivel) {
    situacao = `<span class="chip aviso" title="A pasta do sistema não tem repositório git">Sem controle de versão</span>`;
  } else if (v.pendentes) {
    situacao = `<span class="chip aviso" title="Há mudanças no código que ainda não foram guardadas como uma versão">${v.pendentes} alteração(ões) ainda sem versão</span>`;
  } else {
    situacao = `<span class="chip ok">Tudo guardado</span>`;
  }
  const pendentes = v.disponivel && v.pendentes && (v.arquivos_pendentes || []).length
    ? `<details class="rede-ajuda"><summary>Ver os ${v.pendentes} arquivo(s) alterado(s) desde a v${esc(v.versao)}</summary>
        <ul class="lista-info mono">${v.arquivos_pendentes.map((a) => `<li>${esc(a)}</li>`).join("")}${v.pendentes > v.arquivos_pendentes.length ? `<li>… e mais ${v.pendentes - v.arquivos_pendentes.length}</li>` : ""}</ul>
        <p class="sutil">Elas já estão valendo no sistema; só falta registrar como uma versão nova.</p></details>`
    : "";
  return `<div class="card col-inteira" id="card-versao">
    <div class="rede-topo"><h3>${icone("relogio", 18)} Versão do sistema</h3>${situacao}</div>
    <p style="color:var(--texto-2)">Você está usando o <strong>Fin Pro v${esc(v.versao)}</strong>${v.data ? `, de ${dataBR(v.data)}` : ""}.
      ${v.disponivel ? `Há <strong>${v.versoes_guardadas}</strong> versão(ões) guardada(s)${v.commit_data ? `; a última foi registrada em ${dataHoraBR(v.commit_data)}` : ""}.` : ""}</p>
    ${pendentes}
    <div class="versoes">${htmlVersoes(historico.slice(0, VISIVEIS), v.versao)}</div>
    ${historico.length > VISIVEIS ? `<details class="rede-ajuda"><summary>Ver as ${historico.length - VISIVEIS} versões anteriores</summary>
      <div class="versoes">${htmlVersoes(historico.slice(VISIVEIS), v.versao)}</div></details>` : ""}
    <details class="rede-ajuda"><summary>Como funcionam as versões?</summary>
      <ul class="lista-info">
        <li>Cada versão é um <strong>ponto guardado do código</strong> do sistema, com a lista do que mudou. Dá para comparar duas versões e <strong>voltar</strong> a qualquer uma.</li>
        <li>Voltar a uma versão não apaga nada: o código antigo vira uma versão nova, e os <strong>seus dados não são tocados</strong> (boletos, comprovantes e configurações ficam como estão).</li>
        <li>As versões guardam só o programa. Quem protege os dados é o <a href="#/config?aba=integracoes">backup</a>, que também leva o código e este histórico.</li>
        <li>Guardar uma versão ou voltar a outra é feito por quem mantém o sistema, com a ferramenta <code>ferramentas/versao.py</code> (ou o atalho <code>versoes.bat</code>).</li>
      </ul></details>
  </div>`;
}
