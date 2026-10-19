// Configurações · Receber boletos e comprovantes por e-mail e Telegram.
import { api } from "../../api.js";
import { estado } from "../../estado.js";
import { icone } from "../../icons.js";
import { abrirModal, confirmar, copiar, dataHoraBR, esc, mensagemErro, pedirTexto, toast } from "../../ui.js";
import { bloquearAdmin, pedirSenhaAdmin } from "../../admin.js";
import { tela } from "./tela.js";
import { atualizarAdmin } from "./importacao.js";

export const PROVEDORES_IMAP = [
  ["imap.gmail.com", "Gmail"], ["outlook.office365.com", "Outlook, Hotmail ou Microsoft 365"], ["imap.mail.yahoo.com", "Yahoo"],
  ["imap.uol.com.br", "UOL"], ["imap.terra.com.br", "Terra"], ["", "Outro (digite o servidor)"],
];

export function linhaVerificacao(c) {
  if (c.ultimo_erro) return `<div class="alerta erro">${icone("erro", 16)}<span>${esc(c.ultimo_erro)}</span></div>`;
  return c.ultima_verificacao ? `<p class="sutil">${icone("check", 13)} Última verificação: ${dataHoraBR(c.ultima_verificacao)}</p>` : "";
}

export function htmlEntrada(dados, adm) {
  if (!dados) return "";
  const { email: e, telegram: tg } = dados.config;
  const liberado = adm?.autorizado;
  const chip = e.ativo || tg.ativo
    ? `<span class="chip ok">${icone("check", 12)} ${[e.ativo ? "E-mail" : "", tg.ativo ? "Telegram" : ""].filter(Boolean).join(" e ")}</span>`
    : `<span class="chip">Desligado</span>`;
  const provedor = PROVEDORES_IMAP.some(([s]) => s && s === e.servidor) ? e.servidor : "";
  const bloqueado = liberado ? "" : "disabled";
  return `<div class="card col-inteira" id="card-entrada">
    <div class="rede-topo"><h3>${icone("caixa", 18)} Receber boletos por e-mail e Telegram</h3>${chip}</div>
    <p style="color:var(--texto-2)">Boletos que chegam por e-mail ou são enviados ao bot do Telegram são lidos sozinhos e aparecem em
      <a href="#/ler">Ler boletos</a> para alguém conferir e lançar. Nada é lançado sem conferência.
      ${dados.pendentes ? `<strong>${dados.pendentes} aguardando conferência.</strong>` : ""}</p>
    ${liberado ? "" : `<div class="linha-botoes"><button class="btn btn-primario" type="button" data-entrada="admin">${icone("escudo", 16)} Digitar a senha de administrador para configurar</button></div>`}
    <div class="entrada-grade">
      <form class="entrada-bloco" data-entrada-form="email" autocomplete="off">
        <div class="entrada-titulo"><strong>${icone("email", 16)} Caixa de e-mail</strong>
          <label class="interruptor" title="Ler boletos que chegam nesta caixa de e-mail"><input type="checkbox" name="ativo" ${e.ativo ? "checked" : ""} ${bloqueado}><span></span></label></div>
        <p class="sutil">Use de preferência um e-mail só para boletos (ex.: boletos@suaempresa.com.br) e peça aos fornecedores para enviar para ele.
          Os e-mails não são apagados nem marcados como lidos.</p>
        <div class="grade-campos">
          <div class="campo"><label>Provedor</label><select class="input" name="provedor" ${bloqueado}>
            ${PROVEDORES_IMAP.map(([s, n]) => `<option value="${s}" ${s === provedor ? "selected" : ""}>${n}</option>`).join("")}</select></div>
          <div class="campo"><label>Servidor IMAP</label><input class="input mono" name="servidor" value="${esc(e.servidor)}" placeholder="imap.seudominio.com.br" ${bloqueado}></div>
          <div class="campo"><label>E-mail</label><input class="input" name="usuario" value="${esc(e.usuario)}" placeholder="boletos@empresa.com.br" ${bloqueado}></div>
          <div class="campo"><label>Senha de app</label><input class="input" type="password" name="senha" value="${esc(e.senha)}" autocomplete="new-password" ${bloqueado}></div>
          <div class="campo"><label>Porta</label><input class="input" name="porta" inputmode="numeric" value="${esc(e.porta || 993)}" ${bloqueado}></div>
          <div class="campo"><label>Pasta</label><input class="input" name="pasta" value="${esc(e.pasta || "INBOX")}" ${bloqueado}></div>
          <div class="campo col-2"><label>Aceitar só destes remetentes (opcional)</label>
            <input class="input" name="remetentes" value="${esc(e.remetentes)}" placeholder="ex.: energisa.com.br, financeiro@fornecedor.com — vazio aceita todos" ${bloqueado}></div>
        </div>
        ${linhaVerificacao(e)}
        <details class="rede-ajuda"><summary>Gmail ou Outlook recusou a senha?</summary><ul class="lista-info">
          <li><strong>Gmail:</strong> ative a verificação em duas etapas na conta Google e crie uma <strong>senha de app</strong> (Conta Google → Segurança → Senhas de app). Use essa senha aqui.</li>
          <li><strong>Outlook/Hotmail:</strong> em Segurança da conta Microsoft, crie uma senha de app. Em contas de empresa (Microsoft 365), o administrador precisa permitir IMAP.</li>
          <li>A senha fica guardada só neste computador.</li></ul></details>
        ${liberado ? `<div class="linha-botoes">
          <button class="btn btn-primario" type="submit">${icone("check", 16)} Salvar</button>
          ${e.servidor ? `<button class="btn" type="button" data-entrada="verificar-email">${icone("atualizar", 16)} Verificar agora</button>` : ""}</div>` : ""}
      </form>
      <div class="entrada-bloco">
        <div class="entrada-titulo"><strong>${icone("telegram", 16)} Bot do Telegram</strong>
          <label class="interruptor" title="Receber boletos enviados ao bot"><input type="checkbox" data-entrada-telegram ${tg.ativo ? "checked" : ""} ${bloqueado}><span></span></label></div>
        <p class="sutil">As pessoas cadastradas em <a href="#/notificacoes">Notificações → Telegram</a> encaminham a foto ou o PDF do boleto para o bot.
          Ele responde com o que conseguiu ler, e o boleto aparece em Ler boletos. Arquivos de quem não está cadastrado são recusados.</p>
        ${linhaVerificacao(tg)}
        ${liberado && tg.ativo ? `<div class="linha-botoes"><button class="btn" type="button" data-entrada="verificar-telegram">${icone("atualizar", 16)} Verificar agora</button></div>` : ""}
      </div>
    </div>
  </div>`;
}

