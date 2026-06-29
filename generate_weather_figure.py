"""
Genereaza un tabel-figura cu toate cele 6 augmentari (ceata/ploaie/zapada +
contrast/luminozitate/inghet) la severitati crescatoare, cu etichete text
pentru numele degradarii (rand) si severitate (coloana), pentru figura din
Capitolul 3 (augmentare de date) a lucrarii.

Foloseste functiile REALE de antrenare din datasets/mono_dataset.py, nu
versiunile din hf_space (care difera usor si nu includ cele 3 noi).

Output: weather_figures/tabel_augmentari.png
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from datasets.mono_dataset import (
    apply_fog, apply_rain, apply_snow,
    apply_contrast, apply_brightness_shift, apply_frost_like,
    apply_defocus_blur, apply_motion_blur, apply_gaussian_noise,
    apply_shot_noise, apply_jpeg_compression,
)

SAMPLE_IMG = "kitti_c/kitti_c/clean/kitti_data/2011_09_26/2011_09_26_drive_0009_sync/image_02/data/0000000000.png"
OUT_DIR = "weather_figures"
os.makedirs(OUT_DIR, exist_ok=True)

SEVERITIES = [0.0, 0.25, 0.45, 0.65, 0.85]
ROWS_METEO = [
    ("Ceata", apply_fog),
    ("Ploaie", apply_rain),
    ("Zapada", apply_snow),
    ("Contrast redus", apply_contrast),
    ("Luminozitate crescuta", apply_brightness_shift),
    ("Inghet (frost)", apply_frost_like),
]

ROWS_VIZUALE = [
    ("Defocus blur", apply_defocus_blur),
    ("Motion blur", apply_motion_blur),
    ("Zgomot gaussian", apply_gaussian_noise),
    ("Shot noise", apply_shot_noise),
    ("Compresie JPEG", apply_jpeg_compression),
]

LABEL_W = 340       # latime banda de eticheta randuri (stanga)
HEADER_H = 50        # inaltime banda de eticheta coloane (sus)
FONT_SIZE = 20


def get_font(size):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if os.path.isfile(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def build_table(img, rows, out_name):
    w, h = img.size
    font = get_font(FONT_SIZE)

    n_rows, n_cols = len(rows), len(SEVERITIES)
    canvas_w = LABEL_W + n_cols * w
    canvas_h = HEADER_H + n_rows * h
    canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    # antet coloane: severitate
    for j, sev in enumerate(SEVERITIES):
        label = "curat" if sev == 0.0 else f"sev={sev:.2f}"
        x = LABEL_W + j * w + w // 2
        draw.text((x, HEADER_H // 2), label, fill=(0, 0, 0), font=font, anchor="mm")

    # randuri: imagine + eticheta nume degradare
    for i, (name, fn) in enumerate(rows):
        y = HEADER_H + i * h
        draw.text((LABEL_W // 2, y + h // 2), name, fill=(0, 0, 0), font=font, anchor="mm")
        for j, sev in enumerate(SEVERITIES):
            out_img = img if sev == 0.0 else fn(img, sev)
            x = LABEL_W + j * w
            canvas.paste(out_img, (x, y))

    out_path = os.path.join(OUT_DIR, out_name)
    canvas.save(out_path)
    print(f"-> tabel salvat: {out_path} ({canvas_w}x{canvas_h})")


def main():
    img = Image.open(SAMPLE_IMG).convert("RGB")
    build_table(img, ROWS_METEO, "tabel_augmentari.png")
    build_table(img, ROWS_VIZUALE, "tabel_degradari_vizuale.png")


if __name__ == "__main__":
    main()
