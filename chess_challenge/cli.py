import argparse
from pathlib import Path

import chess

from .clock import parse_clock
from .config import Config
from .game import Game, IllegalMove
from .session import open_game

HELP = """Comandos:
  <lance>         lance do adversario em UCI (e2e4, g1f3, e7e8q)
  go              forca o calculo do nosso lance
  clock <tempo>   sincroniza o nosso relogio (ex.: clock 12:34 ou clock 754)
  status          mostra relogio e vez
  board           mostra o tabuleiro e a FEN
  undo            desfaz o ultimo lance
  fen <FEN>       carrega uma posicao (tabuleiro fisico e a fonte da verdade)
  help            mostra esta ajuda
  quit            encerra"""

COLORS = {
    "white": chess.WHITE,
    "brancas": chess.WHITE,
    "w": chess.WHITE,
    "black": chess.BLACK,
    "pretas": chess.BLACK,
    "b": chess.BLACK,
}


def parse_color(text: str) -> chess.Color:
    try:
        return COLORS[text.strip().lower()]
    except KeyError:
        raise argparse.ArgumentTypeError("use white/black (ou brancas/pretas)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chess_challenge")
    parser.add_argument("--color", type=parse_color)
    parser.add_argument("--cli", action="store_true")
    parser.add_argument("--engine", type=Path)
    parser.add_argument("--threads", type=int)
    parser.add_argument("--hash", type=int, dest="hash_mb")
    parser.add_argument("--book", type=Path)
    parser.add_argument("--no-book", action="store_true")
    parser.add_argument("--syzygy", type=Path)
    parser.add_argument("--no-syzygy", action="store_true")
    parser.add_argument("--log-dir", type=Path)
    parser.add_argument("--time", default="15:00")
    parser.add_argument("--increment", type=float, default=10.0)
    parser.add_argument("--overhead", type=float, default=2.0)
    parser.add_argument("--entry-estimate", type=float, default=3.0)
    parser.add_argument("--no-ponder", action="store_true")
    return parser


def config_from_args(args: argparse.Namespace) -> Config:
    config = Config(
        total_time=parse_clock(args.time),
        increment=args.increment,
        move_overhead=args.overhead,
        entry_estimate=args.entry_estimate,
        ponder=not args.no_ponder,
    )
    if args.no_book:
        config.book_path = None
    elif args.book is not None:
        config.book_path = args.book
    if args.no_syzygy:
        config.syzygy_path = None
    elif args.syzygy is not None:
        config.syzygy_path = args.syzygy
    if args.engine is not None:
        config.engine_path = args.engine
    if args.threads is not None:
        config.threads = args.threads
    if args.hash_mb is not None:
        config.hash_mb = args.hash_mb
    if args.log_dir is not None:
        config.log_dir = args.log_dir
    return config


def play_turn(game: Game) -> None:
    print("pensando...", flush=True)
    result = game.choose_move()
    print()
    print(f"  >>> ANUNCIE: {result.move.uci()}   ({result.san})")
    print(
        f"      origem={result.source} prof={result.depth} aval={result.score} "
        f"tempo={result.elapsed:.1f}s relogio={game.clock}"
    )
    print()


def report_outcome(game: Game) -> bool:
    outcome = game.outcome()
    if outcome is None:
        return False
    text = f"Fim de jogo: {outcome.termination.name} {outcome.result()}"
    print(text)
    game.logger.event(text)
    return True


def handle(game: Game, text: str) -> bool:
    command, _, argument = text.partition(" ")
    command = command.lower()
    if command in ("quit", "exit", "sair"):
        return False
    if command == "help":
        print(HELP)
    elif command == "board":
        print(game.board)
        print(game.board.fen())
    elif command == "status":
        vez = "nossa" if game.our_turn else "do adversario"
        print(f"relogio={game.clock} vez={vez} lance={game.board.fullmove_number}")
    elif command == "clock":
        try:
            game.clock.set(parse_clock(argument))
        except ValueError:
            print("Tempo invalido. Use mm:ss ou segundos.")
        else:
            print(f"relogio={game.clock}")
    elif command == "undo":
        undone = game.undo()
        print(f"desfeito: {undone.uci()}" if undone else "nada para desfazer")
    elif command == "fen":
        try:
            game.set_fen(argument)
        except IllegalMove:
            print("FEN invalida.")
        else:
            print(game.board)
            if game.our_turn and game.outcome() is None:
                play_turn(game)
    elif command == "go":
        if game.our_turn:
            play_turn(game)
        else:
            print("Nao e a nossa vez.")
    else:
        play_opponent(game, text)
    return True


def play_opponent(game: Game, text: str) -> None:
    if game.our_turn:
        print("Nao e a vez do adversario. Use 'go' para calcular o nosso lance.")
        return
    try:
        game.apply_opponent_move(text)
    except IllegalMove:
        print(f"Lance ilegal ou invalido: {text}. Confira o tabuleiro fisico.")
        return
    if game.outcome() is None:
        play_turn(game)


def loop(game: Game) -> None:
    if game.our_turn:
        play_turn(game)
    while not report_outcome(game):
        try:
            text = input("adversario> " if not game.our_turn else "voce> ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if text and not handle(game, text):
            return


def run_cli(config: Config, color: chess.Color) -> int:
    try:
        with open_game(config, color) as game:
            print(f"{game.engine.name} | log: {game.logger.path}")
            print("Digite 'help' para ver os comandos.")
            loop(game)
    except FileNotFoundError as error:
        print(error)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = config_from_args(args)
    if args.cli:
        if args.color is None:
            parser.error("--color e obrigatorio com --cli")
        return run_cli(config, args.color)
    from .ui.app import run_gui

    return run_gui(config, args.color)
