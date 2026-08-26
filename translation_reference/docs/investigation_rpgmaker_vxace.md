# Investigacao: Formatos de Dados RPG Maker VX/Ace

**Data:** 2026-08-25  
**Objetivo:** Avaliar viabilidade de leitura de arquivos .rvdata/.rvdata2 com Python stdlib  
**Status:** Concluido (pesquisa somente leitura)

---

## 1. Resumo do Formato

### Formato Ruby Marshal v4.8

RPG Maker VX/Ace armazena dados do jogo em arquivos binarios serializados pelo `Marshal` do Ruby. O formato utiliza header de 2 bytes: `\x04\x08` (major=4, minor=8).

| Engine | Extensao | Ruby Version | Encoding Strings |
|--------|----------|-------------|-----------------|
| XP     | .rxdata  | Ruby 1.8    | Shift-JIS (bytes sem tag) |
| VX     | .rvdata  | Ruby 1.8    | Shift-JIS (bytes sem tag) |
| VX Ace | .rvdata2 | Ruby 1.9.2  | Unicode (UTF-8 com tag `E: true`) |

### Type Codes do Marshal 4.8

| Code | Tipo | Descricao |
|------|------|-----------|
| `"`  | String | Byte sequence com tamanho (Fixnum precedente) |
| `i`  | Fixnum | Inteiro compacto |
| `l`  | Bignum | Inteiro grande (sinal + bytes) |
| `[`  | Array  | Lista de objetos |
| `{`  | Hash   | Dicionario chave-valor |
| `o`  | Object | Objeto Ruby com classe + atributos |
| `S`  | Struct | Struct Ruby com classe + atributos |
| `I`  | IVar   | Objeto com instance variables (encoding para strings) |
| `:`  | Symbol | Simbolo Ruby (string interning) |
| `;`  | Symlink| Referencia a symbol ja lido |
| `@`  | Link   | Referencia a objeto ja lido |
| `T`  | True   | Booleano verdadeiro |
| `F`  | False  | Booleano falso |
| `0`  | Nil    | Nulo |
| `f`  | Float  | Ponto flutuante |
| `c`  | Class  | Referencia a classe |
| `m`  | Module | Referencia a modulo |
| `u`  | UserDef| Objeto com serializacao user-defined (`_dump`/`_load`) |
| `U`  | UsrMarshal | Objeto com serializacao user-defined (`marshal_dump`/`marshal_load`) |
| `d`  | Data   | Data wrapper |
| `e`  | Extended | Objeto com modulo estendido |
| `/`  | Regexp | Expressao regular |

### Estrutura Interna dos Objetos Ruby

Os arquivos .rvdata2 armazenam objetos Ruby como `TYPE_OBJECT` (`o`), onde:
- Primeiro: symbol com nome da classe (ex: `RPG::Actor`)
- Segundo: dictionary de atributos (simbolo -> valor)
- Cada atributo e representado como `@nome_atributo` (symbol) seguido do valor

Para strings em VX Ace, o Marshal usa `TYPE_IVAR` (`I`) que envolve a string real e adiciona variaveis de instancia, incluindo `E: true` para indicar encoding UTF-8.

---

## 2. Arquivos com Textos Traduziveis

### Arquivos de Database (Data/*.rvdata2)

| Arquivo | Conteudo Textual | Prioridade |
|---------|-----------------|------------|
| `Actors.rvdata2` | @name, @nickname, @description, @notes | Alta |
| `Items.rvdata2` | @name, @description, @note | Alta |
| `Weapons.rvdata2` | @name, @description, @note | Alta |
| `Armors.rvdata2` | @name, @description, @note | Alta |
| `Skills.rvdata2` | @name, @description, @note | Alta |
| `States.rvdata2` | @name, @description, @note, @message1-4 | Alta |
| `Enemies.rvdata2` | @name | Media |
| `Classes.rvdata2` | @name | Media |
| `System.rvdata2` | @terms (vocabulary), @elements, @weapon_types, etc. | Alta |
| `MapInfos.rvdata2` | @name (nomes dos mapas) | Media |

### Arquivos de Mapa (Data/Map*.rvdata2)

| Conteudo | Tipo | Prioridade |
|----------|------|------------|
| Eventos do mapa (dialogos) | Event code 401, 405 | Alta |
| Escolhas (Show Choices) | Event code 102 | Alta |
| Nome do mapa | MapInfos | Media |
| Comandos de evento com texto | Event code 356 (plugin commands) | Media |

### Common Events (Data/CommonEvents.rvdata2)

