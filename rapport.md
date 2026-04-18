# Rapport - Implémentation DCT/JPEG

## Objectif
Ce projet implémente une chaîne de compression inspirée de JPEG en niveaux de gris dans [dct-jpeg.py](dct-jpeg.py), puis évalue le compromis entre compression et qualité d'image.

## Principe technique
Le traitement suit les étapes classiques d'un codec JPEG simplifié:
1. L'image est lue puis convertie en niveaux de gris pour travailler sur une seule composante.
2. Un padding est appliqué pour obtenir des dimensions multiples de 8, afin de traiter l'image par blocs 8x8.
3. Chaque bloc est centré autour de 128 puis transformé par DCT 2D.
4. La quantification réduit la précision des coefficients, surtout ceux des hautes fréquences.
5. Les coefficients sont parcourus en zigzag, compressés par RLE puis encodés par Huffman.
6. La reconstruction se fait par déquantification puis IDCT.
7. La qualité est mesurée avec le MSE et le PSNR, et la compression avec le gain et le ratio.

## Notions clés
- La DCT concentre l'information utile dans les basses fréquences, généralement en haut à gauche de la matrice.
- Les hautes fréquences représentent surtout les détails fins et les contours.
- La quantification supprime ou arrondit davantage ces hautes fréquences, ce qui réduit la taille mais dégrade l'image.
- Le MSE mesure l'écart moyen entre l'image originale et l'image reconstruite.
- Le PSNR traduit cet écart en une mesure de qualité: plus il est élevé, meilleure est la reconstruction.
- Le gain indique la part d'espace économisée, tandis que le ratio compare directement la taille originale à la taille compressée.

## Résultats (exemple multi-qualités)
Commande utilisée:

```bash
python3 dct-jpeg.py --qualities 1,2,3,4,5,10,15,20,25,30 --main-quality 15
```

Tendance observée:
- Quand `quality` augmente, la quantification est plus forte.
- La taille compressée diminue.
- Le gain et le ratio augmentent.
- Le PSNR baisse, donc la qualité visuelle diminue.

## Figures pertinentes

### 1) Image d'entrée (grayscale)
![Image originale](output/original.png)
Cette figure montre l'image de départ après conversion en niveaux de gris et padding.

### 2) Coefficients DCT (visualisation)
![DCT coefficients](output/dct_coefficients.png)
On observe que les coefficients importants sont regroupés dans les basses fréquences, tandis que les zones plus éloignées correspondent aux détails et aux variations rapides de l'image.

### 3) Coefficients quantifiés
![Coefficients quantifiés](output/quantifie.png)
Après quantification, beaucoup de coefficients deviennent petits ou nuls. Cela montre que l'on conserve surtout l'information principale et que l'on élimine une partie des détails. On va alors garder l'information essentielle, des basses fréquences et éliminer en partie les hautes fréquences de l'image

### 4) Image reconstruite
![Image reconstruite](output/reconstruction.png)
La reconstruction reste proche de l'image d'origine, mais on peut voir des artefacts de compression, surtout sur les zones de texte et les contours.

### 5) Comparaison original/reconstruction/erreur
![Comparaison](output/comparaison.png)
Cette figure compare l'original, la reconstruction et la carte d'erreur. Les écarts apparaissent surtout sur les zones de fort contraste, où la compression est la plus visible.

![zoom texte](image.png)

### 6) Compromis gain/qualité
![Gain et qualités](output/gain_qualites.png)
Cette courbe montre le compromis classique: plus la compression est forte, plus le gain augmente, mais plus la qualité mesurée par le PSNR diminue. 25 serait la compression la plus forte encore pertinente, augmenter au delà va beaucoup trop diminuer le SNR et la qualité pour peu de rendement en compression.

## Conclusion
Le code couvre les briques principales d'un codec JPEG simplifié: transformation fréquentielle, quantification, compression entropique et reconstruction. Les figures confirment le comportement attendu d'un codec de type JPEG: bonne réduction de taille, mais perte progressive de fidélité quand la quantification augmente.
