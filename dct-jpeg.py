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

import argparse
import os
import pathlib
import heapq
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

def zigzag(block):
    block = numpy.asarray(block)
    if block.ndim != 2:
        raise ValueError("block must be a 2D numpy array")
    if block.shape[0] != block.shape[1]:
        raise ValueError("block must be square")

    block_size = block.shape[0]
    zigzag_data = []

    for diagonal_sum in range(2 * block_size - 1):
        if diagonal_sum % 2 == 0:
            row = min(diagonal_sum, block_size - 1)
            col = diagonal_sum - row
            while row >= 0 and col < block_size:
                zigzag_data.append(block[row, col])
                row -= 1
                col += 1
        else:
            col = min(diagonal_sum, block_size - 1)
            row = diagonal_sum - col
            while col >= 0 and row < block_size:
                zigzag_data.append(block[row, col])
                row += 1
                col -= 1

    return numpy.asarray(zigzag_data, dtype=block.dtype)


def reverse_zigzag(zigzag_data, block_size=BLOCKSIZE):
    zigzag_data = numpy.asarray(zigzag_data)
    if zigzag_data.ndim != 1:
        raise ValueError("zigzag_data must be a 1D numpy array")
    if block_size < 2:
        raise ValueError("block_size must be a positive integer greater than or equal to 2")
    if zigzag_data.size != block_size * block_size:
        raise ValueError(
            f"zigzag_data size must be equal to block_size**2, got {zigzag_data.size} for block_size={block_size}"
        )

    block = numpy.zeros((block_size, block_size), dtype=zigzag_data.dtype)
    index = 0

    for diagonal_sum in range(2 * block_size - 1):
        if diagonal_sum % 2 == 0:
            row = min(diagonal_sum, block_size - 1)
            col = diagonal_sum - row
            while row >= 0 and col < block_size:
                block[row, col] = zigzag_data[index]
                index += 1
                row -= 1
                col += 1
        else:
            col = min(diagonal_sum, block_size - 1)
            row = diagonal_sum - col
            while col >= 0 and row < block_size:
                block[row, col] = zigzag_data[index]
                index += 1
                row += 1
                col -= 1

    return block


def rle_encode(zigzag_data):
    zigzag_data = numpy.asarray(zigzag_data)
    if zigzag_data.ndim != 1:
        raise ValueError("zigzag_data must be a 1D numpy array")
    if zigzag_data.size == 0:
        return []

    encoded = []
    current_value = zigzag_data[0]
    count = 1

    for value in zigzag_data[1:]:
        if value == current_value:
            count += 1
        else:
            encoded.append((current_value.item() if hasattr(current_value, "item") else current_value, count))
            current_value = value
            count = 1

    encoded.append((current_value.item() if hasattr(current_value, "item") else current_value, count))
    return encoded


def rle_decode(rle_data):
    decoded = []
    for item in rle_data:
        if len(item) != 2:
            raise ValueError("rle_data items must be (value, count) pairs")
        value, count = item
        if count < 0:
            raise ValueError("run length must be non-negative")
        decoded.extend([value] * count)
    return numpy.asarray(decoded)


def huffman_encode(rle_data):
    normalized_symbols = []
    for item in rle_data:
        if len(item) != 2:
            raise ValueError("rle_data items must be (value, count) pairs")
        value, count = item
        normalized_symbols.append((value, count))

    if len(normalized_symbols) == 0:
        return {"bitstring": "", "codes": {}}

    frequency = {}
    for symbol in normalized_symbols:
        frequency[symbol] = frequency.get(symbol, 0) + 1

    # heap entries are (frequency, order, node), where node is either a symbol tuple
    # or a pair of children for internal nodes.
    heap = []
    order = 0
    for symbol, count in frequency.items():
        heapq.heappush(heap, (count, order, symbol))
        order += 1

    if len(heap) == 1:
        only_symbol = heap[0][2]
        codes = {only_symbol: "0"}
        bitstring = "0" * len(normalized_symbols)
        return {"bitstring": bitstring, "codes": codes}

    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        merged_frequency = left[0] + right[0]
        merged_node = (left[2], right[2])
        heapq.heappush(heap, (merged_frequency, order, merged_node))
        order += 1

    root = heap[0][2]
    codes = {}
    stack = [(root, "")]
    while len(stack) > 0:
        node, prefix = stack.pop()
        if isinstance(node, tuple) and len(node) == 2 and isinstance(node[0], tuple) and isinstance(node[1], tuple):
            stack.append((node[1], prefix + "1"))
            stack.append((node[0], prefix + "0"))
        else:
            codes[node] = prefix if prefix != "" else "0"

    bitstring = "".join(codes[symbol] for symbol in normalized_symbols)
    return {"bitstring": bitstring, "codes": codes}


