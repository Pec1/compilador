"""Ponto de entrada: python main.py <arquivo.java> [--json] [--ascii] [--sem-fonte]"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    try:
        from src.main import main
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as exc:
        print(f"[ERRO INESPERADO] {type(exc).__name__}: {exc}")
        sys.exit(1)