| Conteudo | Tipo | Prioridade |
|----------|------|------------|
| Dialogos do evento comum | Event codes 401, 405 | Alta |
| Escolhas | Event code 102 | Alta |

### Scripts (Data/Scripts.rvdata2) - NAO prioridade

- Formato: Array de `[id, nome, script_zlib_compressed]`
- Conteudo comprimido com Zlib apos serializacao Marshal
- Texto UI hard-coded nos scripts fica na lingua original
- **Nao recomendado para varredura automatizada** - requer decodificacao Ruby

### Arquivo Criptografado (Game.rgss3a)

- Arquivo contendo todos os .rvdata2 (criptografado com XOR)
- Header: `RGSSAD\0` + version byte `0x03`
- Chave inicial: `key = read_int32() * 9 + 3`
- Decricao: XOR com chave que evolui `key = (key * 7 + 3) % 2^32`

---

## 3. Python stdlib marshal: INCOMPATIVEL

O modulo `marshal` do Python e **completamente incompativel** com o Marshal do Ruby, apesar de compartilhar o nome.

| Aspecto | Python marshal | Ruby Marshal |
|---------|---------------|-------------|
| Header | Versao do Python (0-5) | `\x04\x08` (4.8) |
| Type codes | `(` tuple, `c` code, `s` string, etc. | `"` string, `o` object, `i` fixnum, etc. |
| Uso principal | .pyc files | Serializacao de objetos Ruby |
| Formato | Undocumented, pode mudar | Documentado, estavel desde 2000 |
| Objetos | Nao suporta classes custom | Suporta qualquer classe Ruby |

Tentativa de usar `marshal.load()` em arquivo .rvdata2 resulta em:
```
ValueError: bad marshal data (unknown type code)
```

**Conclusao: O modulo marshal do Python NAO pode ler arquivos Ruby Marshal.**

---

## 4. Exemplo de Estrutura: Actors.rvdata2

Um arquivo `Actors.rvdata2` contem um array de objetos `RPG::Actor`. Cada ator tem a seguinte estrutura (baseada na definicao Ruby):

```ruby
# Ruby (RPG Maker VX Ace)
class RPG::Actor < RPG::BaseItem
  def initialize
    super                    # herda de BaseItem: @id, @name, @description, @note
    @nickname = ''
    @class_id = 1
    @initial_level = 1
    @max_level = 99
    @character_name = ''
    @character_index = 0
    @face_name = ''
    @face_index = 0
    @equips = [0, 0, 0, 0, 0]
  end
end

class RPG::BaseItem
  def initialize
    @id = 0
    @name = ''
    @description = ''
    @note = ''
  end
end
```

Representacao Marshal esperada (pseudo-estrutura binaria):

```
\x04\x08                    # header Marshal 4.8
[                           # TYPE_ARRAY
  [n elementos]             # Fixnum com tamanho do array
  ... para cada ator:
  I                         # TYPE_IVAR (objeto com atributos)
    o                       # TYPE_OBJECT
      : RPG::Actor          # Symbol com nome da classe
      {                     # TYPE_HASH (atributos)
        : @id           -> i 1       # Fixnum
        : @name         -> I "Akane" # IVar wrapper com E:true (UTF-8)
        : @description  -> I "..."   # IVar wrapper
        : @note         -> I ""      # IVar wrapper
        : @nickname     -> I ""      # IVar wrapper
        : @class_id     -> i 1       # Fixnum
        : @initial_level -> i 1      # Fixnum
        : @max_level    -> i 99      # Fixnum
        : @character_name -> I ""    # IVar wrapper
        : @character_index -> i 0    # Fixnum
        : @face_name    -> I ""      # IVar wrapper
        : @face_index   -> i 0       # Fixnum
        : @equips       -> [0,0,0,0,0] # Array de Fixnums
      }
  ... proximo ator ...
]
```

Cada campo `@name`, `@description`, `@nickname` e `@note` sao strings que podem conter texto em japones que precisa ser traduzido.

---

## 5. Solucoes Existentes em Python

### 5.1 ruby_marshal_reader puro (recomendado)