def huffman_decode(huffman_data):
    if not isinstance(huffman_data, dict):
        raise ValueError("huffman_data must be a dictionary with keys 'bitstring' and 'codes'")
    if "bitstring" not in huffman_data or "codes" not in huffman_data:
        raise ValueError("huffman_data must contain 'bitstring' and 'codes'")

    bitstring = huffman_data["bitstring"]
    codes = huffman_data["codes"]

    if not isinstance(bitstring, str):
        raise ValueError("huffman_data['bitstring'] must be a string")
    if not isinstance(codes, dict):
        raise ValueError("huffman_data['codes'] must be a dictionary")

    if bitstring == "":
        if len(codes) == 0:
            return []
        raise ValueError("empty bitstring is only valid with an empty codebook")

    inverse_codes = {}
    for symbol, code in codes.items():
        if not isinstance(code, str) or code == "":
            raise ValueError("all Huffman codes must be non-empty bit strings")
        if any(bit not in ("0", "1") for bit in code):
            raise ValueError("Huffman codes must contain only '0' and '1'")
        if code in inverse_codes:
            raise ValueError("duplicate Huffman code detected")
        inverse_codes[code] = symbol

    decoded_symbols = []
    current_bits = ""
    for bit in bitstring:
        if bit not in ("0", "1"):
            raise ValueError("bitstring must contain only '0' and '1'")
        current_bits += bit
        if current_bits in inverse_codes:
            decoded_symbols.append(inverse_codes[current_bits])
            current_bits = ""

    if current_bits != "":
        raise ValueError("bitstring ended with an incomplete Huffman code")

    return decoded_symbols


def crop_to_shape(image_data, target_shape):
    if len(target_shape) != 2:
        raise ValueError("target_shape must contain exactly (height, width)")

    target_h, target_w = target_shape
    if image_data.shape[0] < target_h or image_data.shape[1] < target_w:
        raise ValueError("image_data is smaller than target shape")

    start_h = (image_data.shape[0] - target_h) // 2
    start_w = (image_data.shape[1] - target_w) // 2
    return image_data[start_h:start_h + target_h, start_w:start_w + target_w]


def ensure_output_dir(output_dir=OUTPUT_DIR):
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def normalize_for_display(values):
    values = numpy.asarray(values, dtype=numpy.float64)
    min_val = values.min()
    max_val = values.max()
    if numpy.isclose(max_val, min_val):
        return numpy.zeros(values.shape, dtype=numpy.float64)
    return (values - min_val) / (max_val - min_val)


def get_blocks(image_data, block_size=BLOCKSIZE):
    if image_data.ndim != 2:
        raise ValueError("image_data must be a 2D array")
    if image_data.shape[0] % block_size != 0 or image_data.shape[1] % block_size != 0:
        raise ValueError("image dimensions must be multiples of block_size")

    blocks = []
    for i in range(0, image_data.shape[0], block_size):
        for j in range(0, image_data.shape[1], block_size):
            blocks.append(image_data[i:i + block_size, j:j + block_size])
    return blocks


def mse(reference, estimate):
    reference = reference.astype(numpy.float64)
    estimate = estimate.astype(numpy.float64)
    return float(numpy.mean((reference - estimate) ** 2))


def psnr(reference, estimate):
    error = mse(reference, estimate)
    if error == 0:
        return float("inf")
    return 20.0 * numpy.log10(255.0 / numpy.sqrt(error))


