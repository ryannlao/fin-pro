// Tela: Configurações, em abas — Geral (com a versão do sistema) · Usuários e acesso · Backup e recebimento · Saúde do sistema.
// Cada cartão fica no seu próprio arquivo nesta pasta; aqui só se monta a aba escolhida.
import { api } from "../../api.js";
import { estado, ehAdministrador } from "../../estado.js";
import { icone } from "../../icons.js";
import { esc } from "../../ui.js";
import { htmlAplicativo } from "./aplicativo.js";
import { htmlBackup } from "./backup.js";
import { htmlEntrada } from "./entrada.js";
import { aoAlterar, aoClicar, aoEnviar } from "./eventos.js";
import { htmlImportacao } from "./importacao.js";
import { htmlRede } from "./rede.js";
import { aoClicarSaude, htmlSaude, iniciarSaude, pararSaude } from "./saude.js";
import { tela } from "./tela.js";
import { htmlUsuarios } from "./usuarios.js";
import { htmlVersao } from "./versao.js";

const ABAS = [
  ["geral", "aplicativo", "Geral"],
  ["usuarios", "usuarios", "Usuários e acesso"],
  ["integracoes", "nuvem", "Backup e recebimento"],
  ["saude", "ok", "Saúde do sistema"],
];

async function aoClicarTela(e) {
  if (await aoClicarSaude(e)) return;
  aoClicar(e);
}

export async function montar(el, params) {
  tela.raiz = el;
  const aba = ABAS.some(([chave]) => chave === params?.get("aba")) ? params.get("aba") : "geral";
  let s = estado.status;
  if (!s) {
    try { s = estado.status = await api.get("/api/status"); } catch { s = null; }
  }
  if (!s) {
    el.innerHTML = `<div class="card vazio"><div class="vazio-icone">${icone("alerta", 26)}</div><h3>Servidor indisponível</h3></div>`;
    return;
  }
  el.innerHTML = `
    <nav class="alternar-modo sub-abas config-abas" role="tablist" aria-label="Seções de Configurações">
      ${ABAS.map(([chave, ic, rotulo]) => `<a role="tab" href="#/config?aba=${chave}" class="${chave === aba ? "ativo" : ""}"
        aria-selected="${chave === aba}">${icone(ic, 15)} ${rotulo}</a>`).join("")}
    </nav>
    <section class="config-grade" id="config-conteudo"><div class="card esqueleto col-inteira" style="height:240px"></div></section>`;
  el.addEventListener("click", aoClicarTela);
  el.addEventListener("change", aoAlterar);
  el.addEventListener("submit", aoEnviar);

  const conteudo = el.querySelector("#config-conteudo");
  const html = await (aba === "usuarios" ? htmlAbaUsuarios() : aba === "integracoes" ? htmlAbaIntegracoes()
    : aba === "saude" ? htmlAbaSaude() : htmlAbaGeral(s));
  if (tela.raiz !== el) return;
  conteudo.innerHTML = html;
  if (aba === "saude") iniciarSaude();
}

export function desmontar() {
  pararSaude();
  tela.raiz?.removeEventListener("click", aoClicarTela);
  tela.raiz?.removeEventListener("change", aoAlterar);
  tela.raiz?.removeEventListener("submit", aoEnviar);
  tela.raiz = null;
}

// ------------------------------------------------------------------ abas

async function htmlAbaUsuarios() {
  const [administracao, rede] = await Promise.all([api.get("/api/admin").catch(() => null), api.get("/api/rede").catch(() => null)]);
  const lista = (administracao?.autorizado || ehAdministrador()) ? await api.get("/api/usuarios").catch(() => null) : null;
  return `${htmlImportacao(administracao)}${htmlUsuarios(administracao, lista)}${rede ? htmlRede(rede) : ""}`;
}

async function htmlAbaIntegracoes() {
  const [administracao, backup, caixa] = await Promise.all([
    api.get("/api/admin").catch(() => null), api.get("/api/backup").catch(() => null), api.get("/api/entrada").catch(() => null)]);
  return `${htmlBackup(backup, administracao)}${htmlEntrada(caixa, administracao)}`;
}

