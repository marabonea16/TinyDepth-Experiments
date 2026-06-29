"""Testeaza checkpoint-ul NoGate-Test in ambele moduri (gate_depth_input
True/False) pe KITTI clean si pe un subset de vreme reala din KITTI-C,
ca sa vedem daca suprimarea (pornita doar la inferenta) recupereaza
beneficiul de robustete fara sa coste pe curat."""
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

WEIGHTS = "models/URW-Depth-NoGate-Test/models/weights_1"
HEIGHT, WIDTH = 192, 640
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
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


from layer import upsample  # noqa (asigura ca modulele layer sunt incarcate)


def predict_both_modes(data_path):
    """gate OFF: disp=sigmoid(dispconv(d)) (ca la antrenare).
    gate ON (pur, fara capul de corupie): disp=sigmoid(dispconv(d*(1-sigma))),
    formula originala Fix4 - bypass complet g (care e colapsat ~0 aici,
    netrenat in acest run)."""
    dataset = datasets.KITTIRAWDataset(data_path, filenames, HEIGHT, WIDTH, [0], 4,
                                        is_train=False, img_ext=".png")
    loader = DataLoader(dataset, 16, shuffle=False, num_workers=4)
    preds = {"on": [], "off": []}
    with torch.no_grad():
        for data in loader:
            inp = data[("color_MiS", 0, 0)].to(device)
            feats = encoder(inp)

            decoder.gate_depth_input = False
            out = decoder(feats, raw_image=inp)
            disp, _ = disp_to_depth(out[("disp", 0)][:, 0:1], 0.1, 100.0)
            preds["off"].append(disp.cpu()[:, 0].numpy())

            sigma = torch.sigmoid(out[("uncert", 0)])
            d = decoder._last_d
            d_refined = d * (1.0 - sigma)
            disp_on = torch.sigmoid(decoder.convs[("dispconv", 0)](d_refined))
            disp_on, _ = disp_to_depth(disp_on[:, 0:1], 0.1, 100.0)
            preds["on"].append(disp_on.cpu()[:, 0].numpy())
    return {k: np.concatenate(v) for k, v in preds.items()}


print("=== KITTI clean ===")
preds = predict_both_modes("/home/ubuntu/TinyDepth")
print(f"suprimare PURA (d*(1-sigma)): abs_rel={run_eval(preds['on']):.4f}")
print(f"fara suprimare (ca la antrenare): abs_rel={run_eval(preds['off']):.4f}")

for corr in ["fog", "snow", "frost", "brightness", "contrast"]:
    data_path = f"/home/ubuntu/TinyDepth/kitti_c/kitti_c/{corr}/3/kitti_data"
    if not os.path.isdir(data_path):
        continue
    print(f"\n=== {corr} (severitate 3) ===")
    preds = predict_both_modes(data_path)
    print(f"suprimare PURA (d*(1-sigma)): abs_rel={run_eval(preds['on']):.4f}")
    print(f"fara suprimare (ca la antrenare): abs_rel={run_eval(preds['off']):.4f}")
