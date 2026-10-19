// Configurações · Backup total fora do computador: dados, comprovantes, configurações, código-fonte e versões.
import { api } from "../../api.js";
import { estado } from "../../estado.js";
import { icone } from "../../icons.js";
import { abrirModal, confirmar, copiar, dataHoraBR, esc, mensagemErro, pedirTexto, toast } from "../../ui.js";
import { bloquearAdmin, pedirSenhaAdmin } from "../../admin.js";
import { tela } from "./tela.js";
import { atualizarAdmin } from "./importacao.js";

export const SITUACAO_BACKUP = {
  ok: ["ok", "Backup em dia"],
  aguardando: ["info", "Aguardando o primeiro backup"],
  atrasado: ["erro", "Backup atrasado"],
  erro: ["erro", "Último backup falhou"],
  desligado: ["aviso", "Desligado"],
};

export function htmlBackup(b, adm) {
  if (!b) return "";
  const [classe, rotulo] = SITUACAO_BACKUP[b.situacao] || SITUACAO_BACKUP.desligado;
  const ultimo = b.ultimo || {};
  const podeConfigurar = b.local && adm?.autorizado;
  const falha = (b.situacao === "erro" || b.situacao === "atrasado") && ultimo.ok === false
    ? `<div class="alerta erro">${icone("erro", 16)}<span><strong>O backup não foi feito:</strong> ${esc(ultimo.erro || "erro desconhecido")}.
        Se for pen drive ou HD externo, confira se está conectado.</span></div>`
    : b.situacao === "atrasado"
      ? `<div class="alerta erro">${icone("alerta", 16)}<span>Faz ${b.dias_sem_backup ?? "vários"} dia(s) sem backup. Confira se a pasta ainda existe e clique em <strong>Fazer backup agora</strong>.</span></div>`
      : "";
  const resumo = b.ultimo_sucesso
    ? `<p class="sutil">Último backup: <strong>${dataHoraBR(b.ultimo_sucesso)}</strong>${ultimo.ok && ultimo.tamanho_legivel ? ` · ${esc(ultimo.tamanho_legivel)} em ${ultimo.itens} arquivo(s)` : ""}${b.destino ? `<br>Em <code>${esc(b.destino)}</code>` : ""}</p>
       ${htmlConteudo(b)}${htmlConferencia(b)}${htmlPacotes(b)}`
    : b.ativo ? `<p class="sutil">O primeiro backup é feito em alguns minutos.</p>` : "";
  const botoesBackup = b.ativo ? `
          <button class="btn" type="button" data-backup="agora" title="Copia agora o que mudou desde o último backup">${icone("atualizar", 16)} Fazer backup agora</button>
          <button class="btn" type="button" data-backup="pacote" title="Atualiza o backup e guarda tudo num único arquivo .zip (código, versões, bancos, comprovantes e configurações)">${icone("download", 16)} Gerar pacote completo (.zip)</button>
          <button class="btn" type="button" data-backup="verificar" title="Confere se os bancos abrem, se nada falta e se cada arquivo está igual ao que foi copiado">${icone("escudo", 16)} Verificar backup</button>` : "";

  let corpo;
  if (!b.local) {
    corpo = `<p style="color:var(--texto-2)">A configuração do backup é feita no computador onde o sistema está instalado.</p>`;
  } else if (!podeConfigurar) {
    corpo = `${b.ativo ? "" : `<div class="alerta aviso">${icone("alerta", 16)}<span><strong>Recomendado:</strong> hoje as cópias ficam só neste computador.
        Se ele quebrar ou for roubado, os boletos e comprovantes se perdem. Ligue o backup para uma pasta do OneDrive, Google Drive ou um pen drive.</span></div>`}
      <div class="linha-botoes">
        ${adm?.senha_definida
          ? `<button class="btn ${b.ativo ? "" : "btn-primario"}" type="button" data-backup="admin">${icone("escudo", 16)} ${b.ativo ? "Alterar configuração" : "Configurar backup"}</button>`
          : `<span class="sutil">Para configurar, crie antes a senha de administrador (cartão Importar boletos).</span>`}
        ${botoesBackup}
      </div>`;
  } else {
    const sugestoes = (b.sugestoes || []).map((s) => `<button type="button" class="chip-filtro" data-backup-sugestao="${esc(s.pasta)}" title="${esc(s.pasta)}">${icone("nuvem", 13)} ${esc(s.nome)}</button>`).join("");
    corpo = `<form class="backup-form" data-backup-form autocomplete="off">
        <label class="campo backup-pasta"><span class="sutil">Pasta do backup</span>
          <div class="input-grupo">
            <input class="input mono" name="pasta" value="${esc(b.pasta || "")}" placeholder="Ex.: C:\\Users\\voce\\OneDrive" required>
            <button class="btn" type="button" data-backup="escolher">${icone("pasta", 16)} Escolher…</button>
          </div></label>
        ${sugestoes ? `<div class="backup-sugestoes"><span class="sutil">Encontradas neste computador:</span>${sugestoes}</div>` : ""}
        <div class="backup-opcoes">
          <label class="campo"><span class="sutil">Horário do backup diário</span><input class="input" type="time" name="horario" value="${esc(b.horario || "12:30")}"></label>
          <label class="campo"><span class="sutil">Guardar cópias da planilha por</span>
            <select class="input" name="manter_dias">${[15, 30, 60, 90, 180, 365].map((d) => `<option value="${d}" ${Number(b.manter_dias) === d ? "selected" : ""}>${d} dias</option>`).join("")}</select></label>
          <label class="campo"><span class="sutil">Pacote completo num arquivo .zip</span>
            <select class="input" name="pacote">${[["semanal", "Toda semana"], ["mensal", "Todo mês"], ["nunca", "Não gerar sozinho"]].map(([v, r]) => `<option value="${v}" ${(b.pacote || "semanal") === v ? "selected" : ""}>${r}</option>`).join("")}</select></label>
          <label class="campo"><span class="sutil">Guardar os últimos</span>
            <select class="input" name="manter_pacotes">${[1, 2, 4, 8, 12].map((n) => `<option value="${n}" ${Number(b.manter_pacotes ?? 4) === n ? "selected" : ""}>${n} pacote${n > 1 ? "s" : ""}</option>`).join("")}</select></label>
          <label class="opcao-app"><span class="interruptor"><input type="checkbox" name="codigo" ${b.codigo !== false ? "checked" : ""}><span></span></span>
            <span><strong>Levar também o código-fonte e o histórico de versões</strong><small>Com eles o backup é total: dá para reerguer o sistema inteiro em outro computador.</small></span></label>
          <label class="opcao-app"><span class="interruptor"><input type="checkbox" name="ativo" ${b.ativo ? "checked" : ""}><span></span></span>
            <span><strong>Backup automático ligado</strong><small>Todo dia, no horário escolhido (ou assim que o computador ligar, se passou da hora).</small></span></label>
        </div>
        <div class="linha-botoes">
          <button class="btn btn-primario" type="submit">${icone("check", 16)} Salvar</button>
          ${botoesBackup}
        </div>
      </form>
      <details class="rede-ajuda"><summary>Qual pasta escolher e como restaurar?</summary>
        <ul class="lista-info">
          <li><strong>OneDrive ou Google Drive (recomendado):</strong> escolha a pasta deles no computador; o programa da nuvem envia as cópias para a sua conta sozinho.</li>
          <li><strong>Pen drive ou HD externo:</strong> precisa ficar conectado. Se for desconectado, o sistema avisa que o backup atrasou.</li>
          <li>Dentro da pasta escolhida é criada a pasta <code>Leitor de Boletos - Backup</code> com <strong>tudo</strong>: os bancos de dados e as planilhas (uma cópia por dia), os PDFs, fotos e comprovantes, todas as configurações, o <strong>código-fonte</strong> do sistema e o <strong>histórico de versões</strong>.</li>
          <li>O <strong>pacote completo (.zip)</strong> junta tudo isso num arquivo só, bom para guardar num pen drive. Fica em <code>pacotes</code>, dentro da pasta do backup.</li>
          <li><strong>Para restaurar em outro computador:</strong> instale o Python, abra a pasta do backup e dê dois cliques em <code>RESTAURAR.bat</code>. O passo a passo está no <code>LEIA-ME.txt</code> da mesma pasta.</li>
          <li>A pasta do backup guarda os tokens dos bots e as senhas de e-mail: mantenha-a num lugar de confiança.</li>
        </ul></details>`;
  }
  return `<div class="card col-inteira" id="card-backup">
    <div class="rede-topo"><h3>${icone("nuvem", 18)} Backup total fora do computador</h3><span class="chip ${classe}">${esc(rotulo)}</span></div>
    ${falha}${resumo}${corpo}
  </div>`;
}

