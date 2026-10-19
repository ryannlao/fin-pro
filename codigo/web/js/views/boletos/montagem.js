// Boletos lançados · montagem da tela, filtros e eventos.
import { api } from "../../api.js";
import { icone } from "../../icons.js";
import {
  abrirModal, brl, compacto, confirmar, copiar, dataBR, dataHoraBR, debounce, esc, isoDeData, mensagemErro, numeroBR,
  parseValor, seloSituacao, toast,
} from "../../ui.js";
import { abrirDetalhes } from "../../detalhes.js";
import { pode } from "../../estado.js";
import { NOVO_CENTRO, carregarCentros, escolherCentro, opcoesCentro, opcoesFiltroCentro, tratarNovoCentro } from "../../centros.js";
import { CHIPS, filtros, selecionados, tela } from "./estado.js";
import { aoClicarCalendario } from "./calendario.js";
import { aoAcaoLote, aoClicarTabela, aoMarcar, aoPaginar, carregar, confirmarPagamento, linha } from "./lista.js";

export async function montar(el, params) {
  tela.raiz = el;
  if (params.has("situacao") || params.has("q") || params.has("centro")) {
    filtros.situacao = params.get("situacao") || "";
    filtros.q = params.get("q") || "";
    filtros.centro = params.get("centro") || "";
    filtros.de = filtros.ate = "";
    filtros.pagina = 1;
    if (params.has("q") || params.has("centro")) tela.modo = "lista";
  }
  selecionados.clear();

  el.innerHTML = `
    <section class="card barra-filtros">
      <div class="filtros-linha">
        <label class="busca">${icone("busca", 16)}
          <input id="f-busca" class="input" type="search" value="${esc(filtros.q)}"
                 placeholder="Buscar beneficiário, nº do documento, CPF/CNPJ ou linha digitável  ( / )"></label>
        <div class="alternar-modo" role="tablist" aria-label="Modo de exibição">
          <button role="tab" data-modo="lista">${icone("lista", 15)} Lista</button>
          <button role="tab" data-modo="calendario">${icone("calendario", 15)} Calendário</button>
        </div>
        <div class="menu-ancora">
          <button class="btn" id="btn-exportar" aria-haspopup="menu">${icone("download", 16)} Exportar</button>
          <div class="menu" id="menu-exportar" role="menu" hidden>
            <button data-formato="xlsx">${icone("planilha", 16)}<span>Excel<small>Somente os registros filtrados</small></span></button>
            <button data-formato="csv">${icone("arquivo", 16)}<span>CSV<small>Separado por ponto e vírgula</small></span></button>
            ${pode("caixa") ? `<button data-formato="planilha">${icone("download", 16)}<span>Planilha completa<small>O arquivo boletos.xlsx original</small></span></button>` : ""}
          </div>
        </div>
        <a class="btn" href="#/comprovantes?tipo=boleto" title="Buscar os comprovantes dos boletos">${icone("clipe", 16)} Comprovantes</a>
        <button class="btn" id="btn-abrir-excel">${icone("externo", 16)} Abrir no Excel</button>
      </div>
      <div class="filtros-linha">
        <div class="chips-situacao" id="chips-situacao">
          ${CHIPS.map(([valor, rotulo]) => `<button class="chip-filtro" data-situacao="${valor}">${rotulo}</button>`).join("")}
        </div>
        <select id="f-centro" class="input input-sm filtro-centro" aria-label="Centro de custo">
          <option value="">Todos os centros de custo</option>
          ${filtros.centro ? `<option value="${esc(filtros.centro)}" selected>${esc(filtros.centro === "__sem__" ? "Sem centro de custo" : filtros.centro)}</option>` : ""}
        </select>
        <div class="periodo" id="periodo">
          ${icone("calendario", 16)}
          <select id="f-campo-data" class="input input-sm" aria-label="Filtrar por data de">
            <option value="vencimento">Vencimento</option>
            <option value="data_lancamento">Lançamento</option>
            <option value="data_pagamento">Pagamento</option>
          </select>
          <input type="date" id="f-de" class="input input-sm" aria-label="De">
          <span>até</span>
          <input type="date" id="f-ate" class="input input-sm" aria-label="Até">
          <select id="f-rapido" class="input input-sm" aria-label="Período rápido">
            <option value="">Período rápido…</option>
            <option value="mes">Este mês</option>
            <option value="proximo_mes">Próximo mês</option>
            <option value="30">Próximos 30 dias</option>
            <option value="ano">Este ano</option>
            <option value="limpar">Limpar período</option>
          </select>
        </div>
      </div>
    </section>

    <section class="resumo-lista" id="resumo"></section>

    <section class="card tabela-card" id="card-lista">
      <div class="acoes-lote" id="acoes-lote" hidden></div>
      <div class="tabela-wrap" id="tabela"><div style="padding:18px">${'<div class="esqueleto" style="height:44px;margin-bottom:8px"></div>'.repeat(6)}</div></div>
      <footer class="paginacao" id="paginacao"></footer>
    </section>

    <section class="card calendario-card" id="card-calendario" hidden></section>`;

  sincronizarControles();
  ligarEventos();
  carregarCentros().then((lista) => {
    const select = tela.raiz?.querySelector("#f-centro");
    if (select) select.innerHTML = opcoesFiltroCentro(lista, filtros.centro);
  }).catch(() => {});
  await carregar();

  // Botão "Já paguei" das notificações do Windows abre #/boletos?pagar=ID
  const pagar = Number(params.get("pagar"));
  if (pagar) {
    history.replaceState(null, "", "#/boletos");
    confirmarPagamento(pagar);
  }
}

