(function () {
  "use strict";
  document.documentElement.lang = "pt-BR";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ------------------------------------------------------------ leitor de linha digitável (regras da FEBRABAN) */
  var BANCOS = { "001": "Banco do Brasil", "033": "Santander", "041": "Banrisul", "077": "Banco Inter", "104": "Caixa Econômica Federal", "237": "Bradesco", "260": "Nubank", "341": "Itaú Unibanco", "422": "Safra", "748": "Sicredi", "756": "Sicoob" };
  var SEGMENTOS = { "1": "Prefeituras", "2": "Saneamento", "3": "Energia elétrica e gás", "4": "Telecomunicações", "5": "Órgãos governamentais", "6": "Carnês e assemelhados", "7": "Multas de trânsito", "9": "Uso exclusivo do banco" };
  var DIA = 86400000;
  var BASE_ORIGINAL = Date.UTC(1997, 9, 7);
  var BASE_NOVO_CICLO = Date.UTC(2025, 1, 22) - 1000 * DIA;

  function mod10(n) {
    var soma = 0, peso = 2;
    for (var i = n.length - 1; i >= 0; i--) {
      var produto = Number(n.charAt(i)) * peso;
      soma += Math.floor(produto / 10) + (produto % 10);
      peso = peso === 2 ? 1 : 2;
    }
    return (10 - (soma % 10)) % 10;
  }
  function soma11(n) {
    var soma = 0, peso = 2;
    for (var i = n.length - 1; i >= 0; i--) {
      soma += Number(n.charAt(i)) * peso;
      peso = peso === 9 ? 2 : peso + 1;
    }
    return soma;
  }
  function mod11Bancario(n) { var dv = 11 - (soma11(n) % 11); return dv === 0 || dv === 10 || dv === 11 ? 1 : dv; }
  function mod11Arrecadacao(n) { var resto = soma11(n) % 11; return resto === 0 || resto === 1 ? 0 : 11 - resto; }

  function dataPorFator(fator, hoje) {
    if (fator < 1000) return null;
    var a = BASE_ORIGINAL + fator * DIA, b = BASE_NOVO_CICLO + fator * DIA;
    return Math.abs(a - hoje) <= Math.abs(b - hoje) ? a : b;
  }
  function dataBR(ms) {
    var d = new Date(ms);
    return ("0" + d.getUTCDate()).slice(-2) + "/" + ("0" + (d.getUTCMonth() + 1)).slice(-2) + "/" + d.getUTCFullYear();
  }
  function moeda(v) { return "R$ " + v.toFixed(2).replace(".", ",").replace(/\B(?=(\d{3})+(?!\d))/g, "."); }

  function analisarBancario(d) {
    var linha, barras, conf = [];
    if (d.length === 47) {
      linha = d;
      barras = d.slice(0, 4) + d.charAt(32) + d.slice(33, 47) + d.slice(4, 9) + d.slice(10, 20) + d.slice(21, 31);
      conf.push(["Campo 1", mod10(d.slice(0, 9)) === Number(d.charAt(9))]);
      conf.push(["Campo 2", mod10(d.slice(10, 20)) === Number(d.charAt(20))]);
      conf.push(["Campo 3", mod10(d.slice(21, 31)) === Number(d.charAt(31))]);
    } else {
      barras = d;
      var c1 = d.slice(0, 4) + d.slice(19, 24), c2 = d.slice(24, 34), c3 = d.slice(34, 44);
      linha = c1 + mod10(c1) + c2 + mod10(c2) + c3 + mod10(c3) + d.charAt(4) + d.slice(5, 19);
    }
    conf.push(["Dígito geral", mod11Bancario(barras.slice(0, 4) + barras.slice(5)) === Number(barras.charAt(4))]);
    var hoje = Date.UTC(new Date().getFullYear(), new Date().getMonth(), new Date().getDate());
    var vencimento = dataPorFator(Number(barras.slice(5, 9)), hoje);
    var valor = Number(barras.slice(9, 19)) / 100;
    var banco = barras.slice(0, 3);
    return {
      tipo: "Boleto bancário", rotuloQuem: "Banco", quem: banco + " · " + (BANCOS[banco] || "banco " + banco),
      vencimento: vencimento ? dataBR(vencimento) : "Sem vencimento no código",
      situacaoVenc: vencimento && vencimento < hoje ? "vencido" : "",
      valor: valor ? moeda(valor) : "Sem valor no código", barras: barras, digitos: d.length, conf: conf,
      linha: linha.slice(0, 5) + "." + linha.slice(5, 10) + " " + linha.slice(10, 15) + "." + linha.slice(15, 21) + " " + linha.slice(21, 26) + "." + linha.slice(26, 32) + " " + linha.charAt(32) + " " + linha.slice(33)
    };
  }

  function analisarArrecadacao(d) {
    var barras = "", conf = [], blocos = [], i;
    var id = d.charAt(2);
    var dv = function (n) { return id === "6" || id === "7" ? mod10(n) : mod11Arrecadacao(n); };
    var problemas = [];
    if ("6789".indexOf(id) < 0) { problemas.push("O 3º dígito deveria ser 6, 7, 8 ou 9"); id = "6"; }
    if (d.length === 48) {
      for (i = 0; i < 4; i++) {
        var bloco = d.slice(i * 12, i * 12 + 11);
        blocos.push(bloco + "-" + d.charAt(i * 12 + 11));
        barras += bloco;
        conf.push(["Bloco " + (i + 1), dv(bloco) === Number(d.charAt(i * 12 + 11))]);
      }
    } else {
      barras = d;
      for (i = 0; i < 4; i++) { var parte = d.slice(i * 11, i * 11 + 11); blocos.push(parte + "-" + dv(parte)); }
    }
    conf.push(["Dígito geral", dv(barras.slice(0, 3) + barras.slice(4)) === Number(barras.charAt(3))]);
    var valorReal = id === "6" || id === "8";
    var valor = Number(barras.slice(4, 15)) / 100;
    return {
      tipo: "Conta de consumo ou tributo", rotuloQuem: "Segmento", quem: SEGMENTOS[barras.charAt(1)] || "Segmento " + barras.charAt(1),
      vencimento: "Não vem no código", notaVenc: "o Fin Pro lê do texto da conta", situacaoVenc: "",
      valor: valorReal ? moeda(valor) : "Por referência", barras: barras, digitos: d.length, conf: conf,
      linha: blocos.join(" "), problemas: problemas
    };
  }

  function analisar(texto) {
    var d = String(texto || "").replace(/\D/g, "");
    if (!d) return { vazio: true };
    if (d.length === 47 && d.charAt(0) !== "8") return analisarBancario(d);
    if (d.length === 48 && d.charAt(0) === "8") return analisarArrecadacao(d);
    if (d.length === 44) return d.charAt(0) === "8" ? analisarArrecadacao(d) : analisarBancario(d);
    return { erro: "Foram lidos " + d.length + " dígitos. O esperado é 47 (boleto bancário), 48 (conta de consumo ou tributo) ou 44 (código de barras)." };
  }

  /* Código de barras no padrão intercalado 2 de 5 (o mesmo do boleto impresso). */
  var ITF = ["nnwwn", "wnnnw", "nwnnw", "wwnnn", "nnwnw", "wnwnn", "nwwnn", "nnnww", "wnnwn", "nwnwn"];
  function barrasSvg(digitos) {
    var x = 10, partes = [];
    var bar = function (largura, preto) { if (preto) partes.push('<rect x="' + x + '" y="0" width="' + largura + '" height="60"/>'); x += largura; };
    bar(1, true); bar(1, false); bar(1, true); bar(1, false);
    for (var i = 0; i + 1 < digitos.length; i += 2) {
      var a = ITF[Number(digitos.charAt(i))], b = ITF[Number(digitos.charAt(i + 1))];
      for (var j = 0; j < 5; j++) { bar(a.charAt(j) === "w" ? 3 : 1, true); bar(b.charAt(j) === "w" ? 3 : 1, false); }
    }
    bar(3, true); bar(1, false); bar(1, true);
    return '<svg viewBox="0 0 ' + (x + 10) + ' 60" preserveAspectRatio="none" role="img" aria-label="Código de barras gerado a partir da linha" fill="currentColor">' + partes.join("") + "</svg>";
  }

  function campo(rotulo, valor, classe, extra) {
    return '<div class="campo ' + (classe || "") + '"><dt>' + rotulo + "</dt><dd" + (extra && extra.dd ? ' class="' + extra.dd + '"' : "") + ">" + valor + (extra && extra.nota ? "<small>" + extra.nota + "</small>" : "") + "</dd></div>";
  }
  function mostrar(r) {
    var alvo = $("#resultado");
    if (!alvo) return;
    if (r.vazio) { alvo.innerHTML = '<p class="vazio">Cole uma linha digitável acima ou escolha um dos exemplos.</p>'; return; }
    if (r.erro) { alvo.innerHTML = '<dl class="campos">' + campo("Situação", "Não é uma linha completa", "c12", { dd: "ruim", nota: r.erro }) + "</dl>"; return; }
    var falhas = r.conf.filter(function (c) { return !c[1]; }).length + (r.problemas ? r.problemas.length : 0);
    var conferencia = r.conf.map(function (c) { return '<span class="' + (c[1] ? "" : "ruim") + '">' + c[0] + (c[1] ? " confere" : " não confere") + "</span>"; }).join("");
    var situacao = falhas
      ? campo("Situação", "Linha inválida", "", { dd: "ruim", nota: "o Fin Pro não deixaria lançar sem revisar" })
      : campo("Situação", "Linha válida", "", { dd: "bom" });
    alvo.innerHTML = '<dl class="campos">' + situacao + campo("Tipo", r.tipo) + campo(r.rotuloQuem, r.quem) +
      campo("Vencimento", r.vencimento, "", { nota: r.notaVenc || (r.situacaoVenc === "vencido" ? "já venceu: o sistema alertaria" : "") }) +
      campo("Valor", r.valor) + campo("Dígitos lidos", String(r.digitos)) + campo("Código de barras", r.barras, "c6", { dd: "mono" }) +
      campo("Linha formatada", r.linha, "c12", { dd: "mono" }) +
      '<div class="campo c12"><dt>Conferência dos dígitos verificadores</dt><dd class="conferencia">' + conferencia + "</dd></div></dl>" +
      (falhas ? "" : '<div class="barras">' + barrasSvg(r.barras) + "<p>Código de barras desenhado a partir da linha, no padrão intercalado 2 de 5 usado nos boletos.</p></div>");
  }

  var entrada = $("#linha");
  if (entrada) {
    var atualizar = function () { mostrar(analisar(entrada.value)); };
    entrada.addEventListener("input", atualizar);
    $$("[data-exemplo]").forEach(function (b) {
      b.addEventListener("click", function () { entrada.value = b.getAttribute("data-exemplo"); atualizar(); });
    });
    atualizar();
  }
  window.finproLeitor = { analisar: analisar };

  /* ------------------------------------------------------------ galerias e tela ampliada */
  $$("[data-galeria]").forEach(function (galeria) {
    var abas = $$('[role="tab"]', galeria), img = $("img", galeria), botao = $(".ampliar", galeria), legenda = $("figcaption", galeria);
    abas.forEach(function (aba) {
      aba.addEventListener("click", function () {
        abas.forEach(function (a) { a.setAttribute("aria-selected", a === aba ? "true" : "false"); });
        img.src = aba.getAttribute("data-img");
        img.alt = aba.getAttribute("data-alt") || "";
        if (botao) { botao.setAttribute("data-ampliar", aba.getAttribute("data-img")); botao.setAttribute("data-legenda", aba.getAttribute("data-legenda") || ""); }
        if (legenda) legenda.textContent = aba.getAttribute("data-legenda") || "";
      });
    });
  });
  var dialogo = $("#ampliada");
  if (dialogo && typeof dialogo.showModal === "function") {
    document.addEventListener("click", function (evento) {
      var botao = evento.target.closest ? evento.target.closest(".ampliar") : null;
      if (!botao) return;
      var imagem = $("img", botao);
      $("#ampliada-img").src = botao.getAttribute("data-ampliar");
      $("#ampliada-img").alt = imagem ? imagem.alt : "";
      $("#ampliada-legenda").textContent = botao.getAttribute("data-legenda") || "";
      dialogo.showModal();
    });
    dialogo.addEventListener("click", function (evento) { if (evento.target === dialogo) dialogo.close(); });
  }

  /* ------------------------------------------------------------ índice: abrir no celular, rolar e marcar a seção atual */
  var trilho = $("#trilho"), fundo = $("#fundo-indice"), abre = $("#abre-indice");
  function indice(aberto) {
    if (!trilho) return;
    trilho.classList.toggle("aberto", aberto);
    if (fundo) fundo.hidden = !aberto;
    if (abre) abre.setAttribute("aria-expanded", aberto ? "true" : "false");
  }
  if (abre) abre.addEventListener("click", function () { indice(!trilho.classList.contains("aberto")); });
  if (fundo) fundo.addEventListener("click", function () { indice(false); });
  var fecha = $("#fecha-indice");
  if (fecha) fecha.addEventListener("click", function () { indice(false); });
  document.addEventListener("keydown", function (evento) { if (evento.key === "Escape") indice(false); });

  var suave = !(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  document.addEventListener("click", function (evento) {
    var link = evento.target.closest ? evento.target.closest('a[href^="#"]') : null;
    if (!link) return;
    var destino = document.getElementById(link.getAttribute("href").slice(1));
    if (!destino) return;
    evento.preventDefault();
    indice(false);
    destino.scrollIntoView({ behavior: suave ? "smooth" : "auto", block: "start" });
    try { history.replaceState(null, "", "#" + destino.id); } catch (erro) { /* dentro de um quadro sem histórico */ }
  });

  var links = $$("#indice a");
  var porId = {};
  links.forEach(function (a) { porId[a.getAttribute("href").slice(1)] = a; });
  function marcar(id) {
    links.forEach(function (a) { a.classList.toggle("atual", a === porId[id]); });
    var atual = porId[id];
    if (atual && trilho && trilho.scrollHeight > trilho.clientHeight) {
      var topo = atual.offsetTop - trilho.scrollTop;
      if (topo < 60 || topo > trilho.clientHeight - 120) trilho.scrollTop = Math.max(0, atual.offsetTop - trilho.clientHeight / 2);
    }
  }
  if ("IntersectionObserver" in window) {
    var visiveis = {};
    var observador = new IntersectionObserver(function (itens) {
      itens.forEach(function (item) { visiveis[item.target.id] = item.isIntersecting; });
      for (var i = 0; i < links.length; i++) {
        var id = links[i].getAttribute("href").slice(1);
        if (visiveis[id]) { marcar(id); break; }
      }
    }, { rootMargin: "-12% 0px -72% 0px" });
    Object.keys(porId).forEach(function (id) { var secao = document.getElementById(id); if (secao) observador.observe(secao); });
  }
  marcar("inicio");

  /* ------------------------------------------------------------ tema claro e escuro */
  var raiz = document.documentElement, trocaTema = $("#troca-tema");
  function temaAtual() {
    if (raiz.getAttribute("data-theme")) return raiz.getAttribute("data-theme");
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function rotuloTema() { if (trocaTema) $("span", trocaTema).textContent = temaAtual() === "dark" ? "Tema claro" : "Tema escuro"; }
  try {
    var guardado = localStorage.getItem("finpro-site-tema");
    if (guardado && !raiz.getAttribute("data-theme")) raiz.setAttribute("data-theme", guardado);
  } catch (erro) { /* sem armazenamento: segue o tema do aparelho */ }
  if (trocaTema) {
    trocaTema.addEventListener("click", function () {
      var novo = temaAtual() === "dark" ? "light" : "dark";
      raiz.setAttribute("data-theme", novo);
      try { localStorage.setItem("finpro-site-tema", novo); } catch (erro) { /* idem */ }
      rotuloTema();
    });
  }
  rotuloTema();
})();