/** O que o último backup levou: cada parte com um "ok" ou o motivo de não ter ido. */
function htmlConteudo(b) {
  const u = b.ultimo || {};
  if (!u.ok) return "";
  const parte = (ok, texto) => `<li class="${ok ? "ok" : "falta"}">${icone(ok ? "check" : "alerta", 14)}<span>${texto}</span></li>`;
  return `<ul class="backup-partes">
    ${parte(true, `<strong>Bancos de dados e planilhas</strong> · uma cópia por dia (${b.manter_dias} dias)`)}
    ${parte(true, `<strong>Boletos, comprovantes e fotos</strong> · ${u.arquivos_total ?? 0} arquivo(s)`)}
    ${parte(true, `<strong>Configurações</strong> · ${u.configuracoes ?? 0} arquivo(s) (lembretes, usuários, bots, preços)`)}
    ${parte(b.com_codigo && u.codigo_total > 0, b.com_codigo ? `<strong>Código-fonte do sistema</strong> · ${u.codigo_total ?? 0} arquivo(s)` : "<strong>Código-fonte</strong> · não incluído (ligue na configuração)")}
    ${b.com_codigo ? parte(u.historico_de_versoes, u.historico_de_versoes ? "<strong>Histórico de versões</strong> · todas as versões guardadas" : "<strong>Histórico de versões</strong> · não foi possível guardar (o git está instalado?)") : ""}
  </ul>`;
}

