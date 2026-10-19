// Configurações · Importação de boletos e senha de administrador (área restrita).
import { api } from "../../api.js";
import { estado } from "../../estado.js";
import { icone } from "../../icons.js";
import { abrirModal, confirmar, copiar, dataHoraBR, esc, mensagemErro, pedirTexto, toast } from "../../ui.js";
import { bloquearAdmin, pedirSenhaAdmin } from "../../admin.js";
import { tela } from "./tela.js";
import { atualizarBackup } from "./backup.js";
import { atualizarEntrada } from "./entrada.js";
import { atualizarUsuarios } from "./usuarios.js";

export function htmlImportacao(a) {
  if (!a) {
    // Nunca esconder a opção: se o servidor ainda não tem a função (versão antiga aberta), explica o que fazer
    return `<div class="card col-inteira" id="card-admin">
      <div class="rede-topo">
        <h3>${icone("planilha", 18)} Importar boletos de outro sistema</h3>
        <span class="chip aviso">${icone("escudo", 12)} Indisponível</span>
      </div>
      <div class="alerta aviso">${icone("alerta", 16)}<span>Não foi possível carregar esta função. Feche o Fin Pro
        (botão direito no ícone perto do relógio → <strong>Sair</strong>) e abra de novo para ativar a importação.</span></div>
    </div>`;
  }
  let corpo;
  if (!a.senha_definida) {
    corpo = a.local
      ? `<p style="color:var(--texto-2)">Traga boletos exportados de outro sistema (Excel, CSV ou TXT) para a planilha. Por segurança, esta função
          fica protegida por uma <strong>senha de administrador</strong>: crie a sua abaixo. Só quem souber a senha consegue importar.</p>
        <form class="rede-senha" data-admin="criar">
          <input type="password" class="input" name="senha" placeholder="Senha de administrador (mínimo 6 caracteres)" autocomplete="new-password" minlength="6" required>
          <input type="password" class="input" name="confirmacao" placeholder="Repita a senha" autocomplete="new-password" minlength="6" required>
          <button class="btn btn-primario" type="submit">${icone("escudo", 16)} Criar senha</button>
        </form>
        <p class="sutil">Use uma senha diferente da senha de acesso pelo celular e não a compartilhe.</p>`
      : `<div class="alerta info">${icone("info", 16)}<span>A senha de administrador precisa ser criada no computador onde o sistema está instalado.</span></div>`;
  } else if (a.autorizado) {
    corpo = `<div class="alerta info">${icone("check", 16)}<span>Área liberada neste aparelho. Ela é bloqueada sozinha após ${a.minutos_sessao} minutos sem uso.</span></div>
      <div class="linha-botoes">
        <a class="btn btn-primario" href="#/importar">${icone("upload", 16)} Abrir importação</a>
        <button class="btn" type="button" data-admin="bloquear">${icone("escudo", 16)} Bloquear agora</button>
        ${a.local ? `<button class="btn btn-fantasma" type="button" data-admin="trocar">Trocar senha</button>` : ""}
      </div>`;
  } else {
    corpo = `<p style="color:var(--texto-2)">Traga boletos exportados de outro sistema (Excel, CSV ou TXT) para a planilha.
        Área restrita: só abre com a senha de administrador.</p>
      <div class="linha-botoes">
        <button class="btn btn-primario" type="button" data-admin="abrir">${icone("escudo", 16)} Digitar a senha e abrir</button>
        ${a.local ? `<button class="btn btn-fantasma" type="button" data-admin="trocar">Trocar senha</button>` : ""}
      </div>`;
  }
  return `<div class="card col-inteira" id="card-admin">
    <div class="rede-topo">
      <h3>${icone("planilha", 18)} Importar boletos de outro sistema</h3>
      <span class="chip ${a.senha_definida ? "ok" : "aviso"}">${icone("escudo", 12)} ${a.senha_definida ? "Protegido por senha" : "Senha não criada"}</span>
    </div>
    ${corpo}
    ${a.local && a.senha_definida ? `<details class="rede-ajuda"><summary>Esqueceu a senha de administrador?</summary>
      <p class="sutil">Neste computador, feche o Fin Pro, apague o arquivo <code>dados\\admin.json</code> e abra de novo:
        será possível criar uma nova senha. Boletos, Pix e a planilha não são afetados.</p></details>` : ""}
  </div>`;
}

export async function atualizarAdmin() {
  const dados = await api.get("/api/admin");
  const card = tela.raiz?.querySelector("#card-admin");
  if (card) card.outerHTML = htmlImportacao(dados);
  await Promise.all([atualizarUsuarios(dados), atualizarBackup(), atualizarEntrada(null, dados)]);
}

export async function acaoAdmin(acao) {
  if (acao === "abrir") {
    if (await pedirSenhaAdmin({ descricao: "Digite a senha de administrador para abrir a importação de boletos." })) location.hash = "#/importar";
  } else if (acao === "bloquear") {
    await bloquearAdmin();
    await atualizarAdmin();
    toast("Área de administrador bloqueada.", "info");
  } else if (acao === "trocar") {
    trocarSenhaAdmin();
  }
}

export async function criarSenhaAdmin(formulario) {
  const dados = Object.fromEntries(new FormData(formulario).entries());
  if (dados.senha !== dados.confirmacao) {
    toast("As duas senhas não são iguais.", "erro");
    return;
  }
  const botao = formulario.querySelector("button");
  botao.disabled = true;
  try {
    await api.post("/api/admin/senha", dados);
    await atualizarAdmin();
    toast("Senha de administrador criada. Só quem souber a senha consegue importar boletos.", "ok", { duracao: 6000 });
  } catch (erro) {
    botao.disabled = false;
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
  }
}

export function trocarSenhaAdmin() {
  const { el, fechar } = abrirModal({
    titulo: "Trocar senha de administrador",
    corpo: `<form class="grade-campos" data-trocar-admin autocomplete="off">
      <div class="campo col-2"><label for="adm-atual">Senha atual</label>
        <input id="adm-atual" type="password" class="input" name="senha_atual" autocomplete="current-password" autofocus></div>
      <div class="campo"><label for="adm-nova">Nova senha</label>
        <input id="adm-nova" type="password" class="input" name="senha" autocomplete="new-password" minlength="6"></div>
      <div class="campo"><label for="adm-conf">Repita a nova senha</label>
        <input id="adm-conf" type="password" class="input" name="confirmacao" autocomplete="new-password" minlength="6"></div>
    </form>`,
    rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
             <button class="btn btn-primario" data-salvar>${icone("check", 16)} Trocar senha</button>`,
  });
  const formulario = el.querySelector("[data-trocar-admin]");
  const salvar = async (e) => {
    e?.preventDefault();
    const dados = Object.fromEntries(new FormData(formulario).entries());
    if (dados.senha !== dados.confirmacao) {
      toast("As duas senhas novas não são iguais.", "erro");
      return;
    }
    const botao = el.querySelector("[data-salvar]");
    botao.disabled = true;
    try {
      await api.post("/api/admin/senha", dados);
      fechar(true);
      await atualizarAdmin();
      toast("Senha de administrador trocada. Os outros aparelhos que estavam liberados foram bloqueados.", "ok", { duracao: 6000 });
    } catch (erro) {
      botao.disabled = false;
      toast(mensagemErro(erro), "erro", { duracao: 6000 });
    }
  };
  formulario.addEventListener("submit", salvar);
  el.querySelector("[data-salvar]").addEventListener("click", salvar);
}
