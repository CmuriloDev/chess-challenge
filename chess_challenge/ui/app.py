import ctypes
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox, simpledialog

import chess

from ..clock import parse_clock
from ..config import Config
from ..engine import LiveInfo, SearchResult
from ..game import Game, IllegalMove
from ..session import open_game
from .board_view import BoardView
from .format import (
    eval_fraction,
    format_clock,
    format_count,
    move_list_rows,
    orient_score,
    pv_text,
    score_to_cp,
)

BG = "#1e1f22"
PANEL = "#2b2d31"
FIELD = "#383a40"
TEXT = "#e6e6e6"
MUTED = "#9ca3af"
ACCENT = "#22c55e"
WARN = "#f59e0b"
DANGER = "#ef4444"
BUTTON = "#3b3d44"
BUTTON_ACTIVE = "#4b4e57"
POLL_MS = 50
PONDER_POLL_TICKS = 10
MESSAGE_MS = 7000
PROMOTIONS = (("Dama", "q"), ("Torre", "r"), ("Bispo", "b"), ("Cavalo", "n"))


def run_search(game: Game, events: queue.Queue, board: chess.Board) -> None:
    def on_info(live: LiveInfo) -> None:
        events.put(("live", live, pv_text(board, live.pv)))

    try:
        result = game.choose_move(on_info)
    except Exception as error:
        events.put(("error", error))
        return
    events.put(("done", result, pv_text(board, result.pv)))


def enable_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass


def choose_color(root: tk.Tk) -> chess.Color | None:
    choice: list[chess.Color] = []
    dialog = tk.Toplevel(root)
    dialog.title("Chess Challenge")
    dialog.configure(bg=BG, padx=40, pady=30)
    dialog.resizable(False, False)
    tk.Label(
        dialog, text="Qual a cor do nosso lado?", bg=BG, fg=TEXT, font=("Segoe UI", 16, "bold")
    ).pack(pady=(0, 20))

    def pick(color: chess.Color) -> None:
        choice.append(color)
        dialog.destroy()

    row = tk.Frame(dialog, bg=BG)
    row.pack()
    for label, color, bg, fg in (
        ("Brancas", chess.WHITE, "#f1f1f1", "#111111"),
        ("Pretas", chess.BLACK, "#111111", "#f1f1f1"),
    ):
        tk.Button(
            row,
            text=label,
            width=12,
            font=("Segoe UI", 14, "bold"),
            bg=bg,
            fg=fg,
            relief="flat",
            padx=10,
            pady=10,
            command=lambda c=color: pick(c),
        ).pack(side="left", padx=10)
    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    dialog.grab_set()
    root.wait_window(dialog)
    return choice[0] if choice else None


