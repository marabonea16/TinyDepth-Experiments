"""Sweep peste gate_temperature (ascute g spre 0/1 fara hard-threshold),
evaluat pe KITTI clean (eigen) si pe vreme reala din KITTI-C (severitate 3),
fara reantrenare - reutilizeaza logica din evaluate_kitti_c.py pentru
alinierea corecta cu ground truth."""
import os
import sys
import cv2
import numpy as np
import torch
from torch.utils.data import DataLoader

sys.path.insert(0, os.path.dirname(__file__))
from networks.configuration import get_config
from layer import disp_to_depth
from utils import readlines
import datasets
import networks
from evaluate_depth import compute_errors, splits_dir

WEIGHTS = "models/URW-Depth-Calib-Diag15/models/weights_6"
HEIGHT, WIDTH = 192, 640
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
TEMPERATURES = [1.0, 2.0, 3.0, 5.0, 8.0]
MIN_DEPTH, MAX_DEPTH = 1e-3, 80.0

config = get_config(type("O", (), {"img_height": HEIGHT, "img_width": WIDTH,
                                    "encoder": "tiny_vit_5m_22k_distill", "scales": [0]}))
encoder = networks.build_model(config, img_width=WIDTH, img_height=HEIGHT)
enc_dict = torch.load(os.path.join(WEIGHTS, "encoder.pth"), map_location=device)
md = encoder.state_dict()
encoder.load_state_dict({k: v for k, v in enc_dict.items() if k in md})

decoder = networks.FusionDecoder([64, 64, 128, 160, 320], use_feature_suppression=True)
decoder.load_state_dict(torch.load(os.path.join(WEIGHTS, "depth.pth"), map_location=device), strict=False)
encoder.to(device).eval()
decoder.to(device).eval()

gt_path = os.path.join(splits_dir, "eigen", "gt_depths.npz")
gt_depths = np.load(gt_path, fix_imports=True, encoding="latin1", allow_pickle=True)["data"]
filenames = readlines(os.path.join(splits_dir, "eigen", "test_files.txt"))


def run_eval(pred_disps):
    errors = []
    for i in range(pred_disps.shape[0]):
        gt_depth = gt_depths[i]
        if gt_depth is None:
            continue
        gt_h, gt_w = gt_depth.shape
        pred_depth = 1.0 / cv2.resize(pred_disps[i], (gt_w, gt_h))
        mask = np.logical_and(gt_depth > MIN_DEPTH, gt_depth < MAX_DEPTH)
        crop = np.array([0.40810811 * gt_h, 0.99189189 * gt_h,
                          0.03594771 * gt_w, 0.96405229 * gt_w]).astype(np.int32)
        crop_mask = np.zeros(mask.shape)
        crop_mask[crop[0]:crop[1], crop[2]:crop[3]] = 1
        mask = np.logical_and(mask, crop_mask)
        if mask.sum() == 0:
            continue
        pd, gd = pred_depth[mask], gt_depth[mask]
        ratio = np.median(gd) / np.median(pd)
        pd = np.clip(pd * ratio, MIN_DEPTH, MAX_DEPTH)
        errors.append(compute_errors(gd, pd))
    return np.array(errors).mean(0)[0]


def predict_all_temps(data_path):
    dataset = datasets.KITTIRAWDataset(data_path, filenames, HEIGHT, WIDTH, [0], 4,
                                        is_train=False, img_ext=".png")
    loader = DataLoader(dataset, 16, shuffle=False, num_workers=4)
    preds = {T: [] for T in TEMPERATURES}
    with torch.no_grad():
        for data in loader:
            inp = data[("color_MiS", 0, 0)].to(device)
            feats = encoder(inp)
            for T in TEMPERATURES:
                decoder.gate_temperature = T
                out = decoder(feats, raw_image=inp)
                disp, _ = disp_to_depth(out[("disp", 0)][:, 0:1], 0.1, 100.0)
                preds[T].append(disp.cpu()[:, 0].numpy())
    return {T: np.concatenate(v) for T, v in preds.items()}


print("=== KITTI clean ===")
clean_preds = predict_all_temps("/home/ubuntu/TinyDepth")
for T in TEMPERATURES:
    print(f"T={T}: clean abs_rel={run_eval(clean_preds[T]):.4f}")

for corr in ["fog", "snow", "frost", "brightness", "contrast"]:
    data_path = f"/home/ubuntu/TinyDepth/kitti_c/kitti_c/{corr}/3/kitti_data"
    if not os.path.isdir(data_path):
        print(f"{corr}: director inexistent, skip")
        continue
    print(f"\n=== {corr} (severitate 3) ===")
    preds = predict_all_temps(data_path)
    for T in TEMPERATURES:
        print(f"T={T}: {corr} abs_rel={run_eval(preds[T]):.4f}")