export async function atualizarEntrada(dados, adm) {
  const card = tela.raiz?.querySelector("#card-entrada");
  if (!card) return;
  const [caixa, estadoAdm] = await Promise.all([dados ? Promise.resolve(dados) : api.get("/api/entrada"),
    adm ? Promise.resolve(adm) : api.get("/api/admin").catch(() => null)]);
  card.outerHTML = htmlEntrada(caixa, estadoAdm);
}

export async function acaoEntrada(botao) {
  const acao = botao.dataset.entrada;
  if (acao === "admin") {
    if (await pedirSenhaAdmin({ descricao: "Digite a senha de administrador para configurar o recebimento de boletos." })) await atualizarAdmin();
    return;
  }
  botao.disabled = true;
  try {
    const canal = acao === "verificar-email" ? "email" : "telegram";
    const resultado = await api.post("/api/entrada/verificar", { canal });
    toast(resultado.recebidos ? `${resultado.recebidos} arquivo(s) novo(s) recebido(s). Confira em Ler boletos.` : "Verificado: nenhum boleto novo.",
      resultado.recebidos ? "ok" : "info", { duracao: 6000 });
    window.dispatchEvent(new CustomEvent("entrada:contagem", { detail: resultado.pendentes }));
    await atualizarEntrada(resultado);
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 9000 });
    await atualizarEntrada();
  }
}

export async function salvarEmail(formulario) {
  const d = Object.fromEntries(new FormData(formulario).entries());
  const botao = formulario.querySelector("button[type=submit]");
  botao.disabled = true;
  try {
    const caixa = await api.put("/api/entrada/config", { email: {
      ativo: d.ativo === "on", servidor: d.servidor, usuario: d.usuario, senha: d.senha, porta: Number(d.porta) || 993,
      pasta: d.pasta, remetentes: d.remetentes } });
    toast(caixa.email.ativo ? "E-mail configurado. Clique em Verificar agora para testar." : "Configuração do e-mail salva.", "ok", { duracao: 6000 });
    await atualizarEntrada();
  } catch (erro) {
    botao.disabled = false;
    toast(mensagemErro(erro), "erro", { duracao: 7000 });
  }
}
