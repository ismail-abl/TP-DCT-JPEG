"""
1) Lecture RGB
2) Conversion RGB -> YCbCr OU Conversion RGB -> Grayscale
3) Padding multiples de 8
4) Decoupage en blocs 4D: (nb_blocs, canaux, 8, 8)
5) DCT 2D par bloc et par canal
6) Quantification
7) zigzag
8) codage (RLE puis Huffman)
"""

import numpy
from PIL import Image
from matplotlib import pyplot as plt

BLOCKSIZE = 8

JPEG_LUMA_QUANT = numpy.array(
    [
        [16, 11, 10, 16, 24, 40, 51, 61],
        [12, 12, 14, 19, 26, 58, 60, 55],
        [14, 13, 16, 24, 40, 57, 69, 56],
        [14, 17, 22, 29, 51, 87, 80, 62],
        [18, 22, 37, 56, 68, 109, 103, 77],
        [24, 35, 55, 64, 81, 104, 113, 92],
        [49, 64, 78, 87, 103, 121, 120, 101],
        [72, 92, 95, 98, 112, 100, 103, 99],
    ],
    dtype=numpy.float64,
)

def read_image_file(path):
    img = Image.open(path)
    image_data = numpy.array(img)
    return pad_image(image_data, BLOCKSIZE)

def write_image(image_data, path):
    img = Image.fromarray(image_data)
    img.save(path)

# simple ajout noir bas-droite au prochain multiple de bloc
def pad_image(image_data, block_size):
    pad_height = (block_size - (image_data.shape[0] % block_size)) % block_size
    pad_width = (block_size - (image_data.shape[1] % block_size)) % block_size
    if image_data.ndim == 2:
        pad_spec = ((0, pad_height), (0, pad_width))
    elif image_data.ndim == 3:
        pad_spec = ((0, pad_height), (0, pad_width), (0, 0))
    else:
        raise ValueError("image_data must be a 2D or 3D numpy array")
    return numpy.pad(image_data, pad_spec, mode="constant", constant_values=0)

#TODO verifier les coeffs
def RGB_to_Grayscale(image_data):
    if image_data.ndim == 2:
        return image_data
    elif image_data.ndim == 3:
        return numpy.mean(image_data, axis=2).astype(numpy.uint8)
    else:
        print("Error: image_data must be a 2D or 3D numpy array")
        exit(1)

def RGB_to_YCbCr(image_data):
    pass

def YCbCr_to_RGB(image_data):
    pass

def get_dct_coeff(block_size=BLOCKSIZE):
    coeff_dct = numpy.zeros((block_size, block_size), dtype=numpy.float64)
    for i in range(block_size):
        for j in range(block_size):
            if i == 0:
                coeff_dct[i, j] = 1 / numpy.sqrt(block_size)
            else:
                coeff_dct[i, j] = numpy.sqrt(2 / block_size) * numpy.cos((2 * j + 1) * i * numpy.pi / (2 * block_size))
    return coeff_dct

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
            