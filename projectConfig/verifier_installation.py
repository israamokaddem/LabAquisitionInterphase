"""
verifier_installation.py
Vérifie que tout est correctement installé avant de lancer WaveLab.
Lancer avec : python verifier_installation.py
"""

import sys

OK   = "  [OK]"
WARN = "  [!!]"
ERR  = "  [XX]"

def titre(texte):
    print(f"\n{'='*50}")
    print(f"  {texte}")
    print('='*50)

def check(label, ok, message=""):
    symbole = OK if ok else ERR
    print(f"{symbole}  {label}", f"— {message}" if message else "")
    return ok

# ============================================================
titre("1. VERSION PYTHON")
# ============================================================
version = sys.version_info
ok_python = version >= (3, 9)
check(
    f"Python {version.major}.{version.minor}.{version.micro}",
    ok_python,
    "OK" if ok_python else "Version 3.9 minimum requise — https://python.org/downloads"
)

# ============================================================
titre("2. BIBLIOTHÈQUES COMMUNES")
# ============================================================
libs = {
    "PyQt6"      : "pip install PyQt6",
    "pyqtgraph"  : "pip install pyqtgraph",
    "pandas"     : "pip install pandas",
    "numpy"      : "pip install numpy",
}

for lib, cmd in libs.items():
    try:
        __import__(lib.lower().replace("6","").replace("graph","graph"))
        check(lib, True)
    except ImportError:
        check(lib, False, f"Non installé → {cmd}")

# ============================================================
titre("3. BOÎTIER MCC USB-1808X")
# ============================================================
try:
    import mcculw
    check("mcculw (bibliothèque Python)", True)

    try:
        from mcculw import ul
        from mcculw.enums import InterfaceType
        ul.ignore_instacal()
        devices = ul.get_daq_device_inventory(InterfaceType.USB)
        nb = len(devices)
        if nb > 0:
            check(f"Cartes MCC détectées : {nb}", True)
            for i, d in enumerate(devices):
                print(f"         Board {i} → {d.product_name}  SN: {d.unique_id}")
        else:
            check("Cartes MCC détectées", False,
                  "Aucune carte trouvée — vérifier le câble USB et qu'InstaCal la voit")
    except Exception as e:
        check("Détection cartes MCC", False, f"Erreur : {e}")

except ImportError:
    check("mcculw", False,
          "Non installé → pip install mcculw  (+ installer MCC DAQ Software d'abord)")
    print(f"{WARN}  MCC DAQ Software : https://digilent.com/reference/software/mccdaq-cd/start")

# ============================================================
titre("4. BOÎTIER NATIONAL INSTRUMENTS")
# ============================================================
try:
    import nidaqmx
    check("nidaqmx (bibliothèque Python)", True)

    try:
        system = nidaqmx.system.System.local()
        nb = len(system.devices)
        if nb > 0:
            check(f"Boîtiers NI détectés : {nb}", True)
            for d in system.devices:
                print(f"         → {d.name}  ({d.product_type})")
        else:
            check("Boîtiers NI détectés", False,
                  "Aucun trouvé — vérifier NI MAX et la connexion USB/châssis")
    except Exception as e:
        check("Détection boîtiers NI", False, f"Erreur : {e}")

except ImportError:
    check("nidaqmx", False,
          "Non installé → pip install nidaqmx  (+ installer NI-DAQmx d'abord)")
    print(f"{WARN}  NI-DAQmx : https://www.ni.com/fr-fr/support/downloads/drivers/download.ni-daq-mx.html")

# ============================================================
titre("RÉSUMÉ")
# ============================================================
print("""
  Si tous les [OK] sont verts pour votre matériel,
  vous pouvez lancer WaveLab :

      python maquetteInterpahce.py

  Pour la simulation MCC (sans matériel) :
  cocher "MCC USB-1808X" + "Simulation" dans WaveLab.
""")
