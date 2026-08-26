# -*- coding: utf-8 -*-
"""Testes offline do cliente do motor LLM local (unittest, somente stdlib).

Cobertura exigida pelo objetivo "motor de traducao local":
- payload correto enviado a /chat/completions (model + messages + temperature);
- ordem das traducoes preservada em relacao a entrada;
- divisao em chunks: 5 itens com chunk_size=2 => 3 requests (2+2+1);
- retry: servidor falha 1x com 500 e responde na 2a tentativa;
- esgotar as tentativas em erro de rede/500 levanta TranslationError;
- HTTP 4xx falha imediatamente, sem retry;
- contagem de linhas divergente na resposta levanta TranslationError;
- resposta malformada (sem choices) levanta TranslationError;
- prefixo numerico ecoado pelo modelo ("1. "/"2) ") e removido por linha,
  sem corromper linha sem prefixo; formatos estendidos (bullets, markdown,
  "2、") tambem sao tratados;
- preambulo verboso/bloco <think> do modelo NAO derruba o chunk: o parser
  resgata pelo protocolo numerado (causa raiz do incidente 940/940);
- translate_batch_resilient: chunk com sub-intervalo divergente derruba
  apenas os itens realmente falhos; divergencia restrita a chunks grandes
  recupera a maioria dos itens (subdivisao ate tamanho <= 2);
- collect_reasons distingue "motor de traducao indisponivel" de
  "chunk divergente apos subdivisao";
- mensagens de erro sao pt-BR sem acento (ASCII puro).

O servidor fake sobe em 127.0.0.1 numa porta efemera (ThreadingHTTPServer
em thread daemon) e responde POST /v1/chat/completions com traducoes
derivadas da propria entrada ("echo" numerado), o que permite validar
payload, ordem e contagem sem rede externa.
"""
import json
import socket
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB_DIR = HERE.parent / "scripts" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

import translation_engine  # noqa: E402

TEXTS_DEMO = ["モンスターが現れた！", "こんにちは。", "セーブしますか？"]


# ----------------------------------------------------------------------
# servidor fake de /v1/chat/completions


class _FakeState:
    """Estado compartilhado entre o servidor fake e os testes."""

    def __init__(self):
        self.lock = threading.Lock()
        self.requests = []          # payloads JSON recebidos, em ordem
        self.pending_500 = 0        # proximas respostas que falham com 500
        self.forced_status = None   # se definido, toda resposta usa esse status
        self.fixed_content = None   # se definido, content devolvido literalmente
        self.malformed_body = False  # se True, responde 200 sem campo choices
        # Se definido, toda resposta "echo" OMITE as linhas cujo texto contém
        # esse marcador (simula contagem divergente persiste no sub-intervalo).
        self.drop_lines_containing = None
        # Se definido, essa linha e ANEXADA antes do conteudo (preambulo
        # verboso do modelo => contagem divergente em TODOS os tamanhos).
        self.preamble = None
        # Se definido junto com preamble_only_above, o preambulo entra só em
        # respostas para pedidos com MAIS itens que esse limite (simula
        # divergencia apenas em chunks grandes).
        self.preamble_only_above = None


def _echo_translations(payload, drop_marker=None):
    """Deriva uma linha de traducao por linha numerada 'N. texto'.

    Com ``drop_marker``, linhas cujo texto original contém o marcador sao
    omitidas da resposta (contagem divergente para aquele sub-intervalo).
    """
    user_content = payload["messages"][1]["content"]
    out = []
    for line in user_content.splitlines():
        number, _, text = line.partition(". ")
        if drop_marker is not None and drop_marker in text:
            continue
        out.append("[%s]%s" % (number.strip(), text))
    return "\n".join(out)


