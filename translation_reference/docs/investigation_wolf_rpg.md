# Investigacao: Formatos Wolf RPG Editor e Smile Game Builder

**Data:** 2026-08-25
**Objetivo:** Avaliar viabilidade de adapter para jogos Wolf RPG/Smile Game Builder com Python stdlib
**Status:** Concluido (pesquisa somente leitura)

---

## 1. Wolf RPG Editor (ウディTA)

### 1.1 Resumo do Formato

Wolf RPG Editor (tambem conhecido como "UdieToo") e uma engine freeware japonesa para criacao de RPGs. Foi criada por SmokingWOLF e traduzida para ingles por vgperson/Widderune.

**Caracteristicas principais:**
- Engine freeware, muito popular no cenario indie/doujin japones
- Suporta V2.x e V3.x (V3 usa LZ4 compression + UTF-8)
- Arquivos compactados em formato proprio DXArchive (extensao `.wolf`)
- Textos em binario (V2: Shift-JIS, V3: UTF-8)
- Codigo aberto: https://silversecond.com/WolfRPGEditor/

### 1.2 Estrutura de Arquivos

```
game_folder/
├── Game.exe               # Executavel do jogo
├── Game.ini               # Configuracoes
├── Data/                  # OU na raiz
│   ├── Data.wolf          # Arquivo principal compactado
│   ├── BasicData.wolf     # Dados basicos
│   ├── MapData.wolf       # Dados de mapas
│   └── SoundData.wolf     # Dados de audio
├── Graph/                 # Graficos
├── Music/                 # Musicas
└── Sound/                 # Sons
```

### 1.3 Formato DXArchive (.wolf)

O formato `.wolf` e baseado no **DXArchive** da biblioteca DxLib:

| Campo | Tipo | Descricao |
|-------|------|-----------|
| Header | 48 bytes | Signature "DX", version, tamanhos |
| Filename table | variable | Nomes dos arquivos internos |
| File table | 64 bytes/entry | Offset, tamanho, atributos |
| Directory table | 32 bytes/entry | Estrutura de diretorios |

**Caracteristicas de criptografia:**
- XOR com chave customizada por jogo (12 bytes para v1-6, 32 bytes para v7, 56 bytes para v8)
- Chave pode ser derivada do executaveis (keyCreate)
- Versoes mais recentes (2020+): v7-v8 com chaves maiores
- Compressao Huffman opcional

### 1.4 Arquivos Internos (.dat / .mps)

Apos descompactar `.wolf`, os arquivos de interesse sao:

| Arquivo | Conteudo | Prioridade |
|---------|----------|------------|
| `*.mps` | Mapas (dialogos, eventos, escolhas) | **Alta** - onde vive a maioria do dialogo |
| `CommonEvent.dat` | Eventos comuns (dialogos compartilhados) | **Alta** |
| `Game.dat` | Database principal (Itens, Habilidades, etc.) | **Alta** |
| `*.dat` (database) | Nomes de itens, habilidades, inimigos, estados | **Media** |
| `Evtext.dat` | Textos de eventos | **Media** |
| `System*.dat` | Mensagens do sistema | **Media** |

### 1.5 Formato dos Arquivos .mps

Baseado na especificacao Kaitai Struct (djytw/wolf-rpg-formats):

```
Header: [0]*10 + "WOLFM" + [0] + version_header + [0]*3
Version: 0x65 (v2) ou 0x66 (v3)
Title: string (nome do mapa)
Map dimensions: width, height
Event count: N
Events: [
  {
    header: 0x6f
    event_id: uint32
    title: string
    page_count: uint32
    pages: [{
      event_commands: [
        { command_code: uint16, parameters: ... }
      ]
    }]
  }
]
```

**Os comandos de evento relevantes para texto:**
- **Code 401**: Show Message (texto de dialogo)
- **Code 405**: Show Scrolling Text
- **Code 102**: Show Choices (escolhas)
- **Code 356**: Plugin Commands (possivel texto)

### 1.6 Versao V2 vs V3

| Aspecto | V2.x | V3.x |
|---------|------|------|
| Encoding | Shift-JIS | UTF-8 |
| Compressao | Nenhuma/Huffman | LZ4 |
| Deteccao | Heuristica (length-prefixed) | Structural parser necessario |
| Complexidade | Simples | Media-Alta |

### 1.7 Tools Existentes

