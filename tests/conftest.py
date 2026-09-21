"""Asegura que la raiz del repo esta en sys.path para los tests."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
