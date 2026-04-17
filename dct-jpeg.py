"""
TP DCT / JPEG simplifie sur les 3 canaux YCbCr.

Pipeline implémentée:
1) Lecture RGB
2) Conversion RGB -> YCbCr
3) Padding multiples de 8
4) Decoupage en blocs 4D: (nb_blocs, canaux, 8, 8)
5) DCT 2D par bloc et par canal
6) Quantification
7) zigzag
8) codage (RLE + Huffman)
"""

from matplotlib import pyplot as plt
import numpy as np
from PIL import Image

import numpy as np
from PIL import Image
from matplotlib import pyplot

BLOCKSIZE = 8

def lire_image(chemin):
    img = Image.open(chemin)
    image_data = np.array(img)
    return pad_image(image_data, BLOCKSIZE)

def ecrire_image(image_data, chemin):
    img = Image.fromarray(image_data)
    img.save(chemin)

def pad_image(image_data, block_size):
    pad_height = (block_size - (image_data.shape[0] % block_size)) % block_size
    pad_width = (block_size - (image_data.shape[1] % block_size)) % block_size
    padded_image = np.pad(image_data, ((0, pad_height), (0, pad_width), (0, 0)), mode='constant', constant_values=0)
    return padded_image

#TODO verifier les coeffs
def noiretblanc(image_data):
    if image_data.ndim == 2:
        return image_data
    elif image_data.ndim == 3:
        return np.mean(image_data, axis=2).astype(np.uint8)
    else:
        print("Error: image_data must be a 2D or 3D numpy array")
        exit(1)

def get_dct_coeff(block, block_size):
    C = np.zeros(block.shape)
    for i in range(block_size):
        for j in range(block_size):
            if i == 0:
                C[i, j] = 1 / np.sqrt(block_size)
            else:
                C[i, j] = np.sqrt(2 / block_size) * np.cos((2 * j + 1) * i * np.pi / (2 * block_size))
    return C
            
def dct(image_data):
    if image_data.ndim == 2:
        DCT = np.zeros(image_data.shape, dtype=np.float64)
        C = get_dct_coeff(np.zeros((BLOCKSIZE, BLOCKSIZE)), BLOCKSIZE)
        for i in range(0, image_data.shape[0], BLOCKSIZE):
            for j in range(0, image_data.shape[1], BLOCKSIZE):
                block = image_data[i:i+BLOCKSIZE, j:j+BLOCKSIZE]
                if block.shape != (BLOCKSIZE, BLOCKSIZE):
                    print(f"Error: block data must be a square block of size {BLOCKSIZE}x{BLOCKSIZE}")
                    exit(1)
                DCT[i:i+BLOCKSIZE, j:j+BLOCKSIZE] = C @ block @ C.T
        return DCT

    if image_data.ndim == 3:
        DCT = np.zeros(image_data.shape, dtype=np.float64)
        for channel in range(image_data.shape[2]):
            DCT[:, :, channel] = dct(image_data[:, :, channel])
        return DCT

    print("Error: image_data must be a 2D or 3D numpy array")
    exit(1)
    
def test():
    img_fleur = lire_image("fleur.jpg")
    img_nb_fleur = noiretblanc(img_fleur)
    dct_fleur = dct(img_nb_fleur)
    dct_uint = np.clip(dct_fleur, 0, 255).astype(np.uint8)
    ecrire_image(dct_uint, "testdct.jpg")

    # comparer taille 2 images:
    print(f"Original image size (après padding): {img_fleur.shape}")
    print(f"DCT image size: {dct_uint.shape}")

if __name__ == "__main__":
    test()