| Ferramenta | Tipo | Linguagem | Notas |
|-----------|------|-----------|-------|
| **UberWolfCli** | Descompactador | .NET (MIT) | Extrai/recompacta .wolf |
| **WolfTL** | Extrator de texto | .NET | Extrai .dat/.mps para JSON |
| **wolf-rpg-formats** | Specs | Kaitai Struct | Formatos documentados |
| **wolftrans_py** | Unpack/repack | Python | Para traducao |
| **WolfText** | Localizacao | Python | Extrai/injeta em mapas |
| **DazedMTLTool** | Pipeline completo | .NET | WolfDawn CLI integrado |
| **RuneTranslate** | Pipeline completo | .NET | Suporta V2+V3 |
| **Translator++** | GUI | Perl | Suporta Wolf RPG |

### 1.8 Dependencias para Adapter Python

**Para descompactar .wolf (DXArchive):**
- Implementacao em Python do decrypt/decode do DXArchive
- Chave XOR precisa ser detectada (pode ser derivada do Game.exe)
- **Complexidade: ALTA** - cada jogo tem chave diferente

**Para ler .mps/.dat internos:**
- Parsing binario com `struct` (stdlib)
- Navegacao de eventos com comandos
- Deteccao de strings por heuristica (V2) ou parser estrutural (V3)
- **Complexidade: MEDIA**

---

## 2. Smile Game Builder (SGB)

### 2.1 Resumo

Smile Game Builder e um criador de jogos JRPG desenvolvido pela SmileBoom. E uma evolucao do Wolf RPG Editor, mas com engine proprio baseado em Unity.

**Relacao com Wolf RPG:**
- Nao e derivado do Wolf RPG (e engine separada)
- Usa formato proprio de pacotes (.sgbpack, .rbpack)
- Possui DLC para exportar como projeto Unity

### 2.2 Formato de Pacotes

| Header | Descricao |
|--------|-----------|
| `YUKARPKG` (59 55 4B 41 52 50 4B 47) | Versao antiga (pseudo-zip) |
| `SGBDAT` (53 47 42 44 41 54 00 01) | Versao nova (XOR encrypted) |
| `BKNPAK` (42 4B 4E 50 41 4B) | Bakin (versao mais recente) |

**Criptografia SGBDAT:**
- Header de 8 bytes substituido por ZIP header para decrypt
- XOR com chave de 16 bytes: `[72,9,20,154,48,169,84,225,0,8,14,9,20,60,66,70]`
- Arquivos internos podem ter segunda camada de criptografia

### 2.3 Exportacao Unity

O DLC "SGB Exporter for Unity" exporta jogos SGB como projetos Unity:
- Pasta `Resource/`: arquivos `.sgr.bytes` com header "YUKAR"
- Catalog.cs le arquivos binarios com signatures por tipo
- Pasta `src/`: codigo C# da engine (MIT license)

### 2.4 Viabilidade

**SGB e significativamente mais dificil que Wolf RPG para adapter stdlib:**
- Criptografia em duas camadas
- Formatos de arquivo menos documentados
- Menos ferramentas open-source para extracao
- Bakin (versao mais recente) usa formato ainda mais opaco

---

## 3. Viabilidade de Adapter com Python stdlib

### 3.1 Wolf RPG - Cenarios

#### Cenario A: Jogos ja descompactados (sem .wolf)
Se o usuario ja descompactou com UberWolfCli ou similar:
- Arquivos .mps/.dat sao binarios brutos com `struct`
- **Viabilidade: ALTA** - parsing binario e viavel com stdlib
- Heuristica para V2: scan por strings length-prefixed
- Parser estrutural para V3: requer LZ4 (nao esta na stdlib Python)

#### Cenario B: Jogos com .wolf (compactados)
- Requer descompactador DXArchive em Python
- Chave XOR por jogo (detectar do Game.exe)
- **Viabilidade: MEDIA** - possivel mas complexo
- Alternativa: chamar UberWolfCli externamente

#### Cenario C: V3.x (LZ4 + UTF-8)
- Requer LZ4 decompression (nao esta na stdlib)
- **Viabilidade: BAIXA com stdlib pura**
- Alternativa: usar `python-lz4` ou delegar para ferramenta externa

### 3.2 Smile Game Builder - Viabilidade

- **Viabilidade: BAIXA** - criptografia dupla, formatos pouco documentados
- Recomendacao: NAO criar adapter para SGB neste momento

### 3.3 Comparacao de Complexidade vs Beneficio