class App:
    def __init__(self, root: tk.Tk, game: Game) -> None:
        self.root = root
        self.game = game
        self.flipped = game.color == chess.BLACK
        self.events: queue.Queue[tuple] = queue.Queue()
        self.thinking = False
        self.think_started = 0.0
        self.think_board = game.board.copy()
        self.waiting_since = time.perf_counter()
        self.first_input: float | None = None
        self.selected: chess.Square | None = None
        self.announced: chess.Move | None = None
        self.last_san = ""
        self.closed = False
        self.ponder_tick = 0
        self.message_job: str | None = None
        self.poll_job: str | None = None
        self.worker: threading.Thread | None = None
        self.scale = max(1.0, root.winfo_fpixels("1i") / 96.0)
        self._build()
        self.refresh()
        self.poll_job = self.root.after(POLL_MS, self.poll)
        if game.our_turn:
            self.start_thinking()
        else:
            self.focus_entry()

    def px(self, value: float) -> int:
        return int(value * self.scale)

    def _build(self) -> None:
        root = self.root
        root.title("Chess Challenge")
        root.configure(bg=BG)
        screen = root.winfo_screenheight()
        board_size = max(self.px(440), min(self.px(700), screen - self.px(270)))
        left = tk.Frame(root, bg=BG)
        left.grid(row=0, column=0, padx=(16, 8), pady=16, sticky="n")
        self.board_view = BoardView(
            left, size=board_size, margin=self.px(26), on_click=self.on_square
        )
        self.board_view.pack()
        banner = tk.Frame(left, bg=PANEL)
        banner.pack(fill="x", pady=(10, 0))
        self.banner_title = tk.Label(
            banner, text="", bg=PANEL, fg=MUTED, font=("Segoe UI", 11, "bold"), anchor="w"
        )
        self.banner_title.pack(fill="x", padx=14, pady=(8, 0))
        self.banner_move = tk.Label(
            banner, text="", bg=PANEL, fg=ACCENT, font=("Segoe UI", 30, "bold"), anchor="w"
        )
        self.banner_move.pack(fill="x", padx=14, pady=(0, 8))

        right = tk.Frame(root, bg=BG)
        right.grid(row=0, column=1, padx=(8, 16), pady=16, sticky="n")
        width = self.px(400)

        header = tk.Frame(right, bg=BG)
        header.pack(fill="x")
        side = "brancas" if self.game.color == chess.WHITE else "pretas"
        tk.Label(
            header,
            text=f"{self.game.engine.name}  |  jogamos de {side}",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left")
        tk.Label(header, text="OFFLINE", bg=ACCENT, fg="#06210f", font=("Segoe UI", 9, "bold"), padx=8).pack(
            side="right"
        )

        clock_card = tk.Frame(right, bg=PANEL)
        clock_card.pack(fill="x", pady=(10, 0))
        tk.Label(
            clock_card, text="NOSSO RELOGIO", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", padx=14, pady=(8, 0))
        self.clock_label = tk.Label(
            clock_card, text="", bg=PANEL, fg=TEXT, font=("Consolas", 40, "bold")
        )
        self.clock_label.pack(anchor="w", padx=14)
        self.timer_label = tk.Label(
            clock_card, text="", bg=PANEL, fg=MUTED, font=("Segoe UI", 11), anchor="w"
        )
        self.timer_label.pack(fill="x", padx=14, pady=(0, 8))

        eval_card = tk.Frame(right, bg=PANEL)
        eval_card.pack(fill="x", pady=(10, 0))
        top = tk.Frame(eval_card, bg=PANEL)
        top.pack(fill="x", padx=14, pady=(8, 0))
        tk.Label(top, text="AVALIACAO", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(
            side="left"
        )
        self.source_label = tk.Label(top, text="", bg=PANEL, fg=MUTED, font=("Segoe UI", 9))
        self.source_label.pack(side="right")
        self.eval_label = tk.Label(
            eval_card, text="--", bg=PANEL, fg=TEXT, font=("Consolas", 28, "bold"), anchor="w"
        )
        self.eval_label.pack(fill="x", padx=14)
        self.bar = tk.Canvas(eval_card, width=width - 28, height=self.px(14), bg=DANGER, highlightthickness=0)
        self.bar.pack(padx=14, pady=(2, 6))
        self.bar_width = width - 28
        self.bar_ours = self.bar.create_rectangle(0, 0, self.bar_width // 2, self.px(14), fill=ACCENT, width=0)
        self.stats_label = tk.Label(
            eval_card, text="", bg=PANEL, fg=MUTED, font=("Segoe UI", 10), anchor="w"
        )
        self.stats_label.pack(fill="x", padx=14)
        self.pv_label = tk.Label(
            eval_card,
            text="",
            bg=PANEL,
            fg=TEXT,
            font=("Consolas", 10),
            anchor="w",
            justify="left",
            wraplength=width - 28,
        )
        self.pv_label.pack(fill="x", padx=14, pady=(2, 8))

        input_card = tk.Frame(right, bg=PANEL)
        input_card.pack(fill="x", pady=(10, 0))
        tk.Label(
            input_card,
            text="LANCE DO ADVERSARIO (UCI) OU CLIQUE NO TABULEIRO",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=14, pady=(8, 4))
        row = tk.Frame(input_card, bg=PANEL)
        row.pack(fill="x", padx=14, pady=(0, 8))
        self.entry = tk.Entry(
            row,
            font=("Consolas", 22, "bold"),
            bg=FIELD,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            width=8,
        )
        self.entry.pack(side="left", ipady=6)
        self.entry.bind("<Return>", lambda _event: self.submit(self.entry.get()))
        self.entry.bind("<Key>", self.on_key)
        self.confirm = tk.Button(
            row,
            text="Confirmar",
            font=("Segoe UI", 12, "bold"),
            bg=ACCENT,
            fg="#06210f",
            activebackground="#4ade80",
            relief="flat",
            padx=16,
            command=lambda: self.submit(self.entry.get()),
        )
        self.confirm.pack(side="left", padx=(10, 0), ipady=6)
        self.message = tk.Label(
            input_card, text="", bg=PANEL, fg=WARN, font=("Segoe UI", 10), anchor="w", wraplength=width - 28, justify="left"
        )
        self.message.pack(fill="x", padx=14, pady=(0, 8))

        list_card = tk.Frame(right, bg=PANEL)
        list_card.pack(fill="x", pady=(10, 0))
        tk.Label(list_card, text="LANCES", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(
            anchor="w", padx=14, pady=(8, 2)
        )
        holder = tk.Frame(list_card, bg=PANEL)
        holder.pack(fill="x", padx=14, pady=(0, 8))
        self.moves = tk.Text(
            holder,
            height=7,
            width=1,
            bg=FIELD,
            fg=TEXT,
            font=("Consolas", 11),
            relief="flat",
            state="disabled",
            wrap="none",
        )
        scroll = tk.Scrollbar(holder, command=self.moves.yview)
        self.moves.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.moves.pack(side="left", fill="x", expand=True)

        buttons = tk.Frame(right, bg=BG)
        buttons.pack(fill="x", pady=(10, 0))
        for label, command in (
            ("Desfazer", self.undo),
            ("Posicao (FEN)", self.load_fen),
            ("Calcular agora", self.go_now),
            ("Ajustar relogio", self.adjust_clock),
        ):
            tk.Button(
                buttons,
                text=label,
                font=("Segoe UI", 10),
                bg=BUTTON,
                fg=TEXT,
                activebackground=BUTTON_ACTIVE,
                activeforeground=TEXT,
                relief="flat",
                padx=8,
                pady=5,
                command=command,
            ).pack(side="left", padx=(0, 6))

        config = self.game.config
        book = config.book_path.name if config.book_path else "nenhum"
        tablebase = f"{config.tablebase_max_pieces} pecas" if config.syzygy_path else "nenhuma"
        footer = (
            f"{config.threads} threads  |  hash {config.hash_mb} MB  |  livro: {book}  |  "
            f"tablebases: {tablebase}\nlog: {self.game.logger.path}"
        )
        tk.Label(
            right, text=footer, bg=BG, fg=MUTED, font=("Segoe UI", 8), anchor="w", justify="left", wraplength=width
        ).pack(fill="x", pady=(10, 0))

        root.protocol("WM_DELETE_WINDOW", self.close)

    def focus_entry(self) -> None:
        self.entry.configure(state="normal")
        self.entry.focus_set()

    def notify(self, text: str, color: str = WARN) -> None:
        self.message.configure(text=text, fg=color)
        if self.message_job is not None:
            self.root.after_cancel(self.message_job)
        self.message_job = self.root.after(MESSAGE_MS, lambda: self.message.configure(text=""))

    def refresh(self) -> None:
        board = self.game.board
        last = board.peek() if board.move_stack else None
        self.board_view.render(board, self.flipped, last, self.announced, self.selected)
        self.clock_label.configure(text=format_clock(self.game.clock.remaining))
        self.update_moves()
        self.update_banner()
        self.warn_draw()

    def update_moves(self) -> None:
        self.moves.configure(state="normal")
        self.moves.delete("1.0", "end")
        for number, white, black in move_list_rows(self.game.board):
            self.moves.insert("end", f"{number:>3}. {white:<8}{black}\n")
        self.moves.see("end")
        self.moves.configure(state="disabled")

    def update_banner(self) -> None:
        outcome = self.game.outcome()
        if outcome is not None:
            self.banner_title.configure(text="FIM DE JOGO", fg=WARN)
            self.banner_move.configure(
                text=f"{outcome.result()}  {outcome.termination.name}", fg=WARN, font=("Segoe UI", 20, "bold")
            )
        elif self.thinking:
            self.banner_title.configure(text="CALCULANDO", fg=WARN)
            self.banner_move.configure(text="Pensando...", fg=WARN, font=("Segoe UI", 30, "bold"))
        elif self.announced is not None and not self.game.our_turn:
            san = self.last_san
            self.banner_title.configure(text="ANUNCIE EM VOZ ALTA (UCI)", fg=ACCENT)
            self.banner_move.configure(
                text=f"{self.announced.uci()}   ({san})", fg=ACCENT, font=("Segoe UI", 30, "bold")
            )
        else:
            self.banner_title.configure(text="VEZ DO ADVERSARIO", fg=MUTED)
            self.banner_move.configure(text="Digite o lance", fg=MUTED, font=("Segoe UI", 30, "bold"))

    def show_eval(self, score: str, centipawns: int, depth: int, nodes: int, nps: int, pv: str, label: str) -> None:
        color = self.game.color
        ours = orient_score(score, color)
        our_cp = centipawns if color == chess.WHITE else -centipawns
        self.eval_label.configure(text=ours, fg=ACCENT if our_cp > 30 else (DANGER if our_cp < -30 else TEXT))
        self.bar.coords(self.bar_ours, 0, 0, int(self.bar_width * eval_fraction(our_cp)), self.px(14))
        self.stats_label.configure(
            text=f"prof {depth}   |   {format_count(nodes)} nos   |   {format_count(nps)} n/s"
        )
        self.pv_label.configure(text=pv)
        self.source_label.configure(text=label)

    def clear_eval(self, label: str) -> None:
        self.eval_label.configure(text="--", fg=TEXT)
        self.bar.coords(self.bar_ours, 0, 0, self.bar_width // 2, self.px(14))
        self.stats_label.configure(text="")
        self.pv_label.configure(text="")
        self.source_label.configure(text=label)

    def start_thinking(self) -> None:
        if self.thinking or self.game.outcome() is not None:
            return
        self.thinking = True
        self.think_started = time.perf_counter()
        self.think_board = self.game.board.copy()
        self.announced = None
        self.selected = None
        self.entry.delete(0, "end")
        self.entry.configure(state="disabled")
        self.clear_eval("calculando")
        self.refresh()
        self.worker = threading.Thread(
            target=run_search,
            args=(self.game, self.events, self.think_board.copy()),
            daemon=True,
        )
        self.worker.start()

    def poll(self) -> None:
        if self.closed:
            return
        try:
            while True:
                event = self.events.get_nowait()
                self.handle_event(event)
        except queue.Empty:
            pass
        self.update_timers()
        self.poll_job = self.root.after(POLL_MS, self.poll)

    def handle_event(self, event: tuple) -> None:
        kind = event[0]
        if kind == "live":
            live, pv = event[1], event[2]
            self.show_eval(live.score, live.centipawns, live.depth, live.nodes, live.nps, pv, "calculando")
        elif kind == "done":
            self.finish_thinking(event[1], event[2])
        elif kind == "error":
            self.thinking = False
            self.notify(f"Erro no motor: {event[1]}", DANGER)
            self.focus_entry()

    def finish_thinking(self, result: SearchResult, pv: str) -> None:
        self.thinking = False
        self.announced = result.move
        self.last_san = result.san
        self.waiting_since = time.perf_counter()
        self.first_input = None
        nps = int(result.nodes / max(result.elapsed, 1e-3))
        source = {"book": "livro de aberturas", "forced": "lance unico", "engine-norep": "motor (evitou repeticao)"}.get(result.source, "motor")
        score = result.score
        if score != "n/a":
            self.show_eval(score, score_to_cp(score), result.depth, result.nodes, nps, pv, source)
        else:
            self.clear_eval(source)
            self.pv_label.configure(text=pv)
            self.stats_label.configure(text=f"{result.elapsed:.1f}s")
        self.refresh()
        self.finish_if_over()
        self.focus_entry()

    def warn_draw(self) -> None:
        notice = self.game.new_draw_notice()
        if notice is not None:
            self.notify(
                f"Aviso: {notice}. O arbitro pode declarar empate, mas o programa continua jogando.", WARN
            )

    def finish_if_over(self) -> None:
        outcome = self.game.outcome()
        if outcome is None:
            return
        text = f"Fim de jogo: {outcome.termination.name} {outcome.result()}"
        self.game.logger.event(text)
        self.entry.configure(state="disabled")
        self.update_banner()

    def update_timers(self) -> None:
        now = time.perf_counter()
        if self.thinking:
            self.clock_label.configure(text=format_clock(self.game.clock.remaining - (now - self.think_started)))
            self.timer_label.configure(text=f"pensando ha {now - self.think_started:.1f}s", fg=WARN)
            return
        self.clock_label.configure(text=format_clock(self.game.clock.remaining))
        if self.game.outcome() is not None:
            self.timer_label.configure(text="")
            return
        if not self.game.our_turn:
            waited = now - self.waiting_since
            expected = self.game.clock.expected_entry()
            self.timer_label.configure(
                text=f"adversario pensando ha {format_clock(waited)}   |   digitacao media {expected:.1f}s",
                fg=MUTED,
            )
            self.ponder_tick += 1
            if self.ponder_tick >= PONDER_POLL_TICKS:
                self.ponder_tick = 0
                self.show_ponder()

    def show_ponder(self) -> None:
        board = self.game.ponder_board
        if board is None:
            return
        live = self.game.engine.ponder_live()
        if live is None:
            return
        self.show_eval(
            live.score,
            live.centipawns,
            live.depth,
            live.nodes,
            live.nps,
            pv_text(board, live.pv),
            "analisando a resposta provavel",
        )

    def on_key(self, event: tk.Event) -> None:
        if self.first_input is None and event.char and event.char.isprintable():
            self.first_input = time.perf_counter()

    def on_square(self, square: chess.Square) -> None:
        game = self.game
        if self.thinking or game.outcome() is not None or game.our_turn:
            return
        if self.first_input is None:
            self.first_input = time.perf_counter()
        board = game.board
        piece = board.piece_at(square)
        opponent_piece = piece is not None and piece.color != game.color
        if self.selected is None:
            if opponent_piece:
                self.selected = square
        elif square == self.selected:
            self.selected = None
        elif opponent_piece:
            self.selected = square
        else:
            move = chess.Move(self.selected, square)
            moving = board.piece_at(self.selected)
            if moving is not None and moving.piece_type == chess.PAWN and chess.square_rank(square) in (0, 7):
                letter = self.ask_promotion()
                if letter is None:
                    self.selected = None
                    self.refresh()
                    return
                move = chess.Move(self.selected, square, chess.Piece.from_symbol(letter).piece_type)
            self.submit(move.uci())
            return
        self.refresh()

    def ask_promotion(self) -> str | None:
        choice: list[str] = []
        dialog = tk.Toplevel(self.root)
        dialog.title("Promocao")
        dialog.configure(bg=BG, padx=24, pady=20)
        dialog.resizable(False, False)
        tk.Label(dialog, text="Promover para:", bg=BG, fg=TEXT, font=("Segoe UI", 13, "bold")).pack(pady=(0, 12))
        row = tk.Frame(dialog, bg=BG)
        row.pack()

        def pick(letter: str) -> None:
            choice.append(letter)
            dialog.destroy()

        for label, letter in PROMOTIONS:
            tk.Button(
                row, text=label, width=8, bg=BUTTON, fg=TEXT, relief="flat", font=("Segoe UI", 11),
                command=lambda value=letter: pick(value),
            ).pack(side="left", padx=4, ipady=4)
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)
        return choice[0] if choice else None

    def submit(self, text: str) -> None:
        game = self.game
        text = text.strip()
        if self.thinking or game.outcome() is not None or not text:
            return
        if game.our_turn:
            self.notify("Nao e a vez do adversario. Use 'Calcular agora' para forcar o nosso lance.")
            return
        latency = None if self.first_input is None else time.perf_counter() - self.first_input
        self.selected = None
        try:
            game.apply_opponent_move(text, latency)
        except IllegalMove as error:
            self.first_input = None
            self.entry.delete(0, "end")
            extra = f" ({error.hint})" if error.hint else ""
            self.notify(f"Lance ilegal ou invalido: {text}{extra}. Confira o tabuleiro fisico.", DANGER)
            self.refresh()
            return
        self.first_input = None
        self.entry.delete(0, "end")
        self.announced = None
        self.refresh()
        if game.outcome() is not None:
            self.finish_if_over()
        else:
            self.start_thinking()

    def undo(self) -> None:
        if self.thinking:
            return
        undone = self.game.undo()
        self.announced = None
        self.selected = None
        self.refresh()
        if undone is None:
            self.notify("Nada para desfazer.")
        else:
            self.notify(f"Desfeito: {undone.uci()}. Use 'Calcular agora' se for a nossa vez.", MUTED)

    def load_fen(self) -> None:
        if self.thinking:
            return
        fen = simpledialog.askstring("Posicao", "Cole a FEN do tabuleiro fisico:", parent=self.root)
        if not fen:
            return
        try:
            self.game.set_fen(fen)
        except IllegalMove:
            self.notify("FEN invalida.", DANGER)
            return
        self.announced = None
        self.selected = None
        self.refresh()
        if self.game.our_turn:
            self.start_thinking()

    def go_now(self) -> None:
        if self.thinking:
            return
        if not self.game.our_turn:
            self.notify("Nao e a nossa vez.")
            return
        self.start_thinking()

    def adjust_clock(self) -> None:
        text = simpledialog.askstring("Relogio", "Tempo restante (mm:ss ou segundos):", parent=self.root)
        if not text:
            return
        try:
            self.game.clock.set(parse_clock(text))
        except ValueError:
            self.notify("Tempo invalido.", DANGER)
            return
        self.refresh()

    def shutdown(self) -> None:
        self.closed = True
        for job in (self.poll_job, self.message_job):
            if job is not None:
                try:
                    self.root.after_cancel(job)
                except tk.TclError:
                    pass
        self.poll_job = None
        self.message_job = None

    def join_worker(self, timeout: float = 10.0) -> None:
        if self.worker is not None and self.worker.is_alive():
            self.worker.join(timeout)

    def close(self) -> None:
        self.shutdown()
        self.root.destroy()


def run_gui(config: Config, color: chess.Color | None) -> int:
    enable_dpi_awareness()
    root = tk.Tk()
    root.withdraw()
    if color is None:
        color = choose_color(root)
        if color is None:
            root.destroy()
            return 0
    try:
        with open_game(config, color) as game:
            root.deiconify()
            App(root, game)
            root.mainloop()
    except FileNotFoundError as error:
        messagebox.showerror("Chess Challenge", str(error))
        return 1
    return 0