export function desmontar() {
  document.removeEventListener("keydown", atalhoBusca);
  document.removeEventListener("click", fecharMenuFora);
  window.removeEventListener("boletos:atualizar", recarregarExterno);
  tela.raiz = null;
}

export const recarregarExterno = () => carregar();

export function sincronizarControles() {
  tela.raiz.querySelectorAll("[data-situacao]").forEach((b) => b.classList.toggle("ativo", b.dataset.situacao === filtros.situacao));
  tela.raiz.querySelectorAll("[data-modo]").forEach((b) => {
    b.classList.toggle("ativo", b.dataset.modo === tela.modo);
    b.setAttribute("aria-selected", String(b.dataset.modo === tela.modo));
  });
  const filtroCentro = tela.raiz.querySelector("#f-centro");
  if ([...filtroCentro.options].some((o) => o.value === filtros.centro)) filtroCentro.value = filtros.centro;
  tela.raiz.querySelector("#f-campo-data").value = filtros.campo_data;
  tela.raiz.querySelector("#f-de").value = filtros.de;
  tela.raiz.querySelector("#f-ate").value = filtros.ate;
  tela.raiz.querySelector("#card-lista").hidden = tela.modo !== "lista";
  tela.raiz.querySelector("#card-calendario").hidden = tela.modo !== "calendario";
  tela.raiz.querySelector("#periodo").hidden = tela.modo !== "lista";
}

export function atalhoBusca(e) {
  if (e.key === "/" && !e.target.closest("input, textarea, select")) {
    e.preventDefault();
    tela.raiz?.querySelector("#f-busca")?.focus();
  }
}

export function fecharMenuFora(e) {
  const menu = tela.raiz?.querySelector("#menu-exportar");
  if (menu && !menu.hidden && !e.target.closest(".menu-ancora")) menu.hidden = true;
}