| Motor | Complexidade Adapter | Beneficio Potencial | Recomendacao |
|-------|---------------------|--------------------:|--------------|
| Wolf RPG (ja descompactado) | Media | Alto | **FAZER** (prioridade) |
| Wolf RPG (compactado .wolf) | Alta | Alto | Fazer depois (usar UberWolfCli como sidecar) |
| Wolf RPG V3.x | Muito Alta | Medio | Postergar (LZ4 nao e stdlib) |
| Smile Game Builder | Muito Alta | Medio-Baixo | **NAO FAZER** agora |

---

## 4. Estrategia Recomendada para Adapter Wolf RPG

### 4.1 Fase 1: Extracao de arquivos brutos (ja descompactados)

O adapter deve:
1. **detect()**: Procurar por arquivos .mps/.dat em Data/ ou raiz
2. **extract()**: Ler binarios .mps/.dat, parsear eventos, extrair textos
3. **metadata()**: Contar arquivos, tipos de eventos

**Parsing de .mps (V2):**
```python
import struct

# Heuristica para V2: scan por strings length-prefixed
# Formato: [length:2bytes][string:shift-jis][null]
def scan_strings_v2(data: bytes) -> list[str]:
    strings = []
    pos = 0
    while pos < len(data) - 2:
        length = struct.unpack_from('<H', data, pos)[0]
        if 0 < length < 1000:
            try:
                s = data[pos+2:pos+2+length].decode('cp932')
                if any('\u3040' <= c <= '\u9fff' for c in s):  # CJK check
                    strings.append(s)
            except:
                pass
        pos += 1
    return strings
```

**Parsing de .mps (V3):**
- Requer LZ4 decompression
- Parser estrutural de event commands
- **Recomendacao**: delegar para ferramenta externa ou usar LZ4 condicional

### 4.2 Fase 2: Descompactacao .wolf (opcional)

O adapter pode:
1. Verificar se UberWolfCli esta disponivel no PATH
2. Se sim, chamar como sidecar para descompactar
3. Se nao, instruir o usuario a descompactar manualmente

**Nao implementar decrypt DXArchive em Python stdlib** - complexidade alta, cada jogo tem chave diferente.

### 4.3 Fase 3: Integracao com Scanner

O adapter Wolf RPG deve:
- Usar `TextEntry` do contrato existente
- Category: `wolfrpg_dialogue`, `wolfrpg_choice`, `wolfrpg_system`
- Context: `{"map": "map_name", "event_id": N, "command_code": N}`

---

## 5. Referencias

1. **djytw/wolf-rpg-formats** - https://github.com/djytw/wolf-rpg-formats
   - Especificacoes Kaitai Struct dos formatos .mps, .dat, Game.dat
   - MIT license, documentacao detalhada

2. **RuneTranslate - How to translate Wolf RPG** - https://runetranslate.com/blog/how-to-translate-wolf-rpg-to-english
   - Guia completo de traducao Wolf RPG (V2+V3)
   - Documentacao detalhada de .mps/.dat e extracao

3. **Sinflower/UberWolf** - https://github.com/Sinflower/UberWolf
   - Descompactador GUI/CLI para arquivos .wolf (DXArchive)
   - Suporta todas as versoes, deteccao automatica de chave

4. **DX Archive - XentaxWiki** - https://wiki.xentax.spektr.name/index.php/DX_Archive
   - Documentacao detalhada do formato DXArchive v6-v8
   - Estrutura de header, tabelas, criptografia XOR

5. **Sinflower/WolfTL** - https://github.com/Sinflower/WolfTL
   - Extrator de texto para .dat/.mps, saida em JSON
   - Baseado em wolftrans

6. **UserUnknownFactor/wolftrans_py** - https://github.com/UserUnknownFactor/wolftrans_py
   - Port Python do wolftrans para extracao/reinsercao

7. **Smile Game Builder archives** - http://zenhax.com/viewtopic.php@t=8374.html
   - Documentacao da criptografia SGBDAT (XOR 16 bytes)

---

## 6. Proximos Passos (quando aprovado)

1. Criar modulo `wolfrpg_adapter.py` no TradutorDGames
2. Implementar parsing basico de .mps V2 (heuristica de strings)
3. Implementar parsing basico de .dat V2 (database)
4. Integrar com o scanner existente (adicionar deteccao de .mps/.dat)
5. Testar com amostra real de dados Wolf RPG
6. Avaliar se vale a pena implementar sidecar UberWolfCli