def _make_handler(state):
    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # silencia stderr no suite
            pass

        def _send_json(self, status, obj):
            raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            except OSError:
                pass  # cliente desistiu; nada a fazer

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length") or 0)
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                self._send_json(400, {"error": "payload invalido"})
                return

            with state.lock:
                state.requests.append(payload)
                fail_500 = state.pending_500 > 0
                if fail_500:
                    state.pending_500 -= 1
                forced_status = state.forced_status
                fixed_content = state.fixed_content
                malformed_body = state.malformed_body
                drop_marker = state.drop_lines_containing
                preamble = state.preamble
                preamble_only_above = state.preamble_only_above

            if fail_500:
                self._send_json(500, {"error": "instavel"})
                return
            if forced_status is not None:
                self._send_json(forced_status, {"error": "forjado"})
                return
            if malformed_body:
                self._send_json(200, {"resposta": "sem choices aqui"})
                return
            content = (
                fixed_content
                if fixed_content is not None
                else _echo_translations(payload, drop_marker=drop_marker)
            )
            if preamble is not None:
                item_count = len(
                    payload["messages"][1]["content"].splitlines()
                )
                big = preamble_only_above is None or item_count > preamble_only_above
                if big and not content.startswith(preamble):
                    content = preamble + "\n" + content
            self._send_json(
                200,
                {"choices": [{"message": {"role": "assistant", "content": content}}]},
            )

    return _Handler


class FakeLLMServer:
    """Servidor efemero que imita POST /v1/chat/completions para os testes."""

    def __init__(self):
        self.state = _FakeState()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(self.state))
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def base_url(self):
        return "http://127.0.0.1:%d/v1" % self.port

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)


