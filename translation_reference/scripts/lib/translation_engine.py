# -*- coding: utf-8 -*-
"""Cliente do motor LLM local compativel com a API OpenAI (chat/completions).

Componente do objetivo "motor de traducao local": envia lotes de textos
para um servidor compativel com OpenAI (por padrao Ollama em
``http://localhost:11434/v1``) e devolve as traducoes na MESMA ordem da
entrada, sem depender de bibliotecas externas (somente stdlib do Python 3).

Contrato de ``OpenAICompatEngine``
---------------------------------
- ``translate_batch(texts)`` divide a entrada em chunks de ``chunk_size``
  itens e faz um POST em ``{base_url}/chat/completions`` por chunk.
  Tanto ``translate_batch`` quanto ``translate_batch_resilient`` aceitam o
  kwarg opcional ``on_progress(done, total)``, chamado apos cada chunk
  resolvido, para progresso incremental no consumidor (CLI/painel).
- O corpo JSON usa ``{"model", "messages"}`` com mensagem de sistema fixa
  (``SYSTEM_PROMPT``) que exige preservar placeholders, markup e tags
  ({}, %s, %d, \\n, [tags], <tags>, \\N) e devolver UMA traducao por linha,
  na mesma ordem. A mensagem de usuario lista os textos numerados, um por
  linha (``1. texto``).
- A resposta e lida de ``choices[0].message.content`` e recortada por
  linhas (cada linha sofre ``strip()`` e remove prefixo numerico ecoado
  pelo modelo, ex.: ``"1. texto"``/``"2) texto"`` -> ``"texto"``). Blocos
  ``<think>...</think>`` (familia qwen3/deepseek-r1 via alguns servidores)
  sao descartados antes do recorte. Se a contagem de linhas difere do
  numero de textos enviados, tenta um resgate: remapeia as linhas PELO
  NUMERO do protocolo ("N. texto"), ignorando preambulo/rodape sem numero;
  so levanta ``TranslationError`` se o resgate tambem nao fechar 1..N.
- O payload inclui ``temperature`` (padrao 0.2, configuravel no
  construtor) para reduzir variacao nas respostas do modelo local.
- Retry: erros de rede, timeout e HTTP 5xx sao re-tentados ate ``retries``
  vezes com backoff curto entre tentativas (total = ``retries + 1``
  tentativas). HTTP 4xx falha imediatamente, sem retry.
- ``translate_batch_resilient(texts)`` e a variante tolerante a falha:
  quando um chunk retorna contagem divergente ou erro, ele e dividido ao
  meio recursivamente ate chunks unitarios; o item que falha mesmo sozinho
  entra em ``failed_indices`` com traducao vazia na posicao correspondente,
  sem derrubar os vizinhos. Devolve ``(translations, failed_indices)``.
  Kwarg opcional ``collect_reasons`` (dict): recebe index -> nota curta do
  motivo da falha individual ("chunk divergente apos subdivisao" ou
  "motor de traducao indisponivel"), para relatorios auditaveis.
- ``TranslationError`` cobre rede, HTTP e resposta invalida, sempre com
  mensagem pt-BR sem acento (ASCII puro), para nao quebrar logs/CSV no
  Windows; detalhes vindos do SO sao reduzidos a ASCII antes de entrar na
  mensagem. ``TranslationUnavailableError`` (subclasse) sinaliza falha de
  rede/5xx/tentativas esgotadas, distinta de problema de protocolo.
"""

import http.client
import json
import re
import time
import urllib.error
import urllib.request

__all__ = [
    "TranslationError",
    "TranslationUnavailableError",
    "OpenAICompatEngine",
    "NOTE_DIVERGENT",
    "NOTE_UNAVAILABLE",
]

SYSTEM_PROMPT = (
    "You are a game translator. Translate Japanese to English. "
    "Preserve ALL placeholders, markup and tags exactly "
    "({}, %s, %d, \\n, [tags], <tags>, \\N). "
    "Do NOT wrap proper nouns in square brackets. "
    "Render names in romaji/English without any brackets. "
    "Output ONLY the translations, one per line, same order."
)

# Notas curtas de falha individual do modo resiliente (entram no CSV).
NOTE_DIVERGENT = "chunk divergente apos subdivisao"
NOTE_UNAVAILABLE = "motor de traducao indisponivel"

# Backoff base entre tentativas de retry (cresce linearmente por tentativa).
_RETRY_BACKOFF_SECONDS = 0.25

