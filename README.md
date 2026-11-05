# Chess Challenge

Software de xadrez para o III Chess Challenge. Roda 100% local: usa o Stockfish como motor de busca e avaliação, e uma camada própria em Python para gestão de tempo, validação de lances, log e interface gráfica (com modo terminal opcional).

Licença: GPLv3. Veja `DECLARACAO.md` para o projeto-base, o commit de origem e a autoria.

## Participantes

-Carlos Murilo Nogueira Portela
-Pedro de Carvalho Lima
-Antônio Santana Castelo Branco Bisneto

## Instituição

-Icev

## Instalação

Requer Python 3.10 ou superior.

```
pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File scripts/fetch_stockfish.ps1
```

```
python scripts/fetch_data.py
```

O primeiro script baixa o binário oficial do Stockfish `sf_19` para `bin/stockfish.exe`. O segundo baixa o livro de aberturas `komodo.bin` (`data/book/`) e as tablebases Syzygy de até 5 peças (`data/syzygy/`, cerca de 1 GB). Faça isso antes do evento, com internet. Depois disso nada mais precisa de rede.

O livro e as tablebases são detectados automaticamente em `data/`. Para desligar: `--no-book` e `--no-syzygy`.

Para usar outro binário, aponte a variável de ambiente `STOCKFISH_PATH` ou use `--engine`.

## Uso

```
python -m chess_challenge
python -m chess_challenge --color white
python -m chess_challenge --color black
python -m chess_challenge --cli --color white
```

Sem `--cli`, abre a interface gráfica. Sem `--color`, ela pergunta a cor do nosso lado. Com `--cli`, roda no terminal e `--color` é obrigatório.

## Interface gráfica

- Tabuleiro com o último lance destacado e uma seta verde indicando o lance que devemos anunciar.
- Faixa grande com o lance em UCI para anunciar em voz alta e a notação algébrica ao lado.
- Nosso relógio, tempo de busca ao vivo e há quanto tempo o adversário está pensando.
- Avaliação do nosso ponto de vista, barra de vantagem, profundidade, nós, nós por segundo e variante principal em tempo real. Enquanto o adversário pensa, mostra a análise do pondering.
- Lance do adversário: digite em UCI (`e7e5`, `e7e8q`) e pressione Enter, ou clique na peça e na casa de destino no tabuleiro. Promoções abrem um seletor.
- Lista de lances, desfazer, carregar posição por FEN e calcular agora.
- Indicadores de livro de aberturas, tablebases, threads, hash e caminho do log.

Opções:

| Opção | Padrão | Descrição |
| --- | --- | --- |
| `--color` | pergunta na interface | `white` ou `black` (aceita `brancas`/`pretas`); obrigatório com `--cli` |
| `--threads` | núcleos lógicos − 2 | threads do Stockfish |
| `--hash` | 8192 | tabela hash em MB |
| `--time` | `15:00` | tempo total da partida |
| `--increment` | 10 | incremento por lance, em segundos |
| `--overhead` | 2 | tempo fixo por lance para ouvir, confirmar e anunciar |
| `--entry-estimate` | 3 | digitação estimada até a primeira medição, em segundos |
| `--book` | `data/book/komodo.bin` | livro Polyglot `.bin` |
| `--no-book` | desligado | não usar livro |
| `--syzygy` | `data/syzygy` | pasta com tablebases Syzygy de até 5 peças |
| `--no-syzygy` | desligado | não usar tablebases |
| `--cli` | desligado | modo terminal em vez da interface gráfica |
| `--log-dir` | `logs/` | pasta dos logs |
| `--no-ponder` | desligado | desativa o cálculo durante a vez do adversário |

Ajuste `--threads` e `--hash` à máquina que será usada no evento.

## Protocolo de jogo

1. O programa anuncia o nosso lance em UCI (`ANUNCIE: e2e4`).
2. A equipe adversária repete o lance em voz alta e o relógio físico é acionado.
3. Quando o adversário anunciar o lance dele, digite-o em UCI (`e7e5`, `e7e8q` para promoção) ou clique no tabuleiro.
4. O programa valida a legalidade, calcula e anuncia o próximo lance.

Se houver divergência, o tabuleiro físico vale.

## Relógio automático

Não é preciso sincronizar o relógio. O programa mede sozinho o tempo que a equipe leva para inserir cada lance do adversário (da primeira tecla ou clique até o Enter) e desconta esse tempo do nosso relógio, junto com a busca e o tempo fixo `--overhead`, somando o incremento. A média das últimas medições também entra no planejamento do tempo dos próximos lances. No modo terminal, que não vê as teclas, usa-se `--entry-estimate`. O botão "Ajustar relógio" (ou o comando `clock` no terminal) existe só como correção opcional.

## Comandos do modo terminal

| Comando | Efeito |
| --- | --- |
| `clock 12:34` | corrige o nosso relógio |
| `fen <FEN>` | recarrega a posição do tabuleiro físico |
| `undo` | desfaz o último lance |
| `go` | força o cálculo do nosso lance |
| `status` | mostra relógio e vez |
| `board` | mostra o tabuleiro e a FEN |
| `help` | lista os comandos |
| `quit` | encerra |

Tripla repetição, regra dos 50 lances e suas versões automáticas (quíntupla repetição e 75 lances) não encerram a partida no programa: ele mostra um aviso uma única vez, registra no log e continua jogando, já que o tabuleiro físico e o árbitro é que decidem o resultado. O programa só para em xeque-mate, afogamento e material insuficiente.

## Log

Cada partida gera `logs/game_AAAAMMDD_HHMMSS.log`, tanto na interface quanto no terminal. Para cada lance nosso são registrados: número do lance, cor, lance em UCI, profundidade, nós, avaliação, variante principal, tempo gasto, origem (`engine`, `book` ou `forced`) e relógio restante. Os lances do adversário também entram no log.

## Gestão de tempo

Descrita em `DECLARACAO.md`. Código em `chess_challenge/timemanager.py`.

## Testes

```
python -m unittest discover -s tests -t .
```

Os testes que usam o Stockfish são pulados se o binário não estiver em `bin/`.
