"""
Genereaza heatmap-uri de adancime pentru imagini proprii, cu URW-Depth-S2.
"""
import os
import sys
import cv2
import numpy as np
import torch

sys.path.insert(0, os.path.dirname(__file__))
from networks.configuration import get_config
import networks
from layer import disp_to_depth

device = torch.device("cpu")
HEIGHT, WIDTH = 192, 640

IMAGES = [
    "/home/ubuntu/Downloads/1.jpeg",
    "/home/ubuntu/Downloads/2.jpeg",
    "/home/ubuntu/Downloads/3.jpeg",
]
OUT_DIR = "/home/ubuntu/TinyDepth/user_heatmaps"
os.makedirs(OUT_DIR, exist_ok=True)

class _Opt:
    img_height = HEIGHT
    img_width = WIDTH
    encoder = "tiny_vit_5m_22k_distill"
    scales = [0]

config = get_config(_Opt())
encoder = networks.build_model(config, img_width=WIDTH, img_height=HEIGHT)
enc_dict = torch.load("models/URW-Depth-S2/models/weights_14/encoder.pth", map_location=device)
model_dict = encoder.state_dict()
encoder.load_state_dict({k: v for k, v in enc_dict.items() if k in model_dict})

decoder = networks.FusionDecoder([64, 64, 128, 160, 320], use_feature_suppression=True)
decoder.load_state_dict(
    torch.load("models/URW-Depth-S2/models/weights_14/depth.pth", map_location=device), strict=False)

encoder.to(device).eval()
decoder.to(device).eval()

for idx, img_path in enumerate(IMAGES, start=1):
    img = cv2.imread(img_path)
    if img is None:
        print(f"  [SKIP] nu pot citi {img_path}")
        continue
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    orig_h, orig_w = img_rgb.shape[:2]
    img_resized = cv2.resize(img_rgb, (WIDTH, HEIGHT))
    inp = torch.from_numpy(img_resized / 255.0).permute(2, 0, 1).unsqueeze(0).float()

    with torch.no_grad():
        out = decoder(encoder(inp))
        disp, _ = disp_to_depth(out[("disp", 0)][:, 0:1], 0.1, 100.0)
        disp_np = disp[0, 0].numpy()

    disp_full = cv2.resize(disp_np, (orig_w, orig_h))
    disp_norm = (disp_full - disp_full.min()) / (disp_full.max() - disp_full.min() + 1e-8)
    heatmap = cv2.applyColorMap((disp_norm * 255).astype(np.uint8), cv2.COLORMAP_MAGMA)
    heatmap_rgb = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)

    side_by_side = np.concatenate([img_rgb, cv2.cvtColor(heatmap_rgb, cv2.COLOR_RGB2BGR)], axis=1)
    out_path = os.path.join(OUT_DIR, f"{idx}_heatmap.png")
    out_path_combined = os.path.join(OUT_DIR, f"{idx}_side_by_side.png")
    cv2.imwrite(out_path, cv2.cvtColor(heatmap_rgb, cv2.COLOR_RGB2BGR))
    cv2.imwrite(out_path_combined, side_by_side)
    print(f"  salvat: {out_path} si {out_path_combined}")

print("-> Done!")
