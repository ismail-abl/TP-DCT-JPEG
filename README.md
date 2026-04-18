# TP-DCT-JPEG

Mini projet autour de la transformee en cosinus discrete (DCT) appliquée à des images.

## Lancement en 1 commande

Depuis la racine du projet:

```bash
./run.sh
```

Sous Windows PowerShell:

```powershell
.\run.ps1
```

Sous Windows cmd.exe:

```cmd
run.cmd
```

Ce script fait automatiquement:

- creation du venv `.venv` s'il n'existe pas
- mise a jour de pip
- installation des dependances de `requirements.txt`
- execution de `dct-jpeg.py`

Tu peux aussi passer des arguments au script Python:

```bash
./run.sh arg1 arg2
```

Equivalent PowerShell:

```powershell
.\run.ps1 arg1 arg2
```

## Prerequis

- Python 3

## Lancer le programme manuellement

Depuis la racine du projet:

```bash
python3 dct-jpeg.py
```

Le programme lit les images de demo declarees dans le fichier et ecrit les sorties dans le dossier `test/`.

## Lancer les tests unitaires

Depuis la racine du projet:

```bash
python3 -m unittest discover -s test -p 'test_*.py'
```

Commande alternative (fichier unique):

```bash
python3 test/test_dct.py
```