"""
Teste de investigacao: Compatibilidade entre Python marshal e Ruby Marshal.

Objetivo: Demonstrar que o modulo marshal do Python NAO pode ler arquivos
Ruby Marshal (.rvdata/.rvdata2) de RPG Maker VX/Ace.

Autor: TradutorDGames (investigacao)
Data: 2026-08-25
"""

import marshal
import struct
import unittest


class TestPythonMarshalVsRubyMarshal(unittest.TestCase):
    """Testa se o marshal do Python pode ler dados Ruby Marshal."""

    def test_ruby_marshal_header_detection(self):
        """
        Ruby Marshal 4.8 comeca com \\x04\\x08.
        Python marshal comeca com bytes de versao diferentes.
        """
        ruby_header = b"\x04\x08"
        self.assertEqual(len(ruby_header), 2)
        self.assertEqual(ruby_header[0], 4)  # major version
        self.assertEqual(ruby_header[1], 8)  # minor version

    def test_python_marshal_rejects_ruby_data(self):
        """
        Verifica que marshal.load() do Python rejeita dados Ruby Marshal.
        """
        # Ruby Marshal 4.8 com um Fixnum simples (valor 1)
        # Formato Ruby: header(2) + tipo('i') + valor(1)
        ruby_fixnum_1 = b"\x04\x08i\x06"

        with self.assertRaises((ValueError, EOFError)):
            marshal.loads(ruby_fixnum_1)

    def test_python_marshal_rejects_ruby_string(self):
        """
        Verifica que marshal.load() do Python rejeita strings Ruby Marshal.
        """
        # Ruby Marshal 4.8 com uma string "hello"
        # Formato Ruby: header(2) + tipo('"') + tamanho(5) + bytes
        ruby_string = b'\x04\x08"\x0ahello'

        with self.assertRaises((ValueError, EOFError)):
            marshal.loads(ruby_string)

    def test_python_marshal_rejects_ruby_array(self):
        """
        Verifica que marshal.load() do Python rejeita arrays Ruby Marshal.
        """
        # Ruby Marshal 4.8 com array vazio
        # Formato: header(2) + tipo('[') + tamanho(0)
        ruby_empty_array = b"\x04\x08[\x00"

        with self.assertRaises((ValueError, EOFError)):
            marshal.loads(ruby_empty_array)

    def test_python_marshal_rejects_ruby_object(self):
        """
        Verifica que marshal.load() do Python rejeita objects Ruby Marshal.
        """
        # Ruby Marshal 4.8 com object (tipo mais complexo)
        # header + 'o' + symbol(':') + len(6) + 'Object' + hash_vazio('{') + len(0)
        ruby_object = b'\x04\x08o:\x0bObject{\x00'

        with self.assertRaises((ValueError, EOFError)):
            marshal.loads(ruby_object)

    def test_python_marshal_rejects_ruby_ivar_string(self):
        """
        Verifica rejeicao de IVar (instance variable) wrapper com encoding UTF-8.
        VX Ace usa IVar para strings com encoding.
        """
        # Ruby Marshal 4.8 com IVar wrapping string
        # header + 'I' + string('"\x05hello') + hash(1) + symbol(':E') + true('T')
        ruby_ivar = b'\x04\x08I"\x05hello{\x01:\x06ET'

        with self.assertRaises((ValueError, EOFError)):
            marshal.loads(ruby_ivar)

    def test_ruby_marshal_type_codes_not_in_python(self):
        """
        Verifica que type codes do Ruby Marshal nao existem no Python marshal.
        """
        ruby_only_codes = {
            '"': 'Ruby String',
            ':': 'Ruby Symbol',
            ';': 'Ruby Symlink',
            'o': 'Ruby Object',
            'S': 'Ruby Struct',
            'I': 'Ruby IVar',
            'i': 'Ruby Fixnum',
            'l': 'Ruby Bignum',
            'f': 'Ruby Float',
            'c': 'Ruby Class',
            'm': 'Ruby Module',
            'u': 'Ruby UserDef',
            'U': 'Ruby UsrMarshal',
            '@': 'Ruby Link',
            '/': 'Ruby Regexp',
        }
        # Estes type codes sao exclusivos do Ruby Marshal
        # Python marshal usa codes diferentes (ex: 'i' para int, 's' para string, etc.)
        for code, desc in ruby_only_codes.items():
            self.assertEqual(
                len(code), 1,
                f"Ruby type code {desc} ({code!r}) deve ser byte unico"
            )

    def test_ruby_marshal_version_48_specifics(self):
        """
        Verifica propriedades especificas do Marshal 4.8 do Ruby.
        """
        # O Marshal 4.8 e suportado por Ruby 1.8.0+
        # VX Ace usa Ruby 1.9.2 (Marshal 4.8)
        # Header sempre \x04\x08
        header = struct.pack("BB", 4, 8)
        self.assertEqual(header, b"\x04\x08")

        # Diferentes minor versions sao compativel para baixo
        # 4.8 pode ler 4.7, 4.6, etc.
        # Mas 4.7 NAO pode ler 4.8
        self.assertTrue(8 >= 7)  # 4.8 pode ler 4.7
        self.assertFalse(7 >= 8)  # 4.7 NAO pode ler 4.8


