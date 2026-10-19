// Configurações · Aplicativo no computador.
import { api } from "../../api.js";
import { estado } from "../../estado.js";
import { icone } from "../../icons.js";
import { abrirModal, confirmar, copiar, dataHoraBR, esc, mensagemErro, pedirTexto, toast } from "../../ui.js";
import { bloquearAdmin, pedirSenhaAdmin } from "../../admin.js";
import { tela } from "./tela.js";

export function opcaoAplicativo(chave, ativo, desabilitado, titulo, descricao) {
  return `<label class="opcao-app ${desabilitado ? "desabilitada" : ""}">
    <span class="interruptor"><input type="checkbox" data-app="${chave}" ${ativo ? "checked" : ""} ${desabilitado ? "disabled" : ""}><span></span></span>
    <span><strong>${titulo}</strong><small>${descricao}</small></span></label>`;
}

export function htmlAplicativo(a) {
  const inicio = a.inicializacao || {};
  const p = a.preferencias || {};
  const atalhoCriado = a.atalhos?.criados?.length > 0;
  return `<div class="card col-inteira" id="card-app">
    <div class="rede-topo">
      <h3>${icone("aplicativo", 18)} Aplicativo no computador</h3>
      <span class="chip ${a.modo_app ? "ok" : "info"}">${a.modo_app ? "Aberto como aplicativo" : "Aberto no navegador"}</span>
    </div>
    ${a.modo_app ? "" : `<div class="alerta info">${icone("info", 16)}<span>Você está usando o sistema pelo navegador. Para usar a janela própria do aplicativo,
      feche o Fin Pro e abra pelo atalho <strong>Fin Pro</strong> (crie abaixo) ou pelo <code>iniciar.bat</code>.</span></div>`}
    <div class="app-opcoes">
      ${opcaoAplicativo("inicializacao", inicio.ativo, !inicio.disponivel, "Iniciar junto com o Windows",
        "Abre sozinho quando o computador é ligado, para os lembretes de vencimento nunca deixarem de chegar.")}
      ${opcaoAplicativo("minimizado", p.minimizado_ao_iniciar, false, "Iniciar minimizado na bandeja",
        "Ao ligar o computador, fica só o ícone perto do relógio, sem abrir a janela.")}
      ${opcaoAplicativo("bandeja", p.fechar_para_bandeja, false, "Fechar para a bandeja",
        "O X esconde a janela e o sistema continua avisando. Para encerrar: botão direito no ícone → Sair.")}
    </div>
    <div class="linha-botoes" style="align-items:center">
      <button class="btn" data-app="atalhos" ${a.atalhos?.disponivel ? "" : "disabled"}>${icone("externo", 16)} ${atalhoCriado ? "Recriar atalhos" : "Criar atalhos"} na Área de Trabalho e no Menu Iniciar</button>
      <span class="sutil">${atalhoCriado ? `${icone("check", 14)} Atalho "Fin Pro" criado` : "Com o atalho, o sistema abre como um programa comum."}</span>
    </div>
  </div>`;
}

export function atualizarAplicativo(dados) {
  const card = tela.raiz?.querySelector("#card-app");
  if (card && dados) card.outerHTML = htmlAplicativo(dados);
}

export async function alterarAplicativo(chave) {
  const ativo = chave.checked;
  chave.disabled = true;
  try {
    let dados;
    if (chave.dataset.app === "inicializacao") {
      await api.post("/api/sistema/inicializacao", { ativo });
      dados = await api.get("/api/app");
      toast(ativo ? "Pronto: o Fin Pro vai abrir sozinho quando o computador ligar." : "O Fin Pro não vai mais iniciar com o Windows.", ativo ? "ok" : "info", { duracao: 5000 });
    } else {
      const alteracao = chave.dataset.app === "minimizado" ? { minimizado_ao_iniciar: ativo } : { fechar_para_bandeja: ativo };
      dados = await api.put("/api/app/preferencias", alteracao);
    }
    atualizarAplicativo(dados);
  } catch (erro) {
    chave.checked = !ativo;
    chave.disabled = false;
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
  }
}
