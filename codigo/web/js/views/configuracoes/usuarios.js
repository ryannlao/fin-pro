// Configurações · Usuários do escritório (área restrita).
import { api } from "../../api.js";
import { ehAdministrador } from "../../estado.js";
import { icone } from "../../icons.js";
import { abrirModal, confirmar, dataHoraBR, esc, mensagemErro, pedirTexto, toast } from "../../ui.js";
import { pedirSenhaAdmin } from "../../admin.js";
import { tela } from "./tela.js";
import { atualizarAdmin } from "./importacao.js";

let permissoesConhecidas = [];

export function htmlUsuarios(a, dados) {
  const topo = (chip) => `<div class="rede-topo"><h3>${icone("usuarios", 18)} Usuários do escritório</h3>${chip}</div>`;
  const explicacao = `<p style="color:var(--texto-2)">Cada pessoa entra com o próprio usuário e senha, e só enxerga o que o
    <strong>administrador</strong> liberar. O sistema registra quem lançou, pagou, anexou comprovante ou alterou cada
    boleto e Pix (aba <strong>Histórico</strong> da planilha e botão ${icone("relogio", 13)} nas listas).</p>`;
  if (!dados) {
    return `<div class="card col-inteira" id="card-usuarios">${topo(`<span class="chip">${icone("escudo", 12)} Área restrita</span>`)}
      ${explicacao}
      ${a?.senha_definida
        ? `<div class="linha-botoes"><button class="btn btn-primario" type="button" data-usuarios="abrir">${icone("escudo", 16)} Digitar a senha de administrador</button></div>
           <p class="sutil">Quem já é administrador entra com o próprio usuário e senha e não precisa desta senha.</p>`
        : `<div class="alerta info">${icone("info", 16)}<span>Primeiro crie a senha de administrador no cartão <strong>Importar boletos</strong>: com ela você cadastra o primeiro usuário administrador.</span></div>`}
    </div>`;
  }
  permissoesConhecidas = dados.permissoes || [];
  const linhas = dados.usuarios.map((u) => `<tr data-usuario="${esc(u.id)}" data-nome="${esc(u.nome)}" class="${u.ativo ? "" : "usuario-inativo"}">
      <td data-rotulo="Pessoa"><strong>${esc(u.nome)}</strong><div class="sutil mono">${esc(u.login)}</div></td>
      <td data-rotulo="Perfil">${u.perfil === "administrador"
        ? `<span class="chip ok">${icone("escudo", 12)} Administrador</span>`
        : `<span class="chip">Comum</span>`}</td>
      <td data-rotulo="Pode usar" class="celula-permissoes">${u.perfil === "administrador"
        ? `<span class="sutil">Tudo, inclusive cadastrar usuários</span>`
        : (u.permissoes.length
          ? u.permissoes.map((p) => `<span class="chip">${esc(rotuloCurto(p))}</span>`).join(" ")
          : `<span class="sutil">Só consultar</span>`)}</td>
      <td data-rotulo="Último acesso" class="sutil">${u.ultimo_acesso ? dataHoraBR(u.ultimo_acesso) : "Nunca entrou"}${u.aparelhos ? ` · ${u.aparelhos} aparelho(s)` : ""}</td>
      <td class="col-acoes">
        <button class="btn-icone" data-usuarios="permissoes" title="Perfil e permissões">${icone("escudo", 15)}</button>
        <button class="btn-icone" data-usuarios="renomear" title="Mudar o nome">${icone("editar", 15)}</button>
        <button class="btn-icone" data-usuarios="senha" title="Definir nova senha">${icone("chave", 15)}</button>
        <button class="btn-icone" data-usuarios="${u.ativo ? "desativar" : "ativar"}" title="${u.ativo ? "Desativar (a pessoa não consegue mais entrar)" : "Ativar de novo"}">${icone(u.ativo ? "x" : "check", 15)}</button>
        <button class="btn-icone perigo" data-usuarios="excluir" title="Excluir usuário">${icone("lixeira", 15)}</button>
      </td></tr>`).join("");
  return `<div class="card col-inteira" id="card-usuarios">
    ${topo(dados.em_uso ? `<span class="chip ok">${icone("check", 12)} Login por pessoa ligado</span>` : `<span class="chip">Nenhum usuário ativo</span>`)}
    ${explicacao}
    ${dados.usuarios.length && !dados.tem_administrador
      ? `<div class="alerta aviso">${icone("alerta", 16)}<span>Ninguém é <strong>administrador</strong> ainda. Abra o
          ${icone("escudo", 13)} de uma pessoa (a sua) e marque <strong>Administrador</strong>: assim você entra com o seu
          usuário e senha e gerencia tudo sem a senha de administrador.</span></div>` : ""}
    ${dados.usuarios.length ? `<div class="tabela-wrap"><table class="tabela tabela-usuarios"><thead><tr><th>Pessoa</th><th>Perfil</th><th>Pode usar</th><th>Último acesso</th><th class="col-acoes">Ações</th></tr></thead>
      <tbody>${linhas}</tbody></table></div>`
      : `<div class="alerta info">${icone("info", 16)}<span>Enquanto não houver usuários, o sistema funciona como hoje: aparelhos da rede usam a senha única de acesso.
        Ao cadastrar o primeiro usuário, <strong>os aparelhos da rede passam a pedir usuário e senha</strong>.</span></div>`}
    <form class="usuario-novo" data-usuarios-form autocomplete="off">
      <strong>${icone("mais", 15)} Novo usuário</strong>
      <input class="input" name="nome" placeholder="Nome (ex.: Maria Souza)" maxlength="60" required>
      <input class="input" name="login" placeholder="Login (ex.: maria)" maxlength="40" autocapitalize="none" spellcheck="false">
      <input class="input" type="password" name="senha" placeholder="Senha inicial (mín. 6)" minlength="6" autocomplete="new-password" required>
      <select class="input" name="perfil" aria-label="Perfil">
        <option value="comum">Comum (permissões escolhidas)</option>
        <option value="administrador">Administrador (pode tudo)</option>
      </select>
      <button class="btn btn-primario" type="submit">${icone("check", 16)} Cadastrar</button>
    </form>
    ${a?.local ? `<label class="opcao-app">
      <span class="interruptor"><input type="checkbox" data-usuarios-config="exigir_login_no_computador" ${dados.exigir_login_no_computador ? "checked" : ""} ${dados.em_uso ? "" : "disabled"}><span></span></span>
      <span><strong>Pedir login também neste computador</strong><small>Desligado: quem usa este computador aparece como "Computador principal" no histórico.
        Ligado: todos precisam entrar com o próprio usuário, inclusive aqui.</small></span></label>
    <label class="opcao-app">
      <span class="interruptor"><input type="checkbox" data-usuarios-config="pedir_login_ao_abrir" ${dados.pedir_login_ao_abrir ? "checked" : ""} ${dados.em_uso ? "" : "disabled"}><span></span></span>
      <span><strong>Pedir usuário e senha toda vez que o aplicativo abrir</strong><small>Ao abrir o Fin Pro, quem
        estava conectado neste computador precisa entrar de novo. Celulares e outros aparelhos continuam conectados.</small></span></label>` : ""}
    <p class="sutil">Passe a cada pessoa o login e a senha inicial. Ela pode trocar a senha no menu lateral, em "Trocar senha".</p>
  </div>`;
}