def run_pipeline(image_path, quality=QUALITY, output_dir=OUTPUT_DIR, block_size=BLOCKSIZE):
    if quality < 1:
        raise ValueError("quality must be >= 1")

    image = Image.open(image_path)
    image_data = numpy.array(image)
    grayscale = RGB_to_Grayscale(image_data)
    padded = pad_image(grayscale, block_size)

    centered = padded.astype(numpy.float64) - 128.0
    dct_coefficients = dct(centered, matrix_size=block_size)
    quantized = quantize(dct_coefficients, quality=quality, block_size=block_size)

    dequantized = reverse_quantize(quantized, quality=quality, block_size=block_size)
    reconstructed_padded = idct(dequantized, matrix_size=block_size) + 128.0
    reconstructed_padded = numpy.clip(reconstructed_padded, 0, 255)
    reconstructed = crop_to_shape(reconstructed_padded, grayscale.shape).astype(numpy.uint8)

    first_block = quantized[0:block_size, 0:block_size]
    zigzag_data = zigzag(first_block)
    rle_data = rle_encode(zigzag_data)

    all_rle_symbols = []
    for i in range(0, quantized.shape[0], block_size):
        for j in range(0, quantized.shape[1], block_size):
            block = quantized[i:i + block_size, j:j + block_size]
            all_rle_symbols.extend(rle_encode(zigzag(block)))

    huffman_data = huffman_encode(all_rle_symbols)
    round_trip = huffman_decode(huffman_data)
    if round_trip != all_rle_symbols:
        raise RuntimeError("Huffman round-trip failed")

    original_bits = int(grayscale.size * 8)
    codebook_overhead_bits = int(len(huffman_data["codes"]) * 32)
    compressed_bits = int(len(huffman_data["bitstring"]) + codebook_overhead_bits)
    compression_ratio = (original_bits / compressed_bits) if compressed_bits > 0 else float("inf")
    gain_percent = (1.0 - (compressed_bits / original_bits)) * 100.0 if original_bits > 0 else 0.0

    return {
        "image_path": image_path,
        "grayscale": grayscale,
        "padded": padded,
        "centered": centered,
        "dct": dct_coefficients,
        "quantized": quantized,
        "reconstructed": reconstructed,
        "quality": quality,
        "original_bits": original_bits,
        "compressed_bits": compressed_bits,
        "compression_ratio": compression_ratio,
        "gain_percent": gain_percent,
        "mse": mse(grayscale, reconstructed),
        "psnr": psnr(grayscale, reconstructed),
        "zigzag": zigzag_data,
        "rle": rle_data,
        "all_rle_symbols": all_rle_symbols,
        "huffman": huffman_data,
        "codebook_overhead_bits": codebook_overhead_bits,
        "output_dir": ensure_output_dir(output_dir),
    }


def save_step_visualizations(pipeline_data, output_dir=OUTPUT_DIR):
    output_dir = ensure_output_dir(output_dir)
    quality = pipeline_data["quality"]

    original = pipeline_data["grayscale"]
    padded = pipeline_data["padded"]
    dct_coefficients = pipeline_data["dct"]
    quantized = pipeline_data["quantized"]
    reconstructed = pipeline_data["reconstructed"]

    plt.figure(figsize=(7, 7))
    plt.imshow(original, cmap="gray", vmin=0, vmax=255)
    plt.title("Image en niveaux de gris")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "original.png"), dpi=160)
    plt.close()

    blocks = get_blocks(padded)
    block_rows = 4
    block_cols = 4
    fig, axes = plt.subplots(block_rows, block_cols, figsize=(8, 8))
    fig.suptitle("Exemple de blocs 8x8")
    for idx, ax in enumerate(axes.flat):
        if idx < len(blocks):
            ax.imshow(blocks[idx], cmap="gray", vmin=0, vmax=255)
            ax.set_title(f"B{idx + 1}", fontsize=8)
        ax.axis("off")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "blocs_exemple.png"), dpi=160)
    plt.close(fig)

    dct_view = numpy.log1p(numpy.abs(dct_coefficients))
    plt.figure(figsize=(7, 7))
    plt.imshow(dct_view, cmap="magma")
    plt.colorbar(fraction=0.046, pad=0.04)
    plt.title("DCT (log(1 + |coeff|))")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "dct_coefficients.png"), dpi=160)
    plt.close()

    plt.figure(figsize=(7, 7))
    plt.imshow(normalize_for_display(quantized), cmap="viridis")
    plt.colorbar(fraction=0.046, pad=0.04)
    plt.title(f"Coefficients quantifies (q={quality})")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "quantifie.png"), dpi=160)
    plt.close()

    plt.figure(figsize=(7, 7))
    plt.imshow(reconstructed, cmap="gray", vmin=0, vmax=255)
    plt.title(f"Reconstruction apres IDCT (q={quality})")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "reconstruction.png"), dpi=160)
    plt.close()

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes[0].imshow(original, cmap="gray", vmin=0, vmax=255)
    axes[0].set_title("Original")
    axes[0].axis("off")
    axes[1].imshow(reconstructed, cmap="gray", vmin=0, vmax=255)
    axes[1].set_title(f"Reconstruction (q={quality})")
    axes[1].axis("off")
    diff = numpy.abs(original.astype(numpy.float64) - reconstructed.astype(numpy.float64))
    axes[2].imshow(diff, cmap="inferno")
    axes[2].set_title("Difference absolue")
    axes[2].axis("off")
    fig.suptitle("Comparaison des etapes")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "comparaison.png"), dpi=160)
    plt.close(fig)


