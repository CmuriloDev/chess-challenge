# Chess Challenge

Software de xadrez para o III Chess Challenge. Roda 100% local: usa o Stockfish como motor de busca e avaliação, e uma camada própria em Python para gestão de tempo, validação de lances, log e interface de linha de comando.

Licença: GPLv3. Veja `DECLARACAO.md` para o projeto-base, o commit de origem e a autoria.

## Instalação

Requer Python 3.10 ou superior.

```
pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File scripts/fetch_stockfish.ps1
```

O segundo comando baixa o binário oficial do Stockfish `sf_19` para `bin/stockfish.exe`. Faça isso antes do evento, com internet. Depois disso nada mais precisa de rede.

Para usar outro binário, aponte a variável de ambiente `STOCKFISH_PATH` ou use `--engine`.

## Uso

```
python -m chess_challenge --color white
python -m chess_challenge --color black
```

Opções:

| Opção | Padrão | Descrição |
| --- | --- | --- |
| `--color` | obrigatório | `white` ou `black` (aceita `brancas`/`pretas`) |
| `--threads` | núcleos lógicos − 2 | threads do Stockfish |
| `--hash` | 8192 | tabela hash em MB |
| `--time` | `15:00` | tempo total da partida |
| `--increment` | 10 | incremento por lance, em segundos |
| `--overhead` | 5 | atraso estimado por lance (anúncio, confirmação e digitação) |
| `--book` | nenhum | livro Polyglot `.bin` |
| `--syzygy` | nenhum | pasta com tablebases Syzygy de até 5 peças |
| `--log-dir` | `logs/` | pasta dos logs |
| `--no-ponder` | desligado | desativa o cálculo durante a vez do adversário |

Ajuste `--threads` e `--hash` à máquina que será usada no evento.

## Protocolo de jogo

1. O programa anuncia o nosso lance em UCI (`>>> ANUNCIE: e2e4`).
2. A equipe adversária repete o lance em voz alta e o relógio físico é acionado.
3. Quando o adversário anunciar o lance dele, digite-o em UCI no terminal (`e7e5`, `e7e8q` para promoção).
4. O programa valida a legalidade, calcula e anuncia o próximo lance.

Se houver divergência, o tabuleiro físico vale. Comandos úteis durante a partida:

| Comando | Efeito |
| --- | --- |
| `clock 12:34` | sincroniza o nosso relógio com o relógio físico |
| `fen <FEN>` | recarrega a posição do tabuleiro físico |
| `undo` | desfaz o último lance |
| `go` | força o cálculo do nosso lance |
| `status` | mostra relógio e vez |
| `board` | mostra o tabuleiro e a FEN |
| `help` | lista os comandos |
| `quit` | encerra |

Empates por tripla repetição e regra dos 50 lances são detectados automaticamente.

## Log

Cada partida gera `logs/game_AAAAMMDD_HHMMSS.log`. Para cada lance nosso são registrados: número do lance, cor, lance em UCI, profundidade, nós, avaliação, variante principal, tempo gasto, origem (`engine`, `book` ou `forced`) e relógio restante. Os lances do adversário também entram no log.

## Gestão de tempo

Descrita em `DECLARACAO.md`. Código em `chess_challenge/timemanager.py`.

## Testes

```
python -m unittest discover -s tests -t .
```

Os testes que usam o Stockfish são pulados se o binário não estiver em `bin/`.