function htmlConferencia(b) {
  const v = b.verificacao;
  if (!v) return "";
  if (v.ok) {
    return `<p class="sutil backup-conferido">${icone("escudo", 14)} Conferido em <strong>${dataHoraBR(v.quando)}</strong>${v.completa ? " · conferência completa, arquivo por arquivo" : " · conferência rápida (o botão Verificar backup confere arquivo por arquivo)"}</p>`;
  }
  return `<div class="alerta erro">${icone("alerta", 16)}<div><strong>O backup não passou na conferência de ${dataHoraBR(v.quando)}:</strong>
    <ul class="lista-info">${(v.itens || []).filter((i) => !i.ok).map((i) => `<li><strong>${esc(i.nome)}</strong>: ${esc(i.detalhe)}</li>`).join("")}</ul>
    Clique em <strong>Fazer backup agora</strong> para recopiar e depois em <strong>Verificar backup</strong>.</div></div>`;
}

function htmlPacotes(b) {
  const pacotes = b.pacotes || [];
  if (!pacotes.length) {
    return b.pacote === "nunca" ? "" : `<p class="sutil">${icone("download", 14)} Pacote completo (.zip): ainda não gerado — sai sozinho ${b.pacote === "mensal" ? "todo mês" : "toda semana"}, ou pelo botão abaixo.</p>`;
  }
  return `<p class="sutil">${icone("download", 14)} Pacotes completos guardados (em <code>pacotes</code>, dentro da pasta do backup):</p>
    <ul class="backup-pacotes">${pacotes.map((p) => `<li><span class="mono">${esc(p.arquivo)}</span><span class="sutil">${esc(p.tamanho_legivel)} · ${dataHoraBR(p.quando)}</span></li>`).join("")}</ul>`;
}

