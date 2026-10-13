import sys
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .main import analyze_source, read_source_file, AnalysisResult, format_ast, format_ignored


class LineNumbers(tk.Canvas):
    """Barra lateral com numeração de linhas sincronizada com o editor de código."""
    def __init__(self, master, text_widget, **kwargs):
        super().__init__(master, **kwargs)
        self.text_widget = text_widget
        self.configure(width=45, bg="#f1f3f5", highlightthickness=0)

    def redraw(self, *args):
        """Redesenha os números de linha com base no conteúdo visível do editor."""
        self.delete("all")
        i = self.text_widget.index("@0,0")
        while True:
            dline = self.text_widget.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.create_text(
                38, y,
                anchor="ne",
                text=linenum,
                font=("Consolas", 11),
                fill="#6c757d"
            )
            i = self.text_widget.index(f"{i}+1line")


class CompiladorGUI(tk.Tk):
    """Interface Gráfica Didática e Acadêmica para o Compilador AV3."""
    def __init__(self):
        super().__init__()
        self.title("Compilador AV3 — Analisador de Código")
        self.geometry("1020x720")
        self.minsize(860, 600)

        self.current_filepath = None

        self._configure_styles()
        self._build_ui()
        self._bind_shortcuts()
        self.set_status("Pronto")

    def _configure_styles(self):
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        # Configurações de estilo para visual acadêmico e sóbrio
        self.configure(bg="#f8f9fa")
        self.style.configure(".", background="#f8f9fa", font=("Segoe UI", 10))
        self.style.configure("TFrame", background="#f8f9fa")
        self.style.configure("Header.TFrame", background="#2b303a")
        self.style.configure("HeaderTitle.TLabel", background="#2b303a", foreground="#ffffff", font=("Segoe UI", 12, "bold"))
        self.style.configure("HeaderSub.TLabel", background="#2b303a", foreground="#adb5bd", font=("Segoe UI", 9))
        self.style.configure("Action.TButton", font=("Segoe UI", 10, "bold"), padding=4)
        self.style.configure("Tool.TButton", font=("Segoe UI", 9), padding=3)

        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        self.style.configure("Treeview", font=("Consolas", 10), rowheight=24)
        self.style.configure("TNotebook.Tab", font=("Segoe UI", 10), padding=(12, 6))

    def _build_ui(self):
        # 1. Top Bar / Header
        header_frame = ttk.Frame(self, style="Header.TFrame", padding=(14, 10))
        header_frame.pack(fill=tk.X, side=tk.TOP)

        title_box = ttk.Frame(header_frame, style="Header.TFrame")
        title_box.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Label(title_box, text="Compilador AV3", style="HeaderTitle.TLabel").pack(anchor=tk.W)
        ttk.Label(title_box, text="Analisador Didático: Léxico • Tabela • Sintático • AST • Semântica", style="HeaderSub.TLabel").pack(anchor=tk.W)

        top_buttons = ttk.Frame(header_frame, style="Header.TFrame")
        top_buttons.pack(side=tk.RIGHT, fill=tk.Y)
        ttk.Button(top_buttons, text="📂 Abrir (Ctrl+O)", style="Tool.TButton", command=self.on_open).pack(side=tk.LEFT, padx=4)
        ttk.Button(top_buttons, text="💾 Salvar (Ctrl+S)", style="Tool.TButton", command=self.on_save).pack(side=tk.LEFT, padx=4)

        # 2. Toolbar de Ações
        toolbar = ttk.Frame(self, padding=(14, 8))
        toolbar.pack(fill=tk.X, side=tk.TOP)

        ttk.Button(toolbar, text="▶ Analisar Código (F5)", style="Action.TButton", command=self.on_analyze).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="🧹 Limpar Resultados (Ctrl+L)", style="Tool.TButton", command=self.on_clear).pack(side=tk.LEFT, padx=4)

        self.file_label_var = tk.StringVar(value="Nenhum arquivo aberto")
        ttk.Label(toolbar, textvariable=self.file_label_var, foreground="#6c757d", font=("Segoe UI", 9, "italic")).pack(side=tk.RIGHT, padx=6)

        # 3. Painel Divisor Principal (Editor em cima / Resultados embaixo)
        paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 6))

        # --- Painel Superior: Editor de Código ---
        editor_container = ttk.Frame(paned)
        paned.add(editor_container, weight=1)

        editor_header = ttk.Frame(editor_container)
        editor_header.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(editor_header, text="EDITOR DE CÓDIGO FONTE", font=("Segoe UI", 9, "bold"), foreground="#495057").pack(side=tk.LEFT)

        editor_box = ttk.Frame(editor_container, borderwidth=1, relief=tk.SOLID)
        editor_box.pack(fill=tk.BOTH, expand=True)

        # Scrollbars do editor
        v_scroll = ttk.Scrollbar(editor_box, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll = ttk.Scrollbar(editor_box, orient=tk.HORIZONTAL)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.editor = tk.Text(
            editor_box,
            wrap="none",
            font=("Consolas", 11),
            bg="#ffffff",
            fg="#212529",
            insertbackground="#000000",
            selectbackground="#cce5ff",
            selectforeground="#000000",
            relief=tk.FLAT,
            undo=True,
            padx=8,
            pady=6
        )

        self.line_numbers = LineNumbers(editor_box, self.editor)
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        self.editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Sincronização dos scrollbars
        self.editor.config(xscrollcommand=h_scroll.set)
        h_scroll.config(command=self.editor.xview)

        def _on_vscroll(*args):
            self.editor.yview(*args)
            self.line_numbers.redraw()

        def _on_editor_scroll(first, last):
            v_scroll.set(first, last)
            self.line_numbers.redraw()

        v_scroll.config(command=_on_vscroll)
        self.editor.config(yscrollcommand=_on_editor_scroll)

        # Eventos para redesenhar numeração de linha
        self.editor.bind("<KeyRelease>", lambda e: self.line_numbers.redraw())
        self.editor.bind("<MouseWheel>", lambda e: self.after(10, self.line_numbers.redraw))
        self.editor.bind("<Button-1>", lambda e: self.after(10, self.line_numbers.redraw))
        self.editor.bind("<Configure>", lambda e: self.line_numbers.redraw())

        # Editor inicia completamente vazio aguardando arquivo do usuário
        self.after(50, self.line_numbers.redraw)

        # --- Painel Inferior: Abas de Resultado ---
        results_container = ttk.Frame(paned)
        paned.add(results_container, weight=1)

        self.notebook = ttk.Notebook(results_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Aba 1: Tokens
        self.tab_tokens = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_tokens, text="  Tokens  ")
        self._build_tokens_tab(self.tab_tokens)

        # Aba 2: Tabela de Símbolos
        self.tab_symbols = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_symbols, text="  Tabela de Símbolos  ")
        self._build_symbols_tab(self.tab_symbols)

        # Aba 3: AST
        self.tab_ast = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ast, text="  AST  ")
        self._build_ast_tab(self.tab_ast)

        # Aba 4: Semântica
        self.tab_semantic = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_semantic, text="  Semântica  ")
        self._build_semantic_tab(self.tab_semantic)

        # Aba 5: Erros
        self.tab_erros = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_erros, text="  Erros  ")
        self._build_errors_tab(self.tab_erros)

        # 4. Status Bar
        status_bar = ttk.Frame(self, relief=tk.SUNKEN, padding=(8, 3))
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_var = tk.StringVar(value="Pronto")
        ttk.Label(status_bar, textvariable=self.status_var, font=("Segoe UI", 9)).pack(side=tk.LEFT)

        # Inicializa abas no estado limpo aguardando análise
        self.on_clear()

    def _build_tokens_tab(self, parent):
        cols = ("#", "Tipo", "Lexema", "Linha", "Coluna")
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        v_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll = ttk.Scrollbar(frame, orient=tk.HORIZONTAL)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.tokens_tree = ttk.Treeview(frame, columns=cols, show="headings", yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.config(command=self.tokens_tree.yview)
        h_scroll.config(command=self.tokens_tree.xview)

        widths = {"#": 50, "Tipo": 180, "Lexema": 180, "Linha": 80, "Coluna": 80}
        for col in cols:
            self.tokens_tree.heading(col, text=col)
            self.tokens_tree.column(col, width=widths.get(col, 100), anchor="center" if col in ("#", "Linha", "Coluna") else "w")

        self.tokens_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _build_symbols_tab(self, parent):
        cols = ("Ordem", "Lexema", "Categoria", "Tipo", "Linha")
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        v_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll = ttk.Scrollbar(frame, orient=tk.HORIZONTAL)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.symbols_tree = ttk.Treeview(frame, columns=cols, show="headings", yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.config(command=self.symbols_tree.yview)
        h_scroll.config(command=self.symbols_tree.xview)

        widths = {"Ordem": 60, "Lexema": 160, "Categoria": 160, "Tipo": 200, "Linha": 80}
        for col in cols:
            self.symbols_tree.heading(col, text=col)
            self.symbols_tree.column(col, width=widths.get(col, 100), anchor="center" if col in ("Ordem", "Linha") else "w")

        self.symbols_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _build_ast_tab(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        v_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll = ttk.Scrollbar(frame, orient=tk.HORIZONTAL)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.ast_text = tk.Text(frame, wrap="none", font=("Consolas", 11), bg="#ffffff", fg="#212529", state="disabled", relief=tk.FLAT, padx=8, pady=6)
        self.ast_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.ast_text.config(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.config(command=self.ast_text.yview)
        h_scroll.config(command=self.ast_text.xview)

    def _build_semantic_tab(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        v_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.semantic_text = tk.Text(frame, wrap="word", font=("Consolas", 11), bg="#ffffff", fg="#212529", state="disabled", relief=tk.FLAT, padx=8, pady=6)
        self.semantic_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.semantic_text.config(yscrollcommand=v_scroll.set)
        v_scroll.config(command=self.semantic_text.yview)

    def _build_errors_tab(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        v_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.errors_text = tk.Text(frame, wrap="word", font=("Consolas", 11), bg="#ffffff", fg="#212529", state="disabled", relief=tk.FLAT, padx=8, pady=6)
        self.errors_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.errors_text.config(yscrollcommand=v_scroll.set)
        v_scroll.config(command=self.errors_text.yview)

        # Tags para coloração didática de mensagens
        self.errors_text.tag_config("erro_titulo", foreground="#d90429", font=("Consolas", 11, "bold"))
        self.errors_text.tag_config("erro_corpo", foreground="#b00020", font=("Consolas", 11))
        self.errors_text.tag_config("ok", foreground="#2b9348", font=("Consolas", 11, "bold"))

    def _bind_shortcuts(self):
        self.bind("<Control-o>", lambda e: self.on_open())
        self.bind("<Control-O>", lambda e: self.on_open())
        self.bind("<Control-s>", lambda e: self.on_save())
        self.bind("<Control-S>", lambda e: self.on_save())
        self.bind("<F5>", lambda e: self.on_analyze())
        self.bind("<Control-l>", lambda e: self.on_clear())
        self.bind("<Control-L>", lambda e: self.on_clear())

        # Selecionar tudo no editor (Ctrl+A)
        self.editor.bind("<Control-a>", self._select_all)
        self.editor.bind("<Control-A>", self._select_all)

    def _select_all(self, event=None):
        self.editor.tag_add("sel", "1.0", "end")
        return "break"

    def set_status(self, text):
        self.status_var.set(text)

    def _set_readonly_text(self, text_widget, content, tag=None):
        text_widget.config(state="normal")
        text_widget.delete("1.0", tk.END)
        if content:
            if tag:
                text_widget.insert("1.0", content, tag)
            else:
                text_widget.insert("1.0", content)
        text_widget.config(state="disabled")

    def get_editor_text(self):
        return self.editor.get("1.0", "end-1c")

    # -------------------------------------------------------------
    # AÇÕES PRINCIPAIS
    # -------------------------------------------------------------

    def on_open(self):
        """Abre um arquivo com mecanismo seguro e carrega no editor."""
        try:
            path = filedialog.askopenfilename(
                title="Abrir Arquivo de Código Fonte",
                filetypes=[
                    ("Arquivos Java", "*.java"),
                    ("Arquivos C", "*.c"),
                    ("Arquivos de Texto", "*.txt"),
                    ("Todos os Arquivos", "*.*")
                ]
            )
            if not path:
                return

            content, err = read_source_file(path)
            if err:
                self.on_clear()
                self._set_readonly_text(self.errors_text, err, tag="erro_corpo")
                self.notebook.select(self.tab_erros)
                self.set_status("Erro ao abrir arquivo")
                messagebox.showerror("Erro de Leitura", err)
                return

            self.editor.delete("1.0", tk.END)
            self.editor.insert("1.0", content)
            self.line_numbers.redraw()

            self.current_filepath = path
            filename = Path(path).name
            self.file_label_var.set(f"Arquivo: {filename}")
            self.title(f"Compilador AV3 — {filename}")
            self.on_clear()
            self.set_status(f"Arquivo carregado com sucesso: {filename}")

        except Exception as exc:
            self.set_status("Erro inesperado ao abrir arquivo")
            messagebox.showerror("Erro Inesperado", f"Ocorreu um erro ao abrir o arquivo: {exc}")

    def on_save(self):
        """Salva o conteúdo editado no arquivo associado ou abre 'Salvar Como'."""
        try:
            if self.current_filepath:
                path = self.current_filepath
            else:
                path = filedialog.asksaveasfilename(
                    title="Salvar Código Fonte",
                    defaultextension=".java",
                    filetypes=[
                        ("Arquivos Java", "*.java"),
                        ("Arquivos C", "*.c"),
                        ("Arquivos de Texto", "*.txt"),
                        ("Todos os Arquivos", "*.*")
                    ]
                )
                if not path:
                    return
                self.current_filepath = path

            content = self.get_editor_text()
            Path(path).write_text(content, encoding="utf-8")

            filename = Path(path).name
            self.file_label_var.set(f"Arquivo: {filename}")
            self.title(f"Compilador AV3 — {filename}")
            self.set_status(f"Arquivo salvo com sucesso: {filename}")

        except Exception as exc:
            self.set_status("Erro ao salvar arquivo")
            messagebox.showerror("Erro de Gravação", f"[ERRO DE ENTRADA]\nNão foi possível salvar o arquivo:\n{exc}")

    def on_clear(self):
        """Limpa as abas de resultados e redefine o estado da análise."""
        for item in self.tokens_tree.get_children():
            self.tokens_tree.delete(item)

        for item in self.symbols_tree.get_children():
            self.symbols_tree.delete(item)

        self._set_readonly_text(self.ast_text, "")
        self._set_readonly_text(self.semantic_text, "(Aguardando análise)")
        self._set_readonly_text(self.errors_text, "(Aguardando análise)")
        self.set_status("Pronto")

    def on_analyze(self):
        """Executa a análise do código e preenche as abas do compilador."""
        try:
            for item in self.tokens_tree.get_children():
                self.tokens_tree.delete(item)

            for item in self.symbols_tree.get_children():
                self.symbols_tree.delete(item)

            self._set_readonly_text(self.ast_text, "")
            self._set_readonly_text(self.semantic_text, "")
            self._set_readonly_text(self.errors_text, "")
            self.set_status("Analisando código...")
            self.update_idletasks()

            source = self.get_editor_text()
            result: AnalysisResult = analyze_source(source)

            # 1. Preenchimento da Aba de Tokens
            for idx, token in enumerate(result.tokens, start=1):
                self.tokens_tree.insert(
                    "", tk.END,
                    values=(idx, token.type.name, token.lexeme, token.line, token.column)
                )

            # 2. Preenchimento da Aba de Tabela de Símbolos
            if result.symbol_table:
                symbols = result.symbol_table.all()
                for sym in symbols:
                    self.symbols_tree.insert(
                        "", tk.END,
                        values=(sym["order"], sym["name"], sym["category"], sym["type"], sym["line"])
                    )

            # 3. Preenchimento da Aba AST
            ast_text = format_ast(result.ast) + "\n" + format_ignored(result.ignored)
            if result.syntax_errors:
                ast_text += "\n\nErros sintáticos:\n" + "\n".join(str(e) for e in result.syntax_errors)
            self._set_readonly_text(self.ast_text, ast_text)

            # 4. Preenchimento da Aba Semântica
            if result.semantic_errors:
                msg = f"ERROS SEMÂNTICOS ENCONTRADOS ({len(result.semantic_errors)}):\n\n"
                msg += "\n\n".join(str(e) for e in result.semantic_errors)
                self._set_readonly_text(self.semantic_text, msg)
            else:
                self._set_readonly_text(self.semantic_text, "[OK]\nValidação semântica concluída sem erros.", tag="ok")

            # 5. Preenchimento da Aba Geral de Erros
            if result.has_errors:
                erros_lista = []
                erros_lista.extend(str(e) for e in result.lexical_errors)
                erros_lista.extend(str(e) for e in result.syntax_errors)
                for se in result.semantic_errors:
                    erros_lista.append(str(se))

                texto_erros = "\n".join(erros_lista)
                self._set_readonly_text(self.errors_text, texto_erros, tag="erro_corpo")
                self.notebook.select(self.tab_erros)
                self.set_status(f"Análise concluída com erro(s): {len(erros_lista)} problema(s) detectado(s)")
            else:
                if not source.strip():
                    self._set_readonly_text(self.errors_text, "[OK]\nArquivo vazio: nenhum comando para analisar.", tag="ok")
                    self.set_status("Análise concluída: arquivo vazio")
                else:
                    self._set_readonly_text(self.errors_text, "[OK]\nNenhum erro encontrado no código-fonte.\nO programa está conforme com a gramática e regras semânticas.", tag="ok")
                    self.set_status("Análise concluída com sucesso (0 erros)")
                    # Seleciona a aba AST por padrão quando válido para demonstração
                    self.notebook.select(self.tab_ast)

        except Exception as exc:
            self.set_status("Falha inesperada durante a análise")
            self._set_readonly_text(self.errors_text, f"[ERRO INESPERADO]\n{exc}", tag="erro_corpo")
            self.notebook.select(self.tab_erros)
            messagebox.showerror("Erro na Análise", f"Ocorreu uma falha no processamento: {exc}")


def main():
    app = CompiladorGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
