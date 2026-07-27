"""
Ponto de entrada principal do Governance Gateway
Execute: python main.py
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH para permitir imports de src/
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Importa e executa o main do módulo src
from src.main import main

if __name__ == "__main__":
    main()