function rotuloCurto(chave) {
  const curtos = { lancar: "Lançar", pagar: "Dar baixa", editar: "Editar/excluir", gastos: "Gastos",
    empresas: "Empresas", caixa: "Caixa", diesel: "Diesel", notificacoes: "Avisos", config: "Configurações" };
  return curtos[chave] || chave;
}

export async function atualizarUsuarios(admin) {
  const card = tela.raiz?.querySelector("#card-usuarios");
  if (!card) return;
  const estadoAdm = admin || await api.get("/api/admin").catch(() => null);
  const dados = (estadoAdm?.autorizado || ehAdministrador()) ? await api.get("/api/usuarios").catch(() => null) : null;
  card.outerHTML = htmlUsuarios(estadoAdm, dados);
}

/** Janela com o perfil (administrador ou comum) e o que a pessoa pode fazer. */
function abrirPermissoes(id, nome, usuario) {
  const marcada = (chave) => (usuario.permissoes || []).includes(chave);
  const { el, fechar } = abrirModal({
    titulo: `Permissões de ${nome}`,
    corpo: `<form data-form-permissoes>
      <div class="campo"><label for="p-perfil">Perfil</label>
        <select id="p-perfil" name="perfil" class="input">
          <option value="comum" ${usuario.perfil === "comum" ? "selected" : ""}>Comum — só o que estiver marcado abaixo</option>
          <option value="administrador" ${usuario.perfil === "administrador" ? "selected" : ""}>Administrador — pode tudo, inclusive cadastrar usuários</option>
        </select></div>
      <div class="lista-permissoes" ${usuario.perfil === "administrador" ? "hidden" : ""}>
        <p class="sutil">Marque o que esta pessoa pode fazer. Ver os boletos, os Pix e o painel é liberado para todo mundo.</p>
        ${permissoesConhecidas.map((p) => `<label class="opcao-permissao">
          <input type="checkbox" name="permissoes" value="${esc(p.chave)}" ${marcada(p.chave) ? "checked" : ""}>
          <span>${esc(p.rotulo)}</span></label>`).join("")}
      </div>
    </form>`,
    rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
             <button class="btn btn-primario" data-salvar>${icone("check", 16)} Salvar</button>`,
  });
  const lista = el.querySelector(".lista-permissoes");
  el.querySelector("#p-perfil").addEventListener("change", (e) => { lista.hidden = e.target.value === "administrador"; });
  el.querySelector("[data-salvar]").addEventListener("click", async () => {
    const formulario = el.querySelector("[data-form-permissoes]");
    const dados = {
      perfil: formulario.perfil.value,
      permissoes: [...formulario.querySelectorAll("[name=permissoes]:checked")].map((c) => c.value),
    };
    try {
      await api.put(`/api/usuarios/${id}`, dados);
      toast(`Permissões de ${nome} salvas.`, "ok");
      fechar(true);
      await atualizarUsuarios();
    } catch (erro) {
      toast(mensagemErro(erro), "erro", { duracao: 7000 });
    }
  });
}

export async function acaoUsuario(botao) {
  const acao = botao.dataset.usuarios;
  if (acao === "abrir") {
    if (await pedirSenhaAdmin({ descricao: "Digite a senha de administrador para cadastrar e gerenciar os usuários." })) await atualizarAdmin();
    return;
  }
  const linha = botao.closest("[data-usuario]");
  if (!linha) return;
  const { usuario: id, nome } = linha.dataset;
  if (acao === "permissoes") {
    const lista = await api.get("/api/usuarios").catch(() => null);
    const usuario = lista?.usuarios.find((u) => u.id === id);
    if (usuario) abrirPermissoes(id, nome, usuario);
    return;
  }
  try {
    if (acao === "renomear") {
      const novo = await pedirTexto({ titulo: "Nome do usuário", rotulo: "Nome", valor: nome, maximo: 60 });
      if (novo === null) return;
      await api.put(`/api/usuarios/${id}`, { nome: novo });
    } else if (acao === "senha") {
      const senha = await pedirTexto({ titulo: `Nova senha para ${nome}`, rotulo: "Nova senha (mínimo 6 caracteres)",
        descricao: "A pessoa será desconectada dos aparelhos e precisará entrar com a nova senha.", textoConfirmar: "Definir senha" });
      if (senha === null) return;
      await api.put(`/api/usuarios/${id}`, { senha });
      toast(`Senha de ${nome} alterada.`, "ok");
    } else if (acao === "desativar" || acao === "ativar") {
      await api.put(`/api/usuarios/${id}`, { ativo: acao === "ativar" });
      toast(acao === "ativar" ? `${nome} pode entrar de novo.` : `${nome} foi desativado(a) e desconectado(a).`, "info");
    } else if (acao === "excluir") {
      if (!(await confirmar({ titulo: "Excluir usuário", mensagem: `Excluir ${nome}? O histórico do que essa pessoa fez continua na planilha.`, textoConfirmar: "Excluir", perigo: true }))) return;
      await api.del(`/api/usuarios/${id}`);
    }
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 7000 });
  }
  await atualizarUsuarios();
}

export async function criarUsuario(formulario) {
  const botao = formulario.querySelector("button");
  botao.disabled = true;
  try {
    const { criado } = await api.post("/api/usuarios", Object.fromEntries(new FormData(formulario).entries()));
    toast(`Usuário criado: login "${criado.login}". Passe o login e a senha para ${criado.nome}.`, "ok", { duracao: 8000 });
    await atualizarUsuarios();
  } catch (erro) {
    botao.disabled = false;
    if (erro.status === 403) await atualizarUsuarios();
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
  }
}
