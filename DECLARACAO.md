# Declaração de credenciamento – III Chess Challenge

## Projeto-base

| Item | Valor |
| --- | --- |
| Projeto | Stockfish |
| Versão | `sf_19` |
| Commit de origem | `edb0d9db6731067ec50ce619ff372b463bc4dd5d` |
| Repositório | https://github.com/official-stockfish/Stockfish |
| Binário | `stockfish-windows-x86-64-universal.exe` (release oficial `sf_19`) |
| Licença | GPLv3 |

O Stockfish é usado sem alterações no seu código-fonte, como processo externo falando o protocolo UCI. Este repositório contém apenas o código de orquestração e é publicado sob GPLv3 (arquivo `LICENSE`).

## Componente de autoria própria: gestão de tempo

A decisão de quanto tempo gastar em cada lance e de quando interromper a busca é implementada neste repositório, não pelo Stockfish.

- `chess_challenge/timemanager.py`: define o orçamento de cada lance (`soft` e `hard`) e a regra de parada dinâmica.
- `chess_challenge/tracker.py`: acompanha a busca em andamento (estabilidade do melhor lance, queda de avaliação, mate encontrado).
- `chess_challenge/clock.py`: modela o nosso relógio considerando incremento, tempo fixo por lance e o tempo de digitação do lance do adversário, que é medido automaticamente pela interface e entra também no planejamento dos lances seguintes.

Resumo do algoritmo:

1. A fase do jogo (material de peças maiores em relação ao inicial) estima quantos lances ainda faltam: de 20 (final) a 45 (abertura).
2. O orçamento base é `(tempo restante − reserva) / lances restantes + (incremento − atraso por lance)`, limitado a 10% do relógio. O atraso por lance é o tempo fixo de anúncio e confirmação mais a média medida da digitação do lance do adversário.
3. O limite máximo (`hard`) é 2,5 vezes o orçamento, limitado a 25% do relógio.
4. Durante a busca, o orçamento é ajustado: estende em até 60% se o melhor lance mudou há pouco ou a avaliação caiu 40 centipeões ou mais; reduz em 40% se o melhor lance está estável e a avaliação não oscila; encerra imediatamente ao encontrar mate a favor.
5. Com menos de 15 segundos no relógio, entra em modo de emergência com lances curtos.

Também é de autoria própria a escolha entre o lance do motor e um lance alternativo (`chess_challenge/game.py`, `_avoid_repetition`): quando a avaliação nos favorece em 30 centipeões ou mais, o programa descarta lances que levariam à tripla repetição ou ao empate pela regra dos 50 lances (e, com vantagem de 100 centipeões ou mais, também a primeira repetição), e refaz a busca restrita aos lances restantes, mantendo o resultado só se ele continuar com pelo menos 15 centipeões a nosso favor.

## Livro de aberturas

Livro Polyglot `komodo.bin` (Salvo Spitaleri, motor Komodo), obtido na coleção https://github.com/ChrisWhittington/polyglot-books e baixado antes do evento por `scripts/fetch_data.py`. Carregado localmente. Limite de 10 meios-lances aplicado em `chess_challenge/book.py`. Material de terceiros, não conta como autoria.

## Tablebases

Syzygy de 3 a 5 peças (WDL e DTZ), obtidas em https://tablebase.lichess.ovh/tables/standard/ e baixadas antes do evento por `scripts/fetch_data.py`. O limite de 5 peças é imposto por `SyzygyProbeLimit=5` e por só existirem esses arquivos em `data/syzygy`. Material de terceiros, não conta como autoria.

## Interface

Interface gráfica local em Tkinter (biblioteca padrão do Python), em `chess_challenge/ui/`. Não usa rede. Modo terminal disponível com `--cli`.

## Dependências

Declaradas em `requirements.txt`: `chess==1.11.2` (python-chess), usada para representação do tabuleiro, validação de lances legais e leitura do livro Polyglot. Nenhuma requisição de rede é feita durante as partidas.

## GPU

Não utilizada.