def analyze_qualities(image_path, qualities, output_dir=OUTPUT_DIR):
    if len(qualities) == 0:
        raise ValueError("qualities must not be empty")

    results = []
    for quality in qualities:
        results.append(run_pipeline(image_path=image_path, quality=quality, output_dir=output_dir))

    q_values = [entry["quality"] for entry in results]
    gains = [entry["gain_percent"] for entry in results]
    ratios = [entry["compression_ratio"] for entry in results]
    psnr_values = [entry["psnr"] for entry in results]

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))

    axes[0].plot(q_values, gains, marker="o", color="#005f73")
    axes[0].set_title("Gain (%)")
    axes[0].set_xlabel("Coefficient de quantification")
    axes[0].set_ylabel("Gain (%)")
    axes[0].grid(alpha=0.3)

    axes[1].plot(q_values, ratios, marker="o", color="#ca6702")
    axes[1].set_title("Taux de compression")
    axes[1].set_xlabel("Coefficient de quantification")
    axes[1].set_ylabel("Taux (original/comprime)")
    axes[1].grid(alpha=0.3)

    axes[2].plot(q_values, psnr_values, marker="o", color="#9b2226")
    axes[2].set_title("Qualite (PSNR)")
    axes[2].set_xlabel("Coefficient de quantification")
    axes[2].set_ylabel("PSNR (dB)")
    axes[2].grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(ensure_output_dir(output_dir), "gain_qualites.png"), dpi=170)
    plt.close(fig)

    return results


def find_default_image(cwd):
    supported = {".png", ".jpg", ".jpeg", ".bmp"}
    candidates = []
    for item in sorted(pathlib.Path(cwd).iterdir()):
        if item.is_file() and item.suffix.lower() in supported:
            candidates.append(str(item))
    if len(candidates) == 0:
        raise FileNotFoundError(
            "Aucune image detectee dans le dossier courant. Ajoute un fichier image ou utilise --image"
        )
    return candidates[0]


def parse_quality_list(qualities_text):
    parts = [item.strip() for item in qualities_text.split(",") if item.strip() != ""]
    if len(parts) == 0:
        raise ValueError("qualities list cannot be empty")
    qualities = [int(item) for item in parts]
    if any(q < 1 for q in qualities):
        raise ValueError("all quality values must be >= 1")
    return qualities


def print_results_table(results):
    print("\nResultats de compression:")
    print("q\toriginal_bits\tcompressed_bits\tgain_%\tratio\tPSNR_dB")
    for row in results:
        psnr_value = row["psnr"]
        psnr_text = "inf" if numpy.isinf(psnr_value) else f"{psnr_value:.2f}"
        print(
            f"{row['quality']}\t{row['original_bits']}\t{row['compressed_bits']}"
            f"\t{row['gain_percent']:.2f}\t{row['compression_ratio']:.2f}\t{psnr_text}"
        )


def build_argument_parser():
    parser = argparse.ArgumentParser(description="Mini pipeline JPEG avec visualisations")
    parser.add_argument("--image", type=str, default=None, help="Chemin image (png/jpg/jpeg/bmp)")
    parser.add_argument("--output", type=str, default=OUTPUT_DIR, help="Dossier de sortie")
    parser.add_argument(
        "--qualities",
        type=str,
        default="1,3,5,8,12",
        help="Liste de coefficients de quantification, separes par des virgules",
    )
    parser.add_argument(
        "--main-quality",
        type=int,
        default=QUALITY,
        help="Coefficient utilise pour les visualisations detaillees",
    )
    return parser


def main():
    parser = build_argument_parser()
    args = parser.parse_args()

    image_path = args.image if args.image is not None else find_default_image(os.getcwd())
    qualities = parse_quality_list(args.qualities)
    if args.main_quality < 1:
        raise ValueError("main-quality must be >= 1")

    detailed = run_pipeline(image_path=image_path, quality=args.main_quality, output_dir=args.output)
    save_step_visualizations(detailed, output_dir=args.output)

    all_qualities = sorted(set(qualities + [args.main_quality]))
    results = analyze_qualities(image_path=image_path, qualities=all_qualities, output_dir=args.output)

    print(f"Image source : {image_path}")
    print(f"Sorties enregistrees dans : {args.output}")
    print_results_table(results)


if __name__ == "__main__":
    main()
