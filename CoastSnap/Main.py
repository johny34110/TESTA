import os, sys
# ajoute le dossier 'CoastSnap' au chemin de recherche
base = os.path.join(os.path.dirname(__file__), "")
sys.path.insert(0, base)
from coastsnap_py.gui.CSP import main
main()