def _free_tcp_port():
    """Reserva e libera uma porta livre (para simular conexao recusada)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


# ----------------------------------------------------------------------
# casos de teste


class EngineCase(unittest.TestCase):
    """Base com servidor fake por teste e fabrica de engines."""

    def setUp(self):
        self.server = FakeLLMServer()
        self.addCleanup(self.server.stop)

    def make_engine(self, **overrides):
        options = {"base_url": self.server.base_url, "timeout": 10}
        options.update(overrides)
        return translation_engine.OpenAICompatEngine(**options)

    def request_count(self):
        with self.server.state.lock:
            return len(self.server.state.requests)

    def user_content_of(self, index):
        with self.server.state.lock:
            return self.server.state.requests[index]["messages"][1]["content"]

    def assert_error_is_clean(self, context):
        message = str(context.exception)
        self.assertTrue(
            message.isascii(),
            "mensagem de erro deve ser pt-BR sem acento (ASCII): %r" % message,
        )


class DefaultsAndContractTests(unittest.TestCase):
    """Contrato publico da API (valores padrao e prompt de sistema)."""

    def test_default_constructor_values(self):
        engine = translation_engine.OpenAICompatEngine()
        self.assertEqual(engine.base_url, "http://localhost:11434/v1")
        self.assertEqual(engine.model, "qwen2.5:7b-instruct")
        self.assertEqual(engine.timeout, 120)
        self.assertEqual(engine.retries, 2)
        self.assertEqual(engine.chunk_size, 20)
        self.assertEqual(engine.temperature, 0.2)

    def test_system_prompt_preserves_placeholder_tokens(self):
        prompt = translation_engine.SYSTEM_PROMPT
        for token in ("{}", "%s", "%d", "\\n", "[tags]", "<tags>", "\\N"):
            self.assertIn(token, prompt)
        self.assertIn("one per line, same order", prompt)


class PayloadOrderAndChunkingTests(EngineCase):
    def test_single_chunk_sends_model_messages_and_preserves_order(self):
        texts = list(TEXTS_DEMO)
        result = self.make_engine().translate_batch(texts)

        expected = ["[%d]%s" % (i, t) for i, t in enumerate(texts, start=1)]
        self.assertEqual(result, expected)
        self.assertEqual(self.request_count(), 1)

        payload = self.server.state.requests[0]
        self.assertEqual(payload["model"], "qwen2.5:7b-instruct")
        self.assertEqual(payload["temperature"], 0.2)
        messages = payload["messages"]
        self.assertEqual(len(messages), 2)
        self.assertEqual([m["role"] for m in messages], ["system", "user"])
        self.assertEqual(messages[0]["content"], translation_engine.SYSTEM_PROMPT)
        numbered = ["%d. %s" % (i, t) for i, t in enumerate(texts, start=1)]
        self.assertEqual(messages[1]["content"], "\n".join(numbered))

    def test_chunk_size_two_with_five_texts_makes_three_requests_in_order(self):
        texts = ["一つ目", "二つ目", "三つ目", "四つ目", "五つ目"]
        result = self.make_engine(chunk_size=2).translate_batch(texts)

        # Numeracao reinicia a cada chunk: [1,2] [3,4] [5].
        expected = ["[1]一つ目", "[2]二つ目", "[1]三つ目", "[2]四つ目", "[1]五つ目"]
        self.assertEqual(result, expected)
        self.assertEqual(self.request_count(), 3)
        sizes = [len(self.user_content_of(i).splitlines()) for i in range(3)]
        self.assertEqual(sizes, [2, 2, 1])
        for payload in self.server.state.requests:
            self.assertEqual(payload["model"], "qwen2.5:7b-instruct")
            self.assertEqual(
                payload["messages"][0]["content"],
                translation_engine.SYSTEM_PROMPT,
            )

    def test_empty_batch_returns_empty_without_requests(self):
        result = self.make_engine().translate_batch([])
        self.assertEqual(result, [])
        self.assertEqual(self.request_count(), 0)

    def test_custom_temperature_is_sent_in_payload(self):
        result = self.make_engine(temperature=0.7).translate_batch(["テスト"])

        self.assertEqual(result, ["[1]テスト"])
        self.assertEqual(self.server.state.requests[0]["temperature"], 0.7)


class NumericPrefixStripTests(EngineCase):
    """Modelo as vezes ecoa a numeracao do prompt em cada linha devolvida."""

    def test_numbered_prefixes_are_stripped_from_each_line(self):
        self.server.state.fixed_content = (
            "1. First line.\n"
            "2) Second line.\n"
            "3.  Third with extra spaces.\n"
            "4.No space after dot."
        )
        texts = ["一", "二", "三", "四"]

        result = self.make_engine().translate_batch(texts)

        self.assertEqual(
            result,
            [
                "First line.",
                "Second line.",
                "Third with extra spaces.",
                "No space after dot.",
            ],
        )

    def test_line_without_numeric_prefix_is_not_corrupted(self):
        self.server.state.fixed_content = "Plain line stays.\nAlso stays."

        result = self.make_engine().translate_batch(["一", "二"])

        self.assertEqual(result, ["Plain line stays.", "Also stays."])


class ResilientBatchTests(EngineCase):
    """translate_batch_resilient: falha de chunk nao derruba o lote inteiro."""

    def test_divergent_sub_interval_fails_only_affected_items(self):
        texts = ["テキスト%02d" % i for i in range(20)]
        poisoned = 13
        texts[poisoned] = "毒VENENO入りテキスト"
        self.server.state.drop_lines_containing = "VENENO"

        translations, failed = self.make_engine(
            chunk_size=10, retries=0
        ).translate_batch_resilient(texts)

        self.assertEqual(failed, [poisoned])
        self.assertEqual(translations[poisoned], "")
        # Ordem preservada e conteudo correto em TODAS as posicoes boas
        # (a numeracao do echo reinicia por sub-chunk apos a subdivisao).
        good_positions = [i for i in range(len(texts)) if i != poisoned]
        self.assertEqual(
            sorted(set(failed) | set(good_positions)), list(range(len(texts)))
        )
        for i in good_positions:
            self.assertTrue(
                translations[i].startswith("[") and translations[i].endswith(texts[i]),
                "posicao %d deveria conter a traducao do proprio texto: %r"
                % (i, translations[i]),
            )
        # A subdivisao recursiva realmente aconteceu (varias requisicoes).
        self.assertGreater(self.request_count(), 2)

    def test_single_item_chunk_failure_is_isolated_to_that_index(self):
        texts = ["ひとつ", "ふたつ"]
        self.server.state.pending_500 = 99

        translations, failed = self.make_engine(
            chunk_size=1, retries=0
        ).translate_batch_resilient(texts)

        self.assertEqual(failed, [0, 1])
        self.assertEqual(translations, ["", ""])
        self.assertEqual(
            self.request_count(), 2, "chunk unitario nao pode ser subdividido"
        )

    def test_unit_chunk_failure_keeps_neighbors_translated(self):
        texts = ["生き残りA", "破損B", "生き残りC"]
        self.server.state.drop_lines_containing = "破損"

        translations, failed = self.make_engine(
            chunk_size=3, retries=0
        ).translate_batch_resilient(texts)

        self.assertEqual(failed, [1])
        self.assertEqual(translations[0], "[1]生き残りA")
        self.assertEqual(translations[1], "")
        self.assertTrue(translations[2].endswith("生き残りC"))

    def test_resilient_success_matches_translate_batch_contract(self):
        texts = ["一つ目", "二つ目", "三つ目", "四つ目", "五つ目"]

        translations, failed = self.make_engine(chunk_size=2).translate_batch_resilient(
            texts
        )

        self.assertEqual(failed, [])
        # Numeracao reinicia a cada chunk (2+2+1), igual ao translate_batch.
        expected = [
            "[1]一つ目",
            "[2]二つ目",
            "[1]三つ目",
            "[2]四つ目",
            "[1]五つ目",
        ]
        self.assertEqual(translations, expected)

    def test_empty_input_returns_empty_pair_without_requests(self):
        translations, failed = self.make_engine().translate_batch_resilient([])

        self.assertEqual((translations, failed), ([], []))
        self.assertEqual(self.request_count(), 0)

    def test_input_validation_matches_translate_batch(self):
        engine = self.make_engine()
        with self.assertRaises(TypeError):
            engine.translate_batch_resilient("nao sou lista")
        with self.assertRaises(TypeError):
            engine.translate_batch_resilient([42])
        self.assertEqual(self.request_count(), 0)


class SalvageProtocolNoiseTests(EngineCase):
    """Causa raiz do incidente 940/940: ruido de protocolo em todo chunk.

    Modelos verbosos inserem preambulo/rodape/bloco <think> antes das linhas
    numeradas. Antes da correcao isso virava contagem divergente em TODOS os
    tamanhos de chunk (inclusive o unitario) e derrubava 100% do lote com
    nota generica. Agora o parser resgata pelo proprio protocolo numerado.
    """

    PREAMBLE = "Sure! Here are the translations:"

    def test_verbose_preamble_on_every_chunk_no_longer_drops_the_batch(self):
        self.server.state.preamble = self.PREAMBLE
        texts = ["テキスト%02d" % i for i in range(6)]

        translations, failed = self.make_engine(
            chunk_size=3, retries=0
        ).translate_batch_resilient(texts)

        self.assertEqual(failed, [], "preambulo nao pode derrubar itens bons")
        # O resgate consome o rotulo numerico do eco e devolve o texto puro.
        for i, text in enumerate(texts):
            self.assertEqual(translations[i], text)
        # Resgate funciona ja no chunk original: sem subdivisao a mais.
        self.assertEqual(self.request_count(), 2)

    def test_translate_batch_also_salvages_preamble(self):
        self.server.state.preamble = self.PREAMBLE
        result = self.make_engine(chunk_size=3).translate_batch(TEXTS_DEMO)
        self.assertEqual(result, list(TEXTS_DEMO))

    def test_think_block_is_discarded_before_line_split(self):
        self.server.state.fixed_content = (
            "<think>Devo traduzir 3 itens. Plano:\n1. x\n2. y</think>\n"
            "1. Primeira\n2. Segunda\n3. Terceira"
        )

        result = self.make_engine().translate_batch(["一", "二", "三"])

        self.assertEqual(result, ["Primeira", "Segunda", "Terceira"])

    def test_noise_without_numbers_and_wrong_count_still_fails(self):
        self.server.state.fixed_content = "apenas conversa\nsem traducao nenhuma"

        with self.assertRaises(translation_engine.TranslationError) as ctx:
            self.make_engine().translate_batch(["一"])

        self.assert_error_is_clean(ctx)

    def test_duplicated_number_aborts_salvage(self):
        self.server.state.fixed_content = "Intro.\n1. primeira\n1. duplicada\n2. segunda"

        with self.assertRaises(translation_engine.TranslationError):
            self.make_engine().translate_batch(["一", "二"])

    def test_extended_numbering_formats_are_stripped(self):
        self.server.state.fixed_content = (
            "1) Alpha\n"
            "2、Beta\n"
            "- 3. Gamma\n"
            "**4.** Delta"
        )

        result = self.make_engine().translate_batch(["一", "二", "三", "四"])

        self.assertEqual(result, ["Alpha", "Beta", "Gamma", "Delta"])

    def test_number_out_of_range_or_missing_blocks_salvage(self):
        # Numero fora da faixa 1..N em resposta com contagem divergente:
        # o resgate nao pode aceitar rotulo invalido.
        self.server.state.fixed_content = "Intro.\n0. zero\n1. um"

        with self.assertRaises(translation_engine.TranslationError):
            self.make_engine().translate_batch(["一", "二"])

    def test_noise_plus_dropped_line_with_matching_count_is_rejected(self):
        """Contagem que fecha por coincidencia NAO pode passar desalinhada.

        Cenario real descoberto nos testes: modelo soma uma linha de ruido e
        perde uma traducao; o total bate e o mapeamento posicional sairia
        deslocado em silencio. Os rotulos numerados precisam confirmar a
        ordem; sem alinhamento, o chunk falha e a subdivisao resiliente
        recupera os itens bons.
        """
        self.server.state.fixed_content = (
            "Traducoes solicitadas:\n"
            "[1]um\n[3]tres\n[4]quatro\n[5]cinco\n[6]seis"
        )

        translations, failed = self.make_engine(
            chunk_size=6, retries=0
        ).translate_batch_resilient(["a%02d" % i for i in range(6)])

        self.assertEqual(failed, [0, 1, 2, 3, 4, 5])
        self.assertEqual(translations, [""] * 6)


class SizeGatedDivergenceResilienceTests(EngineCase):
    """Cenario obrigatorio: divergencia so em chunks grandes, acerto <= 2.

    O servidor injeta uma linha extra sempre que o pedido tem mais de 2
    itens e SEMPRE omite a linha do item envenenado. O modo resiliente deve
    subdividir ate tamanhos onde o servidor acerta, recuperar a maioria dos
    itens e isolar apenas o item realmente falho como failed individual.
    """

    def test_majority_translated_and_only_poisoned_item_fails(self):
        texts = ["テキスト%02d" % i for i in range(12)]
        poisoned = 7
        texts[poisoned] = "毒VENENO入りテキスト"
        self.server.state.preamble = "Traducoes solicitadas:"
        self.server.state.preamble_only_above = 2
        self.server.state.drop_lines_containing = "VENENO"

        translations, failed = self.make_engine(
            chunk_size=6, retries=0
        ).translate_batch_resilient(texts)

        # Unico falho = o item envenenado, isolado e vazio.
        self.assertEqual(failed, [poisoned])
        self.assertEqual(translations[poisoned], "")
        # Maioria traduzida: 11 de 12, cada posicao com o texto certo.
        good = [i for i in range(len(texts)) if i != poisoned]
        self.assertGreater(len(good), len(failed))
        for i in good:
            self.assertTrue(
                translations[i].endswith(texts[i]),
                "posicao %d deveria conter o proprio texto: %r" % (i, translations[i]),
            )
        # A subdivisao recursiva realmente aconteceu.
        self.assertGreater(self.request_count(), 2)


class FailureReasonTests(EngineCase):
    """collect_reasons distingue servidor indisponivel de protocolo."""

    def test_all_failed_by_server_marks_reason_unavailable(self):
        self.server.state.pending_500 = 99
        reasons = {}

        translations, failed = self.make_engine(
            chunk_size=2, retries=0
        ).translate_batch_resilient(
            ["ひとつ", "ふたつ"], collect_reasons=reasons
        )

        self.assertEqual(failed, [0, 1])
        self.assertEqual(translations, ["", ""])
        self.assertEqual(reasons, {0: translation_engine.NOTE_UNAVAILABLE,
                                   1: translation_engine.NOTE_UNAVAILABLE})

    def test_divergent_unit_chunk_marks_reason_divergent(self):
        self.server.state.drop_lines_containing = "破損"
        reasons = {}

        translations, failed = self.make_engine(
            chunk_size=1, retries=0
        ).translate_batch_resilient(
            ["okA", "破損B"], collect_reasons=reasons
        )

        self.assertEqual(failed, [1])
        self.assertEqual(translations[0], "[1]okA")
        self.assertEqual(reasons, {1: translation_engine.NOTE_DIVERGENT})

    def test_unavailable_error_is_subclass_of_translation_error(self):
        self.server.state.pending_500 = 99

        with self.assertRaises(translation_engine.TranslationError) as ctx:
            self.make_engine(retries=0).translate_batch(["テスト"])

        self.assertIsInstance(ctx.exception, translation_engine.TranslationUnavailableError)
        self.assert_error_is_clean(ctx)


class RetryTests(EngineCase):
    def test_recovers_when_server_fails_once_with_500(self):
        self.server.state.pending_500 = 1
        texts = ["ひとつ", "ふたつ"]

        result = self.make_engine(retries=2).translate_batch(texts)

        self.assertEqual(result, ["[1]ひとつ", "[2]ふたつ"])
        self.assertEqual(
            self.request_count(), 2, "erro 500 deve gerar exatamente 1 retry"
        )

    def test_exhausted_retries_raise_translation_error_on_500(self):
        self.server.state.pending_500 = 99

        with self.assertRaises(translation_engine.TranslationError) as ctx:
            self.make_engine(retries=1).translate_batch(["テスト"])

        self.assert_error_is_clean(ctx)
        self.assertEqual(self.request_count(), 2, "retries=1 => 2 tentativas no total")

    def test_http_4xx_fails_immediately_without_retry(self):
        self.server.state.forced_status = 404

        with self.assertRaises(translation_engine.TranslationError) as ctx:
            self.make_engine(retries=3).translate_batch(TEXTS_DEMO)

        self.assert_error_is_clean(ctx)
        self.assertIn("404", str(ctx.exception))
        self.assertEqual(
            self.request_count(), 1, "HTTP 4xx nao pode gerar retry"
        )

    def test_network_refused_exhausts_retries_and_raises(self):
        port = _free_tcp_port()

        with self.assertRaises(translation_engine.TranslationError) as ctx:
            engine = translation_engine.OpenAICompatEngine(
                base_url="http://127.0.0.1:%d/v1" % port,
                timeout=10,
                retries=1,
            )
            engine.translate_batch(["テスト"])

        self.assert_error_is_clean(ctx)


class ResponseContractTests(EngineCase):
    def test_line_count_mismatch_raises_translation_error(self):
        self.server.state.fixed_content = "so uma linha veio"

        with self.assertRaises(translation_engine.TranslationError) as ctx:
            self.make_engine().translate_batch(["一", "二"])

        self.assert_error_is_clean(ctx)
        self.assertIn("linha", str(ctx.exception).lower())

    def test_malformed_response_without_choices_raises(self):
        self.server.state.malformed_body = True

        with self.assertRaises(translation_engine.TranslationError) as ctx:
            self.make_engine().translate_batch(["テスト"])

        self.assert_error_is_clean(ctx)


if __name__ == "__main__":
    unittest.main()