# Prefixo numerico ecoado pelo modelo em cada linha ("1. texto"/"2) texto",
# tambem "- 3. texto", "**4.** texto", "5、texto"). Removido antes do
# mapeamento linha -> traducao. Traco/hifen NAO e separador aqui para nao
# corromper textos que comecam com numeros ("1-UP"); o resgate aceita.
_NUMBERED_LINE_PREFIX = re.compile(
    r"^\s*(?:[-*\u2022]\s*)?(?:\*\*|__|`{1,3})?\s*"
    r"\d+\s*(?:[.)\uFF09\u3001]|[:：])\s*"
    r"(?:\*\*|__|`{1,3})?\s*"
)

# Mesmo padrao, mas capturando numero e conteudo (resgate por protocolo).
# Aceita tambem rotulo entre colchetes ("[1] texto"), comum em modelos locais.
_NUMBERED_LINE_MATCH = re.compile(
    r"^\s*(?:"
    r"\[\s*(\d+)\s*\]"
    r"|"
    r"(?:[-*\u2022]\s*)?(?:\*\*|__|`{1,3})?\s*(\d+)\s*"
    r"(?:[.)\uFF09\u3001]|[:：]|[-\u2013\u2014])\s*(?:\*\*|__|`{1,3})?"
    r")\s*(.*)$",
    re.DOTALL,
)

# Bloco de raciocinio emitido por modelos "thinking" antes da resposta.
_THINK_BLOCK_RE = re.compile(r"<think\b[^>]*>.*?</think\s*>", re.IGNORECASE | re.DOTALL)


class TranslationError(Exception):
    """Erro de rede, HTTP ou resposta invalida durante a traducao."""


class TranslationUnavailableError(TranslationError):
    """Falha de rede/HTTP 5xx/tentativas esgotadas (servidor indisponivel)."""


class _RetryableError(Exception):
    """Erro transitorio interno (rede/5xx/timeout) elegivel a nova tentativa."""

    def __init__(self, detail):
        super().__init__(detail)
        self.detail = detail


def _sanitize_ascii(text):
    """Reduz texto externo a ASCII (SO pode devolver detalhes acentuados)."""
    return str(text).encode("ascii", "replace").decode("ascii")


def _describe_error(exc):
    """Extrai uma descricao curta de um erro de rede/HTTP."""
    reason = getattr(exc, "reason", None)
    source = exc if reason is None else reason
    return _sanitize_ascii(source)