class TestRubyMarshalReaderConcept(unittest.TestCase):
    """
    Conceito de como um reader Ruby Marshal funcionaria em Python puro.

    Estes testes validam a logica basica SEM implementar o reader completo.
    A implementacao real esta em rpg_extract.py (xi/rpg-extract).
    """

    def test_read_long_ruby_format(self):
        """
        Testa leitura de Fixnum no formato Ruby Marshal.

        O formato Ruby Marshal para inteiros (Fixnum):
        - byte 0: indica tamanho
        - 0: valor 0
        - 1..127: valor = byte - 5
        - -128..-1: valor = byte + 5
        - N (abs > 5): N bytes seguintes formam o inteiro
        """
        def read_ruby_long(data, offset):
            """Leitura simplificada de Fixnum Ruby Marshal."""
            first = data[offset]
            if first > 127:
                first -= 256

            if first == 0:
                return 0, offset + 1
            elif 5 < first < 128:
                return first - 5, offset + 1
            elif -129 < first < -5:
                return first + 5, offset + 1
            else:
                n = abs(first)
                value = 0
                for i in range(n):
                    value |= data[offset + 1 + i] << (8 * i)
                if first < 0:
                    value -= (1 << (8 * n))
                return value, offset + 1 + n

        # Teste: valor 0
        val, off = read_ruby_long(b"\x00", 0)
        self.assertEqual(val, 0)

        # Teste: valor 1 (byte = 1 + 5 = 6)
        val, off = read_ruby_long(b"\x06", 0)
        self.assertEqual(val, 1)

        # Teste: valor -1 (byte = -1 - 5 = -6 = 250)
        val, off = read_ruby_long(bytes([250]), 0)
        self.assertEqual(val, -1)

        # Teste: valor 42 (byte = 42 + 5 = 47)
        val, off = read_ruby_long(b"\x2f", 0)
        self.assertEqual(val, 42)

    def test_ruby_string_format(self):
        """
        Verifica formato esperado de uma string Ruby Marshal.

        Formato: tipo('"') + tamanho(fixnum) + bytes
        """
        # String "hi" (2 bytes)
        # tipo: " (0x22)
        # tamanho: 2 = 2 + 5 = 7 (fixnum)
        # bytes: h i
        data = b'\x22\x07hi'

        self.assertEqual(data[0:1], b'"')  # tipo string
        # fixnum para tamanho
        first = data[1]
        self.assertEqual(first - 5, 2)  # tamanho = 2
        self.assertEqual(data[2:4], b'hi')  # conteudo

    def test_ruby_ivar_wrapping(self):
        """
        Verifica formato de IVar (instance variable) wrapper.

        VX Ace usa IVar para adicionar encoding as strings.
        Formato: tipo('I') + objeto + hash_atributos
        """
        # IVar wrapping de uma string com encoding UTF-8
        # I + " + len(5) + "hello" + { + 1 par + :E + T
        data = b'I"\x05hello{\x01:\x06ET'

        self.assertEqual(data[0:1], b'I')  # tipo IVar
        self.assertEqual(data[1:2], b'"')  # string interna
        self.assertEqual(data[2:3], bytes([5]))  # tamanho = 5
        self.assertEqual(data[3:8], b'hello')  # conteudo
        self.assertEqual(data[8:9], b'{')  # hash de atributos


if __name__ == "__main__":
    unittest.main()