export async function atualizarBackup(dados) {
  const card = tela.raiz?.querySelector("#card-backup");
  if (!card) return;
  const [b, adm] = await Promise.all([dados ? Promise.resolve(dados) : api.get("/api/backup"), api.get("/api/admin").catch(() => null)]);
  card.outerHTML = htmlBackup(b, adm);
  carregarStatusLateral();
}

export function carregarStatusLateral() {
  window.dispatchEvent(new Event("status:atualizar"));
}

export async function acaoBackup(botao) {
  const acao = botao.dataset.backup;
  if (acao === "admin") {
    if (await pedirSenhaAdmin({ descricao: "Digite a senha de administrador para configurar o backup." })) await atualizarAdmin();
  } else if (acao === "agora") {
    botao.disabled = true;
    botao.innerHTML = `${icone("atualizar", 16)} Fazendo backup…`;
    try {
      const dados = await api.post("/api/backup/agora");
      const u = dados.ultimo || {};
      toast(`Backup concluído: ${u.arquivos_copiados ?? 0} arquivo(s) novo(s)${u.codigo_copiados ? ` e ${u.codigo_copiados} do código` : ""}. Total guardado: ${u.tamanho_legivel || "—"}.`, "ok", { duracao: 7000 });
      await atualizarBackup(dados);
    } catch (erro) {
      toast(mensagemErro(erro), "erro", { duracao: 8000 });
      await atualizarBackup();
    }
  } else if (acao === "pacote" || acao === "verificar") {
    const original = botao.innerHTML;
    botao.disabled = true;
    botao.innerHTML = `${icone("atualizar", 16)} ${acao === "pacote" ? "Gerando o pacote…" : "Conferindo…"}`;
    try {
      const dados = await api.post(`/api/backup/${acao}`);
      if (acao === "pacote") {
        const p = dados.ultimo_pacote || {};
        toast(`Pacote completo gerado: ${p.arquivo || ""} (${p.tamanho_legivel || ""}).`, "ok", { duracao: 8000 });
      } else if (dados.verificado) {
        toast("Backup conferido: está tudo lá e nada foi alterado.", "ok", { duracao: 7000 });
      } else {
        toast("O backup não passou na conferência. Veja o aviso no cartão.", "erro", { duracao: 9000 });
      }
      await atualizarBackup(dados);
    } catch (erro) {
      botao.disabled = false;
      botao.innerHTML = original;
      toast(mensagemErro(erro), "erro", { duracao: 8000 });
    }
  } else if (acao === "escolher") {
    botao.disabled = true;
    try {
      const { pasta } = await api.post("/api/backup/escolher-pasta");
      if (pasta) tela.raiz.querySelector("[data-backup-form] [name=pasta]").value = pasta.replaceAll("/", "\\");
    } finally {
      botao.disabled = false;
    }
  }
}

export async function salvarBackup(formulario) {
  const dados = new FormData(formulario);
  const botao = formulario.querySelector("button[type=submit]");
  botao.disabled = true;
  try {
    const resposta = await api.put("/api/backup/config", {
      pasta: dados.get("pasta"), horario: dados.get("horario"), manter_dias: Number(dados.get("manter_dias")), ativo: dados.get("ativo") === "on",
      codigo: dados.get("codigo") === "on", pacote: dados.get("pacote") || "semanal", manter_pacotes: Number(dados.get("manter_pacotes") || 4),
    });
    toast(resposta.ativo ? "Backup ligado. O primeiro backup é feito em alguns minutos (ou clique em Fazer backup agora)." : "Configuração do backup salva.", "ok", { duracao: 7000 });
    await atualizarBackup(resposta);
  } catch (erro) {
    botao.disabled = false;
    toast(mensagemErro(erro), "erro", { duracao: 7000 });
  }
}
