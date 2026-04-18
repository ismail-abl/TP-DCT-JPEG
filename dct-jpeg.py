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
import matplotlib.pyplot as plt

BLOCKSIZE = 8
OUTPUT_DIR = "output"
QUALITY = 3

def read_image_file(path):
    img = Image.open(path)
    image_data = numpy.array(img)
    return pad_image(RGB_to_Grayscale(image_data), BLOCKSIZE)


def write_image(image_data, path, output_dir=OUTPUT_DIR):
    if output_dir in (None, "", "."):
        output_dir = OUTPUT_DIR

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


def get_quantization_matrix(quality=QUALITY, block_size=BLOCKSIZE):
    if quality < 1:
        raise ValueError("quality must be a positive integer")
    if block_size < 2:
        raise ValueError("block_size must be a positive integer greater than or equal to 2")

    quantize_matrix = numpy.zeros((block_size, block_size), dtype=numpy.float64)
    for i in range(block_size):
        for j in range(block_size):
            quantize_matrix[i, j] = 1 + (i + j + 1) * quality
    return quantize_matrix


def quantize(dct_data, quality=QUALITY, block_size=None):
    if dct_data.ndim != 2:
        raise ValueError("dct_data must be a 2D numpy array")

    if block_size is None:
        block_size = BLOCKSIZE
        if dct_data.shape[0] < block_size or dct_data.shape[1] < block_size:
            if dct_data.shape[0] == dct_data.shape[1]:
                block_size = dct_data.shape[0]
            else:
                raise ValueError("dct_data must be square when inferred block_size is used")

    if dct_data.shape[0] % block_size != 0 or dct_data.shape[1] % block_size != 0:
        raise ValueError(
            f"dct_data shape must be multiples of block_size={block_size}, got {dct_data.shape}"
        )

    quantize_matrix = get_quantization_matrix(quality=quality, block_size=block_size)
    quantization = numpy.zeros(dct_data.shape, dtype=numpy.int64)

    for i in range(0, dct_data.shape[0], block_size):
        for j in range(0, dct_data.shape[1], block_size):
            block = dct_data[i:i+block_size, j:j+block_size]
            quantization[i:i+block_size, j:j+block_size] = numpy.round(block / quantize_matrix).astype(numpy.int64)

    return quantization


def reverse_quantize(quantized_data, quality=QUALITY, block_size=None):
    if quantized_data.ndim != 2:
        raise ValueError("quantized_data must be a 2D numpy array")

    if block_size is None:
        block_size = BLOCKSIZE
        if quantized_data.shape[0] < block_size or quantized_data.shape[1] < block_size:
            if quantized_data.shape[0] == quantized_data.shape[1]:
                block_size = quantized_data.shape[0]
            else:
                raise ValueError("quantized_data must be square when inferred block_size is used")

    if quantized_data.shape[0] % block_size != 0 or quantized_data.shape[1] % block_size != 0:
        raise ValueError(
            f"quantized_data shape must be multiples of block_size={block_size}, got {quantized_data.shape}"
        )

    quantize_matrix = get_quantization_matrix(quality=quality, block_size=block_size)
    dequantized = numpy.zeros(quantized_data.shape, dtype=numpy.float64)

    for i in range(0, quantized_data.shape[0], block_size):
        for j in range(0, quantized_data.shape[1], block_size):
            block = quantized_data[i:i+block_size, j:j+block_size]
            dequantized[i:i+block_size, j:j+block_size] = block * quantize_matrix

    return dequantized


def _normalize_for_display(data):
    data = data.astype(numpy.float64)
    min_value = numpy.min(data)
    max_value = numpy.max(data)
    if max_value == min_value:
        return numpy.zeros(data.shape, dtype=numpy.uint8)
    return ((data - min_value) * 255.0 / (max_value - min_value)).astype(numpy.uint8)


def visualize_jpeg_steps(image_path, quality=QUALITY, block_size=BLOCKSIZE, output_dir=OUTPUT_DIR):
    if output_dir in (None, "", "."):
        output_dir = OUTPUT_DIR

    image_data = read_image_file(image_path)
    dct_coeff = dct(image_data, matrix_size=block_size)
    quantized = quantize(dct_coeff, quality=quality, block_size=block_size)
    dequantized = reverse_quantize(quantized, quality=quality, block_size=block_size)
    reconstructed = idct(dequantized, matrix_size=block_size)
    reconstructed = numpy.clip(reconstructed, 0, 255).astype(numpy.uint8)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    original_path = os.path.join(output_dir, "original.png")
    dct_path = os.path.join(output_dir, "dct_coefficients.png")
    quant_path = os.path.join(output_dir, "quantifie.png")
    reconstruction_path = os.path.join(output_dir, "reconstruction.png")
    compare_path = os.path.join(output_dir, "comparaison.png")

    Image.fromarray(image_data).save(original_path)
    Image.fromarray(_normalize_for_display(numpy.log1p(numpy.abs(dct_coeff)))).save(dct_path)
    Image.fromarray(_normalize_for_display(quantized)).save(quant_path)
    Image.fromarray(reconstructed).save(reconstruction_path)

    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    axes[0, 0].imshow(image_data, cmap="gray")
    axes[0, 0].set_title("Original (padded)")
    axes[0, 1].imshow(numpy.log1p(numpy.abs(dct_coeff)), cmap="gray")
    axes[0, 1].set_title("DCT log(1+abs)")
    axes[0, 2].imshow(quantized, cmap="gray")
    axes[0, 2].set_title("Quantized coefficients")
    axes[1, 0].imshow(dequantized, cmap="gray")
    axes[1, 0].set_title("Dequantized coefficients")
    axes[1, 1].imshow(reconstructed, cmap="gray")
    axes[1, 1].set_title("Reconstructed")
    axes[1, 2].imshow(numpy.abs(image_data.astype(numpy.float64) - reconstructed.astype(numpy.float64)), cmap="hot")
    axes[1, 2].set_title("Absolute error")

    for row in axes:
        for ax in row:
            ax.axis("off")

    plt.tight_layout()
    fig.savefig(compare_path, dpi=150)
    plt.close(fig)

    return {
        "original": original_path,
        "dct_coefficients": dct_path,
        "quantified": quant_path,
        "reconstruction": reconstruction_path,
        "comparison": compare_path,
    }

def zigzag(block):
    pass


def reverse_zigzag(zigzag_data, block_size=BLOCKSIZE):
    pass


def rle_encode(zigzag_data):
    pass


def rle_decode(rle_data):
    pass


def huffman_encode(rle_data):
    pass


def huffman_decode(huffman_data):
    pass


def _run_demo_images():
    outputs = visualize_jpeg_steps(
        image_path="Capture d’écran du 2026-03-27 01-22-28.png",
        quality=QUALITY,
        block_size=BLOCKSIZE,
        output_dir=OUTPUT_DIR,
    )
    for key, value in outputs.items():
        print(key + ": " + value)


if __name__ == "__main__":
    _run_demo_images()