async function htmlAbaSaude() {
  return htmlSaude(await api.get("/api/saude").catch(() => null));
}

async function htmlAbaGeral(s) {
  const [estadoAcesso, aplicativo, saude, versao] = await Promise.all([
    api.get("/api/acesso/estado").catch(() => null), api.get("/api/app").catch(() => null), api.get("/api/saude").catch(() => null),
    api.get("/api/versao").catch(() => null)]);
  const banco = saude?.itens.find((i) => i.chave === "banco")?.detalhes || {};
  const avisoRede = estadoAcesso?.rede_sem_senha
    ? `<div class="alerta aviso col-inteira">${icone("escudo", 18)}<div><strong>Acesso pela rede sem senha.</strong>
        Qualquer aparelho no mesmo Wi-Fi consegue abrir o sistema. Defina <code>LEITOR_SENHA_ACESSO=sua-senha</code> no arquivo
        <code>.env</code> e reinicie.</div></div>`
    : "";
  const avisoSaude = saude && saude.situacao !== "ok"
    ? `<a class="alerta ${saude.situacao === "erro" ? "erro" : "aviso"} col-inteira alerta-link" href="#/config?aba=saude">${icone("alerta", 18)}
        <span><strong>${saude.situacao === "erro" ? "Há problemas" : "Há pontos de atenção"} no sistema.</strong>
        Veja em Saúde do sistema.</span></a>`
    : "";
  const recurso = (ok, titulo, descricao, rotuloOk = "Ativo", rotuloOff = "Desativado") => `
    <li><span class="kpi-icone" style="background:${ok ? "var(--ok-suave)" : "var(--superficie-3)"};color:${ok ? "var(--ok)" : "var(--texto-3)"}">${icone(ok ? "ok" : "erro", 18)}</span>
      <div class="info"><strong>${titulo}</strong><p>${descricao}</p></div>
      <span class="chip ${ok ? "ok" : ""}">${ok ? rotuloOk : rotuloOff}</span></li>`;
  const local = aplicativo?.local !== false;

  return `
    ${avisoSaude}${avisoRede}
    ${aplicativo?.local ? htmlAplicativo(aplicativo) : ""}
    ${htmlVersao(versao)}

    <div class="card">
      <h3>${icone("planilha", 18)} Banco de dados e planilha</h3>
      <p style="color:var(--texto-2)">Os boletos e Pix ficam num banco de dados no computador, e a planilha Excel é atualizada
        sozinha poucos segundos depois de cada alteração${banco.boletos !== undefined ? ` (${banco.boletos} boletos e ${banco.pix} Pix)` : ""}.</p>
      <div class="caminho mono">${esc(s.planilha)}</div>
      ${local ? `<div class="linha-botoes">
        <button class="btn btn-primario" data-acao="abrir">${icone("externo", 16)} Abrir planilha</button>
        <button class="btn" data-acao="pasta">${icone("pasta", 16)} Abrir pasta de dados</button>
        <a class="btn" href="/api/exportar?formato=planilha">${icone("download", 16)} Baixar cópia</a>
      </div>` : ""}
      <ul class="lista-info">
        <li>Abas <strong>Boletos</strong>, <strong>Pix</strong>, <strong>Centros de Custo</strong>, <strong>Resumo</strong> (fórmulas) e
          <strong>Histórico</strong> (quem fez cada alteração).</li>
        <li><strong>Pode deixar a planilha aberta no Excel:</strong> os lançamentos são gravados na hora, e a planilha é atualizada quando o arquivo for fechado.</li>
        <li><strong>Editou no Excel e salvou?</strong> As mudanças em boletos já lançados (status, centro de custo, observações…) voltam
          para o sistema sozinhas. Para lançar ou excluir, use o sistema.</li>
        <li>Cópia de segurança diária em <code>dados\\backups</code> (últimos 30 dias). Para proteger contra perda do computador,
          ligue o <a href="#/config?aba=integracoes">backup fora do computador</a>.</li>
      </ul>
    </div>

    <div class="card">
      <h3>${icone("scan", 18)} Recursos de leitura</h3>
      <ul class="recursos">
        ${recurso(true, "Código de barras", "Decodifica o código ITF de 44 dígitos em PDFs e fotos, com valor e vencimento exatos.")}
        ${recurso(true, "Texto de PDF", "Lê a linha digitável e os campos diretamente da camada de texto de boletos digitais.")}
        ${recurso(s.ocr, "OCR local", `Reconhece o texto de fotos e PDFs escaneados, sem enviar nada para a internet.${s.ocr_modelo ? ` Modelo: <code>${esc(s.ocr_modelo)}</code>.` : ""} Fotos de papel são recortadas e endireitadas automaticamente.`, "Ativo", "Indisponível")}
        ${recurso(s.heic, "Fotos do iPhone (HEIC)", "Aceita fotos no formato HEIC/HEIF.", "Suportado", "Não suportado")}
        ${recurso(true, "Comprovantes de pagamento", "Reconhece o comprovante, acha o boleto ou Pix e dá baixa com valor pago, juros e desconto.")}
        ${recurso(s.ia, "IA (Claude)", s.ia
          ? `Botão "Analisar com IA" disponível para fotos difíceis. Modelo: <code>${esc(s.ia_modelo)}</code>${s.ia_automatica ? " · automática quando a confiança é baixa" : ""}.`
          : `Opcional. Para ativar: copie <code>.env.example</code> para <code>.env</code>, preencha <code>ANTHROPIC_API_KEY</code> e reinicie o sistema.`)}
      </ul>
    </div>

    <div class="card col-inteira">
      <h3>${icone("info", 18)} Como a leitura funciona</h3>
      <ol class="passos">
        <li><strong>Envio</strong><p>PDF ou foto enviado pela tela, arrastado, colado (Ctrl+V), fotografado pelo celular, por e-mail ou pelo Telegram.</p></li>
        <li><strong>Código de barras</strong><p>O código ITF é decodificado; a imagem é girada se estiver de lado.</p></li>
        <li><strong>Texto e OCR</strong><p>Rótulos como Beneficiário e Nº do Documento são localizados pela posição na página.</p></li>
        <li><strong>Validação</strong><p>Dígitos verificadores FEBRABAN conferidos; valor e vencimento comparados com o impresso.</p></li>
        <li><strong>Revisão e lançamento</strong><p>Você confere, ajusta e lança. Duplicados são bloqueados.</p></li>
      </ol>
    </div>

    <div class="card">
      <h3>${icone("teclado", 18)} Atalhos</h3>
      <table class="atalhos">
        <tr><td><kbd>Ctrl</kbd> + <kbd>V</kbd></td><td>Colar imagem ou linha digitável</td></tr>
        <tr><td>Arrastar arquivos</td><td>Ler boletos (ou comprovantes) a partir de qualquer tela</td></tr>
        <tr><td><kbd>/</kbd></td><td>Buscar na lista de boletos</td></tr>
        <tr><td>Colar um Pix Copia e Cola</td><td>Abre a aba Pix já preenchida</td></tr>
        <tr><td><kbd>Alt</kbd> + <kbd>1</kbd>…<kbd>7</kbd></td><td>Painel, Ler, Boletos, Pix, Gastos, Notificações, Configurações</td></tr>
        <tr><td><kbd>Esc</kbd></td><td>Fechar janelas</td></tr>
      </table>
    </div>

    <div class="card">
      <h3>${icone("escudo", 18)} Sobre</h3>
      <p style="color:var(--texto-2)">Fin Pro versão ${esc(s.versao)}. Roda no seu computador: banco de dados, planilha e arquivos
        ficam na pasta <code>dados</code>. Somente a análise com IA, quando você a aciona, envia o arquivo para a API da Anthropic.</p>
      <p class="sutil">Suporta boletos bancários (47 dígitos) e de arrecadação — contas de consumo e tributos (48 dígitos) —,
        incluindo o novo ciclo do fator de vencimento iniciado em 22/02/2025.</p>
    </div>`;
}
