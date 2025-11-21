import sys
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <dossier_a_trier>")
        sys.exit(1)

    folder = Path(sys.argv[1])
    print(f"Triage du dossier : {folder}")

    # 👉 Ici ton code NLP + classement de fichiers
    # ...

if __name__ == "__main__":
    main()
