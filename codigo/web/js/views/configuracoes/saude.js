// Configurações · Saúde do sistema: o que roda sozinho está funcionando? (atualiza a cada 30 segundos)
import { api } from "../../api.js";
import { icone } from "../../icons.js";
import { dataHoraBR, esc, mensagemErro, tamanhoArquivo, toast } from "../../ui.js";
import { tela } from "./tela.js";

const SITUACOES = {
  ok: ["ok", "check", "Funcionando"],
  aviso: ["aviso", "alerta", "Atenção"],
  erro: ["erro", "erro", "Problema"],
  desligado: ["", "ligar", "Desligado"],
};
const RESUMO_GERAL = {
  ok: "Tudo funcionando.",
  aviso: "Funcionando, mas há pontos de atenção.",
  erro: "Há problemas que precisam de atenção.",
};
const ATALHOS = {
  banco: `<button class="btn btn-sm" data-saude="planilha">${icone("planilha", 14)} Atualizar planilha agora</button>`,
  backup: `<a class="btn btn-sm" href="#/config?aba=integracoes">${icone("nuvem", 14)} Configurar backup</a>`,
  entrada: `<a class="btn btn-sm" href="#/config?aba=integracoes">${icone("caixa", 14)} Ver recebimento</a>`,
  notificacoes: `<a class="btn btn-sm" href="#/notificacoes">${icone("sino", 14)} Ver lembretes</a>`,
  disco: `<button class="btn btn-sm" data-saude="logs">${icone("lixeira", 14)} Limpar logs</button>`,
  rede: `<a class="btn btn-sm" href="#/config?aba=usuarios">${icone("wifi", 14)} Ver acesso</a>`,
  empresas: `<a class="btn btn-sm" href="#/empresas?aba=bot">${icone("carteira", 14)} Ver bot de notas</a>`,
  caixa: `<a class="btn btn-sm" href="#/caixa?aba=bot">${icone("caixa", 14)} Ver bot do caixa</a>`,
  diesel: `<a class="btn btn-sm" href="#/diesel?aba=bot">${icone("diesel", 14)} Ver bot do diesel</a>`,
};

let temporizador = null;

export function htmlSaude(d) {
  if (!d) {
    return `<div class="card col-inteira" id="card-saude"><div class="alerta erro">${icone("erro", 16)}<span>Não foi possível carregar o diagnóstico.</span></div></div>`;
  }
  const [classe, iconeGeral] = SITUACOES[d.situacao] || SITUACOES.aviso;
  const detalheBanco = d.itens.find((i) => i.chave === "banco")?.detalhes || {};
  return `<div class="card col-inteira" id="card-saude">
    <div class="saude-topo ${classe}">
      <span class="saude-icone">${icone(iconeGeral, 26)}</span>
      <div><h3>${RESUMO_GERAL[d.situacao] || "Diagnóstico"}</h3>
        <p class="sutil">Versão ${esc(d.versao)} · em execução há ${esc(d.em_execucao_ha)} · verificado em ${dataHoraBR(d.atualizado_em)}</p></div>
      <span class="espaco"></span>
      <button class="btn btn-sm" data-saude="atualizar">${icone("atualizar", 14)} Verificar de novo</button>
    </div>
    <ul class="saude-lista">${d.itens.map((i) => {
      const [c, ic, rotulo] = SITUACOES[i.situacao] || SITUACOES.aviso;
      return `<li class="${c}" data-chave="${esc(i.chave)}">
        <span class="saude-marca">${icone(ic, 16)}</span>
        <div class="saude-info"><strong>${esc(i.titulo)}</strong><span>${esc(i.resumo)}</span></div>
        <span class="chip ${c}">${rotulo}</span>
        <div class="saude-acao">${ATALHOS[i.chave] || ""}</div>
      </li>`;
    }).join("")}</ul>
    ${detalheBanco.banco ? `<p class="sutil saude-rodape">Banco de dados: <code>${esc(detalheBanco.banco)}</code> (${tamanhoArquivo(detalheBanco.tamanho_banco)})
      · planilha: <code>${esc(detalheBanco.planilha)}</code></p>` : ""}
  </div>`;
}

export async function carregarSaude() {
  const card = tela.raiz?.querySelector("#card-saude");
  if (!card) return;
  const dados = await api.get("/api/saude").catch(() => null);
  const atual = tela.raiz?.querySelector("#card-saude");
  if (atual) atual.outerHTML = htmlSaude(dados);
}

export function iniciarSaude() {
  pararSaude();
  temporizador = setInterval(carregarSaude, 30 * 1000);
}

export function pararSaude() {
  clearInterval(temporizador);
  temporizador = null;
}

export async function aoClicarSaude(e) {
  const botao = e.target.closest("[data-saude]");
  if (!botao) return false;
  botao.disabled = true;
  try {
    if (botao.dataset.saude === "planilha") {
      await api.post("/api/saude/atualizar-planilha");
      toast("Planilha Excel atualizada com os dados do sistema.", "ok");
    } else if (botao.dataset.saude === "logs") {
      const r = await api.post("/api/saude/limpar-logs");
      toast(`Logs limpos: ${tamanhoArquivo(r.liberados)} liberados.`, "ok");
    }
    await carregarSaude();
  } catch (erro) {
    botao.disabled = false;
    toast(mensagemErro(erro), "erro", { duracao: 7000 });
  }
  return true;
}