O arquivo `rpg_extract.py` do repositorio [xi/rpg-extract](https://github.com/xi/rpg-extract) contem uma classe `RubyMarshalReader` completa, escrito em **Python puro** usando apenas stdlib:

- `struct` - leitura de inteiros binarios
- `base64` - decodificacao de bytes
- `zlib` - descompressao (para scripts)
- `json` - saida formatada

**Caracteristicas:**
- Suporta TODOS os type codes do Marshal 4.8
- Lidia com IVar (encoding de strings)
- Lidia com Bignum, Float, Regexp
- Lidia com object links e symlinks
- Suporta descriptografia RGSS3A
- **~200 linhas de codigo, sem dependencias externas**

### 5.2 ruby_marshal (PyPI)

Biblioteca `rubymarshal` por Matthieu Gallet (d9pouces):
- `pip install rubymarshal`
- Leitura e escrita de Marshal 4.8
- Registry de classes para mapear para tipos Python
- Licenca: WTFPL
- **Requer dependencia externa** (nao stdlib)

### 5.3 rvdata2_parser (GitHub)

Repositorio `Inejka/rvdata2_parser`:
- Baseado no ruby_marshal do d9pouces
- Modificado para rvdata2
- Suporte a RPG Maker XP/VX/VX Ace

### 5.4 ChronoMonochrome/rvdata2json

- Converte rvdata2 para JSON/YAML
- Depende de `rubymarshal` (pip)
- Uso: `python rvdata_converter.py <input> <output>`

---

## 6. Recomendacao

### Viabilidade: ALTA com adaptacao

**Estrategia recomendada:**

1. **Extrair o `RubyMarshalReader`** do `rpg_extract.py` como modulo standalone
   - Copiar a classe (~200 linhas)
   - Adaptar para o scanner do TradutorDGames
   - Ja demonstra funcionalidade completa

2. **Para leitura dos arquivos:**
   - Ler header `\x04\x08` e validar versao
   - Usar o reader para deserializar objetos
   - Navegar na estrutura de objeto -> atributos -> strings

3. **Para extracao de textos:**
   - Database files: navegar array de objetos, extrair campos string
   - Map files: navegar eventos, extrair comandos de dialogo (codes 401, 405)
   - Common Events: similar aos mapas
   - System: extrair vocabulary e element names

4. **ParaGame.rgss3a (criptografado):**
   - Implementar descriptografia XOR (ja implementada no rpg_extract.py)
   - Extrair arquivos .rvdata2 para diretorio temporario
   - Processar normalmente

### Dependencias Externas

| Componente | Necessario? | Alternativa |
|-----------|-------------|-------------|
| ruby_marshal (PyPI) | NAO | RubyMarshalReader puro |
| zlib | NAO | stdlib (para scripts) |
| struct | NAO | stdlib |
| json | NAO | stdlib |

**Nenhuma dependencia externa e necessaria.** O reader puro em Python stdlib e suficiente.

### Limitacoes Conhecidas

1. **Scripts.rvdata2**: Conteudo comprimido com zlib. Para extrair scripts completos, e necessario descomprimir cada item do array. Texto UI hard-coded em scripts nao e acessivel via varredura.

2. **XP/VX (nao VX Ace)**: Strings sao Shift-JIS sem tag de encoding. Requer deteccao de encoding adicional.

3. **Object Links**: Objetos podem referenciar outros ja lidos. O reader precisa manter tabela de objetos.

4. **Performance**: Arquivos grandes (muitos mapas) podem ser lentos para parse completo. Considerar leitura seletiva.

---

## 7. Referencias

1. **Ruby Marshal Documentation** - https://docs.ruby-lang.org/en/2.4.0/marshal_rdoc.html
   - Documentacao oficial do formato Marshal 4.8

2. **xi/rpg-extract** - https://github.com/xi/rpg-extract
   - Extractor Python puro para RPG Maker VX Ace com RubyMarshalReader completo

3. **d9pouces/RubyMarshal** - https://github.com/d9pouces/RubyMarshal
   - Biblioteca Python para leitura/escrita de Ruby Marshal (PyPI: rubymarshal)

4. **RuneTranslate** - https://runetranslate.com/engines/rpg-maker-xp-vx-ace
   - Documentacao detalhada dos formatos de arquivo e estrutura de eventos

5. **Ryex/RubyMarshal gist** - https://gist.github.com/Ryex/1a4758ccaa01af496557
   - Implementacao alternativa em Python 2 (referencia para type codes)

6. **CheYoki/externalize-rvdata2** - https://github.com/CheYoki/externalize-rvdata2
   - Extracao de scripts de Scripts.rvdata2

7. **aoitaku/rvdata2 gist** - https://gist.github.com/aoitaku/7822424
   - Conversao rvdata2 <-> YAML com definicoes de classes Ruby

---

## 8. Proximos Passos (quando aprovado)

1. Criar modulo `rvdata_reader.py` no TradutorDGames baseado no RubyMarshalReader
2. Implementar funcoes de extracao de textos por tipo de arquivo
3. Integrar com o scanner existente (adicionar deteccao de .rvdata/.rvdata2)
4. Testar com amostra real de dados VX Ace
5. Implementar descriptografia RGSS3A se necessario
