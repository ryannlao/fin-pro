// Configurações · Cliques, alterações e formulários da tela de Configurações.
import { api } from "../../api.js";
import { estado } from "../../estado.js";
import { icone } from "../../icons.js";
import { abrirModal, confirmar, copiar, dataHoraBR, esc, mensagemErro, pedirTexto, toast } from "../../ui.js";
import { bloquearAdmin, pedirSenhaAdmin } from "../../admin.js";
import { tela } from "./tela.js";
import { alterarAplicativo, atualizarAplicativo } from "./aplicativo.js";
import { acaoBackup, salvarBackup } from "./backup.js";
import { acaoEntrada, atualizarEntrada, salvarEmail } from "./entrada.js";
import { acaoAdmin, criarSenhaAdmin } from "./importacao.js";
import { atualizarRede } from "./rede.js";
import { acaoUsuario, atualizarUsuarios, criarUsuario } from "./usuarios.js";

export async function aoClicar(e) {
  const alvo = e.target.closest("[data-acao], [data-rede='copiar'], button[data-app='atalhos'], button[data-admin], button[data-usuarios], button[data-backup], [data-backup-sugestao], button[data-entrada]");
  if (!alvo) return;
  try {
    if (alvo.dataset.entrada) {
      await acaoEntrada(alvo);
    } else if (alvo.dataset.backupSugestao) {
      tela.raiz.querySelector("[data-backup-form] [name=pasta]").value = alvo.dataset.backupSugestao;
    } else if (alvo.dataset.backup) {
      await acaoBackup(alvo);
    } else if (alvo.dataset.usuarios) {
      await acaoUsuario(alvo);
    } else if (alvo.dataset.admin) {
      await acaoAdmin(alvo.dataset.admin);
    } else if (alvo.dataset.app === "atalhos") {
      alvo.disabled = true;
      try {
        atualizarAplicativo(await api.post("/api/app/atalhos"));
        toast('Atalho "Fin Pro" criado na Área de Trabalho e no Menu Iniciar.', "ok", { duracao: 6000 });
      } finally {
        alvo.disabled = false;
      }
    } else if (alvo.dataset.rede === "copiar") {
      copiar(alvo.dataset.url, "Endereço copiado");
    } else if (alvo.dataset.acao === "abrir") {
      await api.post("/api/planilha/abrir");
      toast("Abrindo a planilha…", "info");
    } else if (alvo.dataset.acao === "pasta") {
      await api.post("/api/planilha/abrir-pasta");
    } else if (alvo.dataset.acao === "sair") {
      window.dispatchEvent(new Event("acesso:sair"));
    }
  } catch (erro) {
    toast(mensagemErro(erro), "erro");
  }
}

export async function aoAlterar(e) {
  if (e.target.matches("[data-entrada-form] [name=provedor]")) {
    const servidor = e.target.closest("form").querySelector("[name=servidor]");
    if (e.target.value) servidor.value = e.target.value;
    servidor.focus();
    return;
  }
  if (e.target.matches("[data-entrada-telegram]")) {
    try {
      await api.put("/api/entrada/config", { telegram: { ativo: e.target.checked } });
      toast(e.target.checked ? "Pronto: boletos enviados ao bot do Telegram vão aparecer em Ler boletos." : "O bot não recebe mais boletos.", "info", { duracao: 6000 });
      await atualizarEntrada();
    } catch (erro) {
      e.target.checked = !e.target.checked;
      toast(mensagemErro(erro), "erro");
    }
    return;
  }
  if (e.target.matches("[data-usuarios-config]")) {
    const campo = e.target.dataset.usuariosConfig || "exigir_login_no_computador";
    const ligado = e.target.checked;
    const avisos = {
      exigir_login_no_computador: ["Agora todos precisam entrar com o próprio usuário, inclusive neste computador.",
                                   "Este computador não pede mais login."],
      pedir_login_ao_abrir: ["Toda vez que o aplicativo abrir, será preciso entrar com usuário e senha neste computador.",
                             "O aplicativo não vai mais pedir login ao abrir."],
    };
    try {
      await api.put("/api/usuarios/config", { [campo]: ligado });
      toast(avisos[campo][ligado ? 0 : 1], "info", { duracao: 6000 });
      await atualizarUsuarios();  // ligar "ao abrir" liga junto o login neste computador
    } catch (erro) {
      e.target.checked = !ligado;
      toast(mensagemErro(erro), "erro");
    }
    return;
  }
  if (e.target.matches("[data-app]")) {
    alterarAplicativo(e.target);
    return;
  }
  if (!e.target.matches("[data-rede='ativo']")) return;
  const chave = e.target;
  const ativo = chave.checked;
  chave.disabled = true;
  try {
    const rede = await api.post("/api/rede/ativar", { ativo });
    await atualizarRede(rede);
    if (!ativo) toast("Acesso pela rede desligado.", "info");
    else if (rede.rodando) toast("Acesso pela rede liberado. Leia o QR code com o celular.", "ok", { duracao: 6000 });
    else toast(rede.erro || "Não foi possível abrir o acesso pela rede.", "erro", { duracao: 8000 });
  } catch (erro) {
    chave.checked = !ativo;
    chave.disabled = false;
    toast(mensagemErro(erro), "erro", { duracao: 7000 });
  }
}

export async function aoEnviar(e) {
  const formularioEmail = e.target.closest("[data-entrada-form='email']");
  if (formularioEmail) {
    e.preventDefault();
    salvarEmail(formularioEmail);
    return;
  }
  const formularioBackup = e.target.closest("[data-backup-form]");
  if (formularioBackup) {
    e.preventDefault();
    salvarBackup(formularioBackup);
    return;
  }
  const formularioUsuario = e.target.closest("[data-usuarios-form]");
  if (formularioUsuario) {
    e.preventDefault();
    criarUsuario(formularioUsuario);
    return;
  }
  const formularioAdmin = e.target.closest("[data-admin='criar']");
  if (formularioAdmin) {
    e.preventDefault();
    criarSenhaAdmin(formularioAdmin);
    return;
  }
  const formulario = e.target.closest("[data-rede='senha']");
  if (!formulario) return;
  e.preventDefault();
  const dados = Object.fromEntries(new FormData(formulario).entries());
  if (dados.senha !== dados.confirmacao) {
    toast("As duas senhas não são iguais.", "erro");
    return;
  }
  const botao = formulario.querySelector("button");
  botao.disabled = true;
  try {
    const rede = await api.post("/api/rede/senha", dados);
    await atualizarRede(rede);
    toast("Senha de acesso salva.", "ok");
  } catch (erro) {
    botao.disabled = false;
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
  }
}
