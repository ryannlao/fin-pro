// Configurações · Acesso pelo celular (rede Wi-Fi).
import { api } from "../../api.js";
import { estado } from "../../estado.js";
import { icone } from "../../icons.js";
import { abrirModal, confirmar, copiar, dataHoraBR, esc, mensagemErro, pedirTexto, toast } from "../../ui.js";
import { bloquearAdmin, pedirSenhaAdmin } from "../../admin.js";
import { tela } from "./tela.js";

export function textoSituacao(r) {
  if (r.via_env) return "Liberado pelo arquivo .env (LEITOR_HOST=0.0.0.0).";
  if (!(r.senha_definida || r.senha_via_env)) return "Defina a senha acima para poder liberar.";
  if (r.ativo && r.rodando) return `Liberado. Abra no celular: ${r.urls[0] || ""}`;
  if (r.ativo) return "Ligado, mas o acesso não pôde ser aberto (veja o aviso abaixo).";
  return "Desligado. Use a chave no topo deste cartão para liberar.";
}

export function htmlRede(r) {
  if (!r.local) {
    return `<div class="card col-inteira rede-card" id="card-rede">
      <h3>${icone("celular", 18)} Você está usando o Fin Pro pela rede</h3>
      <p style="color:var(--texto-2)">Este aparelho entrou com a senha de acesso. Para desconectá-lo, toque em <em>Sair deste aparelho</em>.</p>
      <div class="linha-botoes"><button class="btn" data-acao="sair">${icone("sair", 16)} Sair deste aparelho</button></div>
    </div>`;
  }
  const senhaOk = r.senha_definida || r.senha_via_env;
  const liberado = r.ativo && r.rodando && r.urls.length;
  return `<div class="card col-inteira rede-card" id="card-rede">
    <div class="rede-topo">
      <h3>${icone("wifi", 18)} Acesso pelo celular (rede Wi-Fi)</h3>
      ${r.via_env
        ? `<span class="chip info">Liberado pelo .env</span>`
        : `<label class="interruptor" title="${senhaOk ? "Liberar acesso pela rede" : "Defina uma senha primeiro"}">
            <input type="checkbox" data-rede="ativo" ${r.ativo ? "checked" : ""} ${senhaOk ? "" : "disabled"} aria-label="Liberar acesso pela rede"><span></span></label>`}
    </div>
    <div class="rede-grade">
      <div class="rede-info">
        <p style="color:var(--texto-2)">Use o sistema no celular ou em outro computador conectado ao <strong>mesmo Wi-Fi</strong> — por exemplo,
          para fotografar boletos de papel direto do celular. No celular, a leitura, a revisão e os lançamentos funcionam igual.</p>

        <div class="rede-passo ${senhaOk ? "ok" : ""}">
          <span class="rede-numero">${senhaOk ? icone("check", 14) : "1"}</span>
          <div>
            <strong>Senha de acesso</strong>
            ${r.senha_via_env
              ? `<p class="sutil">Definida no arquivo .env (LEITOR_SENHA_ACESSO).</p>`
              : `<p class="sutil">${r.senha_definida
                  ? "Senha definida. Trocar a senha desconecta os aparelhos que já entraram."
                  : "Obrigatória: será pedida uma vez em cada aparelho (vale por 30 dias)."}</p>
                <form class="rede-senha" data-rede="senha">
                  <input type="password" class="input" name="senha" placeholder="${r.senha_definida ? "Nova senha" : "Senha"} (mínimo 6 caracteres)" autocomplete="new-password" minlength="6" required>
                  <input type="password" class="input" name="confirmacao" placeholder="Repita a senha" autocomplete="new-password" minlength="6" required>
                  <button class="btn" type="submit">${r.senha_definida ? "Trocar senha" : "Definir senha"}</button>
                </form>`}
          </div>
        </div>

        <div class="rede-passo ${liberado ? "ok" : ""}">
          <span class="rede-numero">${liberado ? icone("check", 14) : "2"}</span>
          <div><strong>Liberar o acesso</strong><p class="sutil">${esc(textoSituacao(r))}</p></div>
        </div>

        ${r.erro ? `<div class="alerta erro">${icone("erro", 16)}<span>${esc(r.erro)}</span></div>` : ""}

        <details class="rede-ajuda">
          <summary>O celular não conecta?</summary>
          <ul class="lista-info">
            <li>Confirme que o celular está no <strong>mesmo Wi-Fi</strong> do computador, e não usando dados móveis.</li>
            <li>Na primeira vez que liberar, o Windows pergunta se o Python pode se comunicar na rede: marque
              <strong>Redes privadas</strong> e clique em <strong>Permitir acesso</strong>.</li>
            <li>Se a rede do computador estiver como <strong>Pública</strong>, mude para <strong>Privada</strong> em
              Configurações do Windows → Rede e Internet → propriedades do Wi-Fi.</li>
            <li>Redes de visitantes ("guest") costumam bloquear a comunicação entre aparelhos.</li>
            <li>Se o roteador reiniciar e o endereço mudar, o sistema reabre o acesso sozinho em até 1 minuto — leia o QR code de novo.</li>
            <li>O computador precisa estar ligado com o Fin Pro aberto (ou iniciando junto com o Windows).</li>
          </ul>
        </details>
      </div>

      ${liberado ? `<div class="rede-qr">
        <img src="/api/rede/qrcode.svg?url=${encodeURIComponent(r.urls[0])}&t=${Date.now()}" alt="QR code para abrir o sistema no celular" width="196" height="196">
        <div class="rede-url mono">${esc(r.urls[0])}</div>
        <button class="btn btn-sm" type="button" data-rede="copiar" data-url="${esc(r.urls[0])}">${icone("copiar", 14)} Copiar endereço</button>
        <p class="sutil">Aponte a câmera do celular para o código e toque no link.</p>
        ${r.urls.length > 1 ? `<details class="rede-outros"><summary class="sutil">Outros endereços deste computador</summary>
          ${r.urls.slice(1).map((u) => `<div class="mono sutil">${esc(u)}</div>`).join("")}</details>` : ""}
      </div>` : ""}
    </div>

    ${r.acessos?.length ? `<div class="rede-acessos">
      <strong>${icone("celular", 15)} Aparelhos que acessaram desde que o sistema foi aberto</strong>
      <table class="atalhos">${r.acessos.map((a) => `<tr><td>${esc(a.aparelho)}</td><td class="mono">${esc(a.ip)}</td><td>${dataHoraBR(a.ultimo)}</td></tr>`).join("")}</table>
    </div>` : ""}
  </div>`;
}

export async function atualizarRede(rede) {
  const dados = rede || await api.get("/api/rede");
  const card = tela.raiz?.querySelector("#card-rede");
  if (card) card.outerHTML = htmlRede(dados);
}
