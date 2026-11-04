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
- `chess_challenge/clock.py`: modela o nosso relógio considerando incremento e o atraso do protocolo verbal.

Resumo do algoritmo:

1. A fase do jogo (material de peças maiores em relação ao inicial) estima quantos lances ainda faltam: de 20 (final) a 45 (abertura).
2. O orçamento base é `(tempo restante − reserva) / lances restantes + (incremento − atraso por lance)`, limitado a 10% do relógio. O atraso por lance representa o tempo de anúncio, confirmação e digitação do lance do adversário.
3. O limite máximo (`hard`) é 2,5 vezes o orçamento, limitado a 25% do relógio.
4. Durante a busca, o orçamento é ajustado: estende em até 60% se o melhor lance mudou há pouco ou a avaliação caiu 40 centipeões ou mais; reduz em 40% se o melhor lance está estável e a avaliação não oscila; encerra imediatamente ao encontrar mate a favor.
5. Com menos de 15 segundos no relógio, entra em modo de emergência com lances curtos.

## Livro de aberturas

Opcional. Arquivo Polyglot `.bin` baixado antes do evento e carregado localmente com `--book`. Limite de 10 meios-lances aplicado em `chess_challenge/book.py`. Não é contado como autoria.

## Tablebases

Opcional. Syzygy de até 5 peças, carregadas localmente com `--syzygy`. O limite é imposto por `SyzygyProbeLimit=5`. Não são contadas como autoria.

## Dependências

Declaradas em `requirements.txt`: `chess==1.11.2` (python-chess), usada para representação do tabuleiro, validação de lances legais e leitura do livro Polyglot. Nenhuma requisição de rede é feita durante as partidas.

## GPU

Não utilizada.
