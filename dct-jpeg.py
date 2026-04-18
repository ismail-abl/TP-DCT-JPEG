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

import os
import numpy
from PIL import Image

BLOCKSIZE = 8
OUTPUT_DIR = "output"

def read_image_file(path):
    img = Image.open(path)
    image_data = numpy.array(img)
    return pad_image(RGB_to_Grayscale(image_data), BLOCKSIZE)


def write_image(image_data, path, output_dir=OUTPUT_DIR):
    img = Image.fromarray(image_data)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    img.save(output_dir + "/" + path)


# simple ajout noir bas-droite au prochain multiple de bloc
def pad_image(image_data, block_size):
    pad_height = (block_size - (image_data.shape[0] % block_size)) % block_size
    before_pad_h, after_pad_h = pad_height // 2, pad_height - (pad_height // 2)
    pad_width = (block_size - (image_data.shape[1] % block_size)) % block_size
    before_pad_w, after_pad_w = pad_width // 2, pad_width - (pad_width // 2)
    if image_data.ndim == 2:
        pad_spec = ((before_pad_h, after_pad_h), (before_pad_w, after_pad_w))
    elif image_data.ndim == 3:
        pad_spec = ((before_pad_h, after_pad_h), (before_pad_w, after_pad_w), (0, 0))
    else:
        raise ValueError("image_data must be a 2D(grayscale) or 3D(RGB) numpy array")
    
    padded_image = numpy.pad(image_data, pad_spec, mode='constant', constant_values=0)
    
    if padded_image.shape[0] % block_size == 0 and padded_image.shape[1] % block_size == 0:
        return padded_image
    else:
        raise ValueError("incorrectly padded image: expected multiple of {}, got {}".format(BLOCKSIZE, padded_image.shape))
    

#TODO verifier les coeffs
def RGB_to_Grayscale(image_data):
    if image_data.ndim == 2:
        return image_data
    elif image_data.ndim == 3:
        return numpy.mean(image_data, axis=2).astype(numpy.uint8)
    else:
        print("Error: image_data must be a 2D(grayscale) or 3D(RGB) numpy array")
        exit(1)


def RGB_to_YCbCr(image_data):
    pass


def YCbCr_to_RGB(image_data):
    pass


def get_dct_coeff(block_size=BLOCKSIZE):
    if block_size < 2:
        raise ValueError("block_size must be a positive integer greater than or equal to 2")
    coeff_dct = numpy.zeros((block_size, block_size), dtype=numpy.float64)
    for i in range(block_size):
        for j in range(block_size):
            if i == 0:
                coeff_dct[i, j] = 1 / numpy.sqrt(block_size)
            else:
                coeff_dct[i, j] = numpy.sqrt(2 / block_size) * numpy.cos((2 * j + 1) * i * numpy.pi / (2 * block_size))
    return coeff_dct


# added matrix_size to test simple matrix for debug
def dct(image_data, matrix_size=BLOCKSIZE):
    if matrix_size < 2:
        raise ValueError("matrix_size must be a positive integer greater than or equal to 2")

    if image_data.ndim == 2:
        DCT = numpy.zeros(image_data.shape, dtype=numpy.float64)
        coeff_dct = get_dct_coeff(matrix_size)
        for i in range(0, image_data.shape[0], matrix_size):
            for j in range(0, image_data.shape[1], matrix_size):
                block = image_data[i:i+matrix_size, j:j+matrix_size]
                if block.shape != (matrix_size, matrix_size):
                    raise ValueError(f"block data must be a square block of size {matrix_size}x{matrix_size}")
                DCT[i:i+matrix_size, j:j+matrix_size] = coeff_dct @ block @ coeff_dct.T
        return DCT

    if image_data.ndim == 3:
        DCT = numpy.zeros(image_data.shape, dtype=numpy.float64)
        for channel in range(image_data.shape[2]):
            DCT[:, :, channel] = dct(image_data[:, :, channel], matrix_size=matrix_size)
        return DCT

    raise ValueError("image_data must be a 2D or 3D numpy array")


def idct(image_data, matrix_size=BLOCKSIZE):
    if matrix_size < 2:
        raise ValueError("matrix_size must be a positive integer greater than or equal to 2")

    if image_data.ndim == 2:
        IDCT = numpy.zeros(image_data.shape, dtype=numpy.float64)
        coeff_dct = get_dct_coeff(matrix_size)
        for i in range(0, image_data.shape[0], matrix_size):
            for j in range(0, image_data.shape[1], matrix_size):
                block = image_data[i:i+matrix_size, j:j+matrix_size]
                if block.shape != (matrix_size, matrix_size):
                    raise ValueError(f"block data must be a square block of size {matrix_size}x{matrix_size}")
                IDCT[i:i+matrix_size, j:j+matrix_size] = coeff_dct.T @ block @ coeff_dct
        return IDCT

    if image_data.ndim == 3:
        IDCT = numpy.zeros(image_data.shape, dtype=numpy.float64)
        for channel in range(image_data.shape[2]):
            IDCT[:, :, channel] = idct(image_data[:, :, channel], matrix_size=matrix_size)
        return IDCT

    raise ValueError("image_data must be a 2D or 3D numpy array")


def _run_demo_images():
    # simply load image, and save it for manual inspection
    img_test = read_image_file("Capture d’écran du 2026-03-27 01-22-28.png")
    write_image(img_test, "test1.png", "test")
    img_test = read_image_file("Capture d’écran du 2026-03-27 16-39-43.png")
    write_image(img_test, "test2.png", "test")
    img_test = read_image_file("Capture d’écran du 2026-03-27 18-33-24.png")
    write_image(img_test, "test3.png", "test")
    img_test = read_image_file("Capture d’écran du 2026-03-31 13-02-31.png")
    write_image(img_test, "test4.png", "test")


if __name__ == "__main__":
    _run_demo_images()