export function ligarEventos() {
  document.addEventListener("keydown", atalhoBusca);
  document.addEventListener("click", fecharMenuFora);
  window.addEventListener("boletos:atualizar", recarregarExterno);

  const recarregar = () => { filtros.pagina = 1; selecionados.clear(); carregar(); };

  tela.raiz.querySelector("#f-busca").addEventListener("input", debounce((e) => { filtros.q = e.target.value; recarregar(); }, 280));
  tela.raiz.querySelector("#chips-situacao").addEventListener("click", (e) => {
    const chip = e.target.closest("[data-situacao]");
    if (!chip) return;
    filtros.situacao = chip.dataset.situacao;
    sincronizarControles();
    recarregar();
  });
  tela.raiz.querySelector(".alternar-modo").addEventListener("click", (e) => {
    const botao = e.target.closest("[data-modo]");
    if (!botao || botao.dataset.modo === tela.modo) return;
    tela.modo = botao.dataset.modo;
    try { localStorage.setItem("boletos_modo", tela.modo); } catch { /* tela.modo privado */ }
    sincronizarControles();
    carregar();
  });
  tela.raiz.querySelector("#f-centro").addEventListener("change", (e) => { filtros.centro = e.target.value; recarregar(); });
  tela.raiz.querySelector("#f-campo-data").addEventListener("change", (e) => { filtros.campo_data = e.target.value; if (filtros.de || filtros.ate) recarregar(); });
  tela.raiz.querySelector("#f-de").addEventListener("change", (e) => { filtros.de = e.target.value; recarregar(); });
  tela.raiz.querySelector("#f-ate").addEventListener("change", (e) => { filtros.ate = e.target.value; recarregar(); });
  tela.raiz.querySelector("#f-rapido").addEventListener("change", (e) => {
    aplicarPeriodoRapido(e.target.value);
    e.target.value = "";
    sincronizarControles();
    recarregar();
  });

  const menu = tela.raiz.querySelector("#menu-exportar");
  tela.raiz.querySelector("#btn-exportar").addEventListener("click", () => { menu.hidden = !menu.hidden; });
  menu.addEventListener("click", (e) => {
    const botao = e.target.closest("[data-formato]");
    if (!botao) return;
    menu.hidden = true;
    const { pagina, por_pagina, ...params } = filtros;
    window.location.href = api.urlExportar({ ...params, formato: botao.dataset.formato });
  });

  tela.raiz.querySelector("#btn-abrir-excel").addEventListener("click", async () => {
    try {
      await api.post("/api/planilha/abrir");
      toast("Abrindo a planilha no Excel… Se lançar boletos com ela aberta, eles serão gravados quando você fechar.", "info", { duracao: 7000 });
    } catch (erro) {
      toast(mensagemErro(erro), "erro");
    }
  });

  tela.raiz.querySelector("#tabela").addEventListener("click", aoClicarTabela);
  tela.raiz.querySelector("#tabela").addEventListener("change", aoMarcar);
  tela.raiz.querySelector("#paginacao").addEventListener("click", aoPaginar);
  tela.raiz.querySelector("#paginacao").addEventListener("change", (e) => {
    if (e.target.id === "por-pagina") { filtros.por_pagina = Number(e.target.value); filtros.pagina = 1; carregar(); }
  });
  tela.raiz.querySelector("#acoes-lote").addEventListener("click", aoAcaoLote);
  tela.raiz.querySelector("#card-calendario").addEventListener("click", aoClicarCalendario);
}

export function aplicarPeriodoRapido(opcao) {
  const hoje = new Date();
  const inicioMes = (desloc) => new Date(hoje.getFullYear(), hoje.getMonth() + desloc, 1);
  const fimMes = (desloc) => new Date(hoje.getFullYear(), hoje.getMonth() + desloc + 1, 0);
  if (opcao === "mes") { filtros.de = isoDeData(inicioMes(0)); filtros.ate = isoDeData(fimMes(0)); }
  else if (opcao === "proximo_mes") { filtros.de = isoDeData(inicioMes(1)); filtros.ate = isoDeData(fimMes(1)); }
  else if (opcao === "30") { filtros.de = isoDeData(hoje); filtros.ate = isoDeData(new Date(hoje.getTime() + 30 * 86400000)); }
  else if (opcao === "ano") { filtros.de = `${hoje.getFullYear()}-01-01`; filtros.ate = `${hoje.getFullYear()}-12-31`; }
  else if (opcao === "limpar") { filtros.de = ""; filtros.ate = ""; }
}