class OpenAICompatEngine:
    """Cliente HTTP minimo para servidores locais compativeis com OpenAI."""

    def __init__(
        self,
        base_url="http://localhost:11434/v1",
        model="qwen2.5:7b-instruct",
        timeout=120,
        retries=2,
        chunk_size=20,
        temperature=0.2,
    ):
        self.base_url = str(base_url).rstrip("/")
        self.model = model
        self.timeout = timeout
        self.retries = max(0, int(retries))
        self.chunk_size = max(1, int(chunk_size))
        self.temperature = float(temperature)

    # ------------------------------------------------------------------
    # API publica

    def translate_batch(self, texts, on_progress=None):
        """Traduz uma lista de textos preservando a ordem da entrada.

        Levanta ``TypeError`` para entradas nao-lista ou itens nao-string e
        ``TranslationError`` para falha de rede, HTTP ou resposta invalida.
        Lista vazia devolve lista vazia sem fazer nenhuma requisicao.

        ``on_progress(done, total)`` opcional: chamado apos cada chunk
        resolvido com os totais relativos a esta lista.
        """
        if isinstance(texts, tuple):
            texts = list(texts)
        if not isinstance(texts, list):
            raise TypeError(
                "translate_batch espera uma lista de strings, recebeu %r"
                % type(texts).__name__
            )
        for item in texts:
            if not isinstance(item, str):
                raise TypeError(
                    "translate_batch espera apenas strings, recebeu %r"
                    % type(item).__name__
                )

        results = []
        total = len(texts)
        for start in range(0, len(texts), self.chunk_size):
            chunk = texts[start : start + self.chunk_size]
            results.extend(self._translate_chunk(chunk))
            if on_progress is not None:
                on_progress(min(start + self.chunk_size, total), total)
        return results

    def translate_batch_resilient(self, texts, on_progress=None, collect_reasons=None):
        """Traduz tolerando falha isolada de chunk (nao propaga ao lote todo).

        Diferente de ``translate_batch`` (que levanta ``TranslationError`` no
        primeiro problema), aqui um chunk com contagem de linhas divergente
        ou erro de rede/HTTP e subdividido ao meio recursivamente ate chegar
        a chunks unitarios. Item que falha mesmo sozinho entra em
        ``failed_indices`` e fica com "" na posicao correspondente das
        traducoes; os demais itens mantem a ordem da entrada.

        Devolve ``(translations, failed_indices)``. Levanta ``TypeError``
        para entradas nao-lista ou itens nao-string, como ``translate_batch``.
        Lista vazia devolve ``([], [])`` sem fazer nenhuma requisicao.

        ``on_progress(done, total)`` opcional: chamado apos cada chunk do
        nivel mais alto ser resolvido (itens falhos contam como processados),
        com os totais relativos a esta lista.

        ``collect_reasons`` opcional (dict mutavel): preenchido com
        index -> nota curta (NOTE_DIVERGENT ou NOTE_UNAVAILABLE) para cada
        indice que falhar individualmente.
        """
        if isinstance(texts, tuple):
            texts = list(texts)
        if not isinstance(texts, list):
            raise TypeError(
                "translate_batch_resilient espera uma lista de strings, "
                "recebeu %r" % type(texts).__name__
            )
        for item in texts:
            if not isinstance(item, str):
                raise TypeError(
                    "translate_batch_resilient espera apenas strings, "
                    "recebeu %r" % type(item).__name__
                )

        translations = ["" for _ in texts]
        failed_indices = []
        total = len(texts)
        for start in range(0, len(texts), self.chunk_size):
            chunk = texts[start : start + self.chunk_size]
            self._resilient_chunk(
                chunk, start, translations, failed_indices, collect_reasons
            )
            if on_progress is not None:
                on_progress(min(start + self.chunk_size, total), total)
        return translations, sorted(failed_indices)

    def _resilient_chunk(
        self, chunk, base_index, translations, failed_indices, reasons=None
    ):
        """Traduz um chunk; em falha, divide ao meio ate tamanho unitario.

        Em chunks unitarios a falha e isolada naquele indice; quando o
        dict ``reasons`` e fornecido, registra se foi problema de protocolo
        (NOTE_DIVERGENT) ou servidor indisponivel (NOTE_UNAVAILABLE).
        """
        try:
            outputs = self._translate_chunk(chunk)
        except TranslationError as exc:
            if len(chunk) == 1:
                translations[base_index] = ""
                failed_indices.append(base_index)
                if reasons is not None:
                    if isinstance(exc, TranslationUnavailableError):
                        reasons[base_index] = NOTE_UNAVAILABLE
                    else:
                        reasons[base_index] = NOTE_DIVERGENT
                return
            middle = len(chunk) // 2
            self._resilient_chunk(
                chunk[:middle], base_index, translations, failed_indices, reasons
            )
            self._resilient_chunk(
                chunk[middle:], base_index + middle, translations, failed_indices, reasons
            )
            return
        for offset, output in enumerate(outputs):
            translations[base_index + offset] = output

    # ------------------------------------------------------------------
    # envio por chunk

    def _build_user_message(self, chunk):
        return "\n".join(
            "%d. %s" % (number, text) for number, text in enumerate(chunk, start=1)
        )

    def _translate_chunk(self, chunk):
        content = self._request_chat_completion(chunk)
        return self._split_translations(content, expected=len(chunk))

    def _request_chat_completion(self, chunk):
        url = self.base_url + "/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self._build_user_message(chunk)},
            ],
            "temperature": self.temperature,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        total_attempts = self.retries + 1
        last_detail = ""
        for attempt in range(total_attempts):
            try:
                return self._post_once(url, body)
            except _RetryableError as exc:
                last_detail = exc.detail
                if attempt < total_attempts - 1:
                    time.sleep(_RETRY_BACKOFF_SECONDS * (attempt + 1))
        raise TranslationUnavailableError(
            "Servidor de traducao indisponivel apos %d tentativas: %s"
            % (total_attempts, last_detail)
        )

    def _post_once(self, url, body):
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            exc.close()
            if 500 <= exc.code < 600:
                raise _RetryableError(
                    "Erro HTTP %d do servidor de traducao." % exc.code
                )
            raise TranslationError(
                "Requisicao rejeitada pelo servidor de traducao (HTTP %d)." % exc.code
            )
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError) as exc:
            raise _RetryableError(
                "Falha de rede ao contatar o servidor de traducao: %s"
                % _describe_error(exc)
            )
        return self._extract_content(raw)

    # ------------------------------------------------------------------
    # leitura da resposta

    def _extract_content(self, raw):
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise TranslationError(
                "Resposta invalida do servidor de traducao: corpo nao e JSON valido."
            )
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise TranslationError(
                "Resposta invalida do servidor de traducao: campo "
                "'choices[0].message.content' ausente ou malformado."
            )
        if not isinstance(content, str):
            raise TranslationError(
                "Resposta invalida do servidor de traducao: conteudo da "
                "mensagem nao e texto."
            )
        return content

    def _split_translations(self, content, expected):
        # Blocos <think> de modelos "thinking" nao sao traducao: descartados
        # antes do recorte (senao virariam linhas extras e derrubariam o chunk).
        cleaned = _THINK_BLOCK_RE.sub("", content).strip()
        raw_lines = [line.strip() for line in cleaned.splitlines()]
        raw_lines = [line for line in raw_lines if line != ""]
        # Modelos locais as vezes ecoam a numeracao do prompt em cada linha
        # ("1. texto"/"2) texto"); o prefixo e removido antes do mapeamento.
        lines = [_NUMBERED_LINE_PREFIX.sub("", line) for line in raw_lines]
        # Contagem igual nao garante alinhamento: se o modelo SOMOU uma linha
        # de ruido e PERDEU uma traducao, o total fecha e o mapeamento
        # posicional sairia deslocado. Quando ha rotulos numerados, eles
        # precisam confirmar a sequencia 1..N; caso contrario, cai no resgate.
        if len(lines) == expected and self._numbering_alignment_ok(raw_lines, expected):
            return lines
        # Contagem divergente (ou rotulos fora de ordem): tenta resgatar pelo
        # proprio protocolo antes de falhar. Preambulo/rodape/comentarios sem
        # numero ("Here are the translations:", blocos de codigo, frases de
        # abertura) sao ignorados; se os numeros 1..N aparecerem exatamente
        # uma vez cada, o resultado e confiavel mesmo com o ruido extra ao
        # redor. Isso evita o cenario em que UM modelo verboso diverge em
        # TODOS os chunks (inclusive unitarios) e derruba 100% do lote.
        salvaged = self._salvage_numbered_lines(cleaned, expected)
        if salvaged is not None:
            return salvaged
        raise TranslationError(
            "Numero de linhas traduzidas (%d) difere do numero de textos "
            "enviados (%d)." % (len(lines), expected)
        )

    @staticmethod
    def _numbering_alignment_ok(raw_lines, expected):
        """True se os rotulos numerados presentes nao contradizem 1..N.

        Resposta sem nenhum rotulo => nada a verificar (True). Com rotulos,
        exige a sequencia completa 1..N na ordem; qualquer desvio (linha de
        ruido no meio, item perdido, ordem trocada) devolve False e empurra
        a decisao para o resgate por protocolo ou para a falha explicita.
        """
        labels = []
        for line in raw_lines:
            match = _NUMBERED_LINE_MATCH.match(line)
            labels.append(
                int(match.group(1) or match.group(2)) if match else None
            )
        known = [label for label in labels if label is not None]
        if not known:
            return True
        return known == list(range(1, expected + 1))

    @staticmethod
    def _salvage_numbered_lines(content, expected):
        """Remapeia linhas pelo numero do protocolo; None se nao fechar 1..N.

        Aceita variacoes de prefixo (bullets, markdown, separadores) via
        ``_NUMBERED_LINE_MATCH``. Linha sem numero e preambulo/rodape ou
        continuacao de linha longa e fica fora do resgate (o prompt exige
        uma traducao por linha); numero repetido, fora da faixa ou vazio
        anula o resgate.
        """
        collected = {}
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("```"):
                continue
            match = _NUMBERED_LINE_MATCH.match(line)
            if match is None:
                continue
            raw_number = match.group(1) or match.group(2)
            number = int(raw_number)
            # Eco duplo de numeracao ("1. 2. texto"): remove o residuo.
            text = _NUMBERED_LINE_PREFIX.sub("", match.group(3).strip())
            if not text:
                return None
            if not 1 <= number <= expected or number in collected:
                return None
            collected[number] = text
        if len(collected) != expected:
            return None
        return [collected[index] for index in range(1, expected + 1)]


if __name__ == "__main__":
    print("Este modulo e uma biblioteca; importe OpenAICompatEngine.")
