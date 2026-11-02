"""P11-4a: flattens the low-frequency tone of the Poly Haven medieval_blocks_03 colour map (numpy + PIL only).

Works in linear light. grey = mean(R, G, B); low = grey blurred with a wrapped Gaussian (sigma 100 px, FFT, seamless at the edges);
every channel is multiplied by grey.mean() / max(low, 0.001), then converted back to sRGB and clipped.
Prints the low-frequency figure (grey blurred with sigma 60, wrapped; std / mean) for the input and the output.

Usage: python make_flat_blocks.py
"""
import os

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SRC = os.path.join(ROOT, "ExternalAssets", "Incoming", "polyhaven-medieval_blocks_03", "polyhaven-medieval_blocks_03",
                   "medieval_blocks_03_diff_2k.jpg")
OUT = os.path.join(ROOT, "SourceArt", "P11", "T_P11_FlatBlocks_BC.png")
SIGMA_FLAT = 100.0
SIGMA_METRIC = 60.0


def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1.0 / 2.4) - 0.055)


def wrapped_blur(img, sigma):
    h, w = img.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    g = np.exp(-2 * (np.pi * sigma) ** 2 * (fx * fx + fy * fy))
    return np.fft.irfft2(np.fft.rfft2(img) * g, s=img.shape)


def low_freq_figure(rgb):
    grey = rgb.mean(axis=2)
    low = wrapped_blur(grey, SIGMA_METRIC)
    return float(low.std() / low.mean())


def main():
    src = np.asarray(Image.open(SRC).convert("RGB"), dtype=np.float64) / 255.0
    rgb = srgb_to_linear(src)
    grey = rgb.mean(axis=2)
    low = wrapped_blur(grey, SIGMA_FLAT)
    out = rgb * (grey.mean() / np.maximum(low, 0.001))[..., None]
    out_srgb = np.clip(linear_to_srgb(out), 0.0, 1.0)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    Image.fromarray(np.round(out_srgb * 255.0).astype(np.uint8), "RGB").save(OUT)
    # figure for the saved (8-bit) result, so it matches what Unreal imports
    saved = srgb_to_linear(np.asarray(Image.open(OUT).convert("RGB"), dtype=np.float64) / 255.0)
    print("input  %s  size %s" % (SRC, src.shape[:2][::-1]))
    print("output %s" % OUT)
    print("low-frequency figure (sigma %g blur, std/mean of grey): input %.4f, output %.4f" % (
        SIGMA_METRIC, low_freq_figure(rgb), low_freq_figure(saved)))
    print("mean linear grey: input %.4f, output %.4f" % (grey.mean(), saved.mean(axis=2).mean()))


if __name__ == "__main__":
    main()
