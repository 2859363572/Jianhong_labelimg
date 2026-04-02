import numpy as np
import struct


def image_hash_gray(img_path, hash_size=8):
    from PIL import Image
    img = Image.open(img_path).convert('L')
    img = img.resize((hash_size + 1, hash_size), Image.LANCZOS)
    pixels = np.array(img, dtype=np.float64)
    diff = pixels[:, 1:] > pixels[:, :-1]
    flat = diff.flatten()
    bits = 0
    for bit in flat:
        bits = (bits << 1) | int(bit)
    return bits


def hash_distance(h1, h2):
    x = h1 ^ h2
    count = 0
    while x:
        count += 1
        x &= x - 1
    return count


def hash_similarity(h1, h2):
    dist = hash_distance(h1, h2)
    return 1.0 - dist / 64.0


def pixel_similarity_fast(img_path1, img_path2, sample_size=64):
    from PIL import Image
    img1 = Image.open(img_path1).convert('L').resize((sample_size, sample_size), Image.LANCZOS)
    img2 = Image.open(img_path2).convert('L').resize((sample_size, sample_size), Image.LANCZOS)
    arr1 = np.array(img1, dtype=np.float32).flatten()
    arr2 = np.array(img2, dtype=np.float32).flatten()
    arr1 = arr1 / 255.0
    arr2 = arr2 / 255.0
    similarity = 1.0 - np.mean(np.abs(arr1 - arr2))
    return float(similarity)


def find_similar_range(img_list, start_idx, threshold=0.85, max_range=500):
    if start_idx >= len(img_list) - 1:
        return 0, 0

    try:
        base_hash = image_hash_gray(img_list[start_idx])
    except Exception:
        return 0, 0

    end_idx = start_idx
    for i in range(start_idx + 1, min(len(img_list), start_idx + max_range + 1)):
        try:
            h = image_hash_gray(img_list[i])
            sim = hash_similarity(base_hash, h)
            if sim >= threshold:
                end_idx = i
            else:
                break
        except Exception:
            break

    count = end_idx - start_idx
    return count, 0
