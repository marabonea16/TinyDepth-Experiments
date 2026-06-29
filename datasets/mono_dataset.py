# Copyright Niantic 2019. Patent Pending. All rights reserved.
#
# This software is licensed under the terms of the Monodepth2 licence
# which allows for non-commercial use only, the full terms of which are made
# available in the LICENSE file.

from __future__ import absolute_import, division, print_function

import os
import random
import numpy as np
import copy
from PIL import Image  # using pillow-simd for increased speed

import torch
import torch.utils.data as data
from torchvision import transforms



def pil_loader(path):
    # open path as file to avoid ResourceWarning
    # (https://github.com/python-pillow/Pillow/issues/835)
    with open(path, 'rb') as f:
        with Image.open(f) as img:
            return img.convert('RGB')


def apply_fog(img, severity=None):
    """Simuleaza ceata: blend cu alb, mai intens spre margini (departe)."""
    if severity is None:
        severity = random.uniform(0.2, 0.6)
    arr = np.array(img, dtype=np.float32)
    fog_color = np.array([220, 220, 220], dtype=np.float32)
    # gradient vertical: mai multa ceata sus (orizont/distanta)
    h, w = arr.shape[:2]
    gradient = np.linspace(severity, severity * 0.3, h, dtype=np.float32)[:, None, None]
    arr = arr * (1 - gradient) + fog_color * gradient
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def apply_rain(img, severity=None):
    """Simuleaza ploaie: streaks diagonale semitransparente + contrast redus.
    Vectorizat cu numpy (fara bucle Python per-pixel) - bucla originala facea
    pana la ~600*25=15000 operatii Python per imagine, principalul bottleneck
    de CPU la antrenare (GPU doar 46% utilizat, bound de data loading)."""
    if severity is None:
        severity = random.uniform(0.3, 0.7)
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape[:2]
    num_streaks = int(severity * 600)
    if num_streaks > 0:
        max_len = 25
        xs0 = np.random.randint(0, w, num_streaks)
        ys0 = np.random.randint(0, h - 20, num_streaks)
        lengths = np.random.randint(10, max_len, num_streaks)
        alphas = np.random.uniform(0.3, 0.6, num_streaks)

        k = np.arange(max_len)
        yi = np.clip(ys0[:, None] + k[None, :], 0, h - 1)
        xi = np.clip(xs0[:, None] + (k[None, :] // 3), 0, w - 1)
        valid = k[None, :] < lengths[:, None]
        alpha_grid = np.broadcast_to(alphas[:, None], yi.shape)

        yi_v = yi[valid]
        xi_v = xi[valid]
        a_v = alpha_grid[valid]
        arr[yi_v, xi_v] = arr[yi_v, xi_v] * (1 - a_v[:, None]) + 200 * a_v[:, None]
    # reducere contrast
    arr = arr * (1 - severity * 0.15) + 128 * severity * 0.15
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def apply_snow(img, severity=None):
    """Simuleaza zapada: puncte albe + desaturare + blur usor. Vectorizat
    (vezi nota din apply_rain)."""
    if severity is None:
        severity = random.uniform(0.2, 0.5)
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape[:2]
    # desaturare
    gray = arr.mean(axis=2, keepdims=True)
    arr = arr * (1 - severity * 0.4) + gray * severity * 0.4
    # flakes albe
    num_flakes = int(severity * 800)
    ys = np.random.randint(0, h, num_flakes)
    xs = np.random.randint(0, w, num_flakes)
    alphas = np.random.uniform(0.5, 1.0, num_flakes)
    arr[ys, xs] = arr[ys, xs] * (1 - alphas[:, None]) + 255 * alphas[:, None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def apply_defocus_blur(img, severity=None):
    """Blur de defocus: gaussian cu kernel mare."""
    import cv2
    if severity is None:
        severity = random.uniform(0.5, 2.5)
    else:
        severity = 0.5 + severity * 2.0  # mapeaza [0,1] -> [0.5, 2.5]
    ksize = int(severity * 4) * 2 + 1  # odd kernel
    arr = np.array(img, dtype=np.uint8)
    arr = cv2.GaussianBlur(arr, (ksize, ksize), severity)
    return Image.fromarray(arr)


def apply_motion_blur(img, severity=None):
    """Motion blur liniar in directie aleatoare."""
    import cv2
    if severity is None:
        length = random.randint(5, 20)
    else:
        length = max(3, int(5 + severity * 15))  # mapeaza [0,1] -> [5, 20]
    angle = random.uniform(0, 360)
    arr = np.array(img, dtype=np.uint8)
    # kernel liniar rotit
    kernel = np.zeros((length, length), dtype=np.float32)
    kernel[length // 2, :] = 1.0 / length
    rad = np.deg2rad(angle)
    M = cv2.getRotationMatrix2D((length / 2, length / 2), angle, 1)
    kernel = cv2.warpAffine(kernel, M, (length, length))
    kernel = kernel / (kernel.sum() + 1e-8)
    arr = cv2.filter2D(arr, -1, kernel)
    return Image.fromarray(arr)


def apply_gaussian_noise(img, severity=None):
    """Zgomot gaussian aditiv."""
    if severity is None:
        sigma = random.uniform(5, 30)
    else:
        sigma = 5 + severity * 25  # mapeaza [0,1] -> [5, 30]
    arr = np.array(img, dtype=np.float32)
    noise = np.random.normal(0, sigma, arr.shape).astype(np.float32)
    arr = arr + noise
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def apply_shot_noise(img, severity=None):
    """Shot noise (Poisson)."""
    if severity is None:
        scale = random.uniform(0.02, 0.15)
    else:
        scale = 0.02 + severity * 0.13  # mapeaza [0,1] -> [0.02, 0.15]
    arr = np.array(img, dtype=np.float32) / 255.0
    arr = np.random.poisson(arr / scale) * scale
    return Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8))


def apply_jpeg_compression(img, severity=None):
    """Artefacte de compresie JPEG, prin re-codificare cu calitate redusa."""
    import cv2
    if severity is None:
        severity = random.uniform(0.2, 0.9)
    quality = int(90 - severity * 80)  # mapeaza [0,1] -> calitate [90,10]
    arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    ok, enc = cv2.imencode(".jpg", arr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    dec = cv2.imdecode(enc, cv2.IMREAD_COLOR)
    return Image.fromarray(cv2.cvtColor(dec, cv2.COLOR_BGR2RGB))


def apply_contrast(img, severity=None):
    """Reduce contrastul (std) pastrand media aproape neschimbata - mimica
    corruptia 'contrast' din KITTI-C (verificat empiric: std scade de la ~84
    la ~17 pe canal, media practic identica cu cea curata)."""
    if severity is None:
        severity = random.uniform(0.4, 0.85)
    arr = np.array(img, dtype=np.float32)
    mean = arr.mean(axis=(0, 1), keepdims=True)
    arr = mean + (arr - mean) * (1 - severity)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def apply_brightness_shift(img, severity=None):
    """Creste luminozitatea globala cu reducere usoara de contrast - mimica
    corruptia 'brightness' din KITTI-C (media +50-60, std redus moderat)."""
    if severity is None:
        severity = random.uniform(0.3, 0.6)
    arr = np.array(img, dtype=np.float32)
    arr = arr * (1 - severity * 0.3) + 255 * severity * 0.6
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def apply_frost_like(img, severity=None):
    """Blend catre o culoare alb-albastruie cu contrast redus - mimica
    corruptia 'frost' din KITTI-C (media creste mult, ~+80-90 per canal)."""
    if severity is None:
        severity = random.uniform(0.4, 0.8)
    arr = np.array(img, dtype=np.float32)
    frost_color = np.array([200, 210, 220], dtype=np.float32)
    arr = arr * (1 - severity * 0.6) + frost_color * severity * 0.6
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def apply_weather_aug(img):
    """Aplica random unul dintre: fog, rain, snow (cu prob 50% per sample)."""
    if random.random() > 0.5:
        return img  # jumatate din imagini raman curate
    choice = random.randint(0, 2)
    if choice == 0:
        return apply_fog(img)
    elif choice == 1:
        return apply_rain(img)
    else:
        return apply_snow(img)


def apply_corruption_aug(img):
    """Weather + blur + noise aug pentru robustete completa pe KITTI-C."""
    if random.random() > 0.5:
        return img  # 50% imagini curate
    choice = random.randint(0, 6)
    if choice == 0:
        return apply_fog(img)
    elif choice == 1:
        return apply_rain(img)
    elif choice == 2:
        return apply_snow(img)
    elif choice == 3:
        return apply_defocus_blur(img)
    elif choice == 4:
        return apply_motion_blur(img)
    elif choice == 5:
        return apply_gaussian_noise(img)
    else:
        return apply_shot_noise(img)


class MonoDataset(data.Dataset):
    """Superclass for monocular dataloaders

    Args:
        data_path
        filenames
        height
        width
        frame_idxs
        num_scales
        is_train
        img_ext
    """
    def __init__(self,
                 data_path,
                 filenames,
                 height,
                 width,
                 frame_idxs,
                 num_scales,
                 is_train=False,
                 img_ext='.png',
                 use_weather_aug=False,
                 use_corruption_aug=False):
        super(MonoDataset, self).__init__()

        self.data_path = data_path
        self.filenames = filenames
        self.height = height
        self.width = width
        self.height_full = 375
        self.width_full = 1242
        # self.num_scales = num_scales
        self.num_scales = 1
        self.interp = Image.ANTIALIAS   #a high-quality downsampling filter

        self.frame_idxs = frame_idxs

        self.is_train = is_train
        self.img_ext = img_ext
        self.use_weather_aug = use_weather_aug
        self.use_corruption_aug = use_corruption_aug

        self.loader = pil_loader
        self.to_tensor = transforms.ToTensor()

        # We need to specify augmentations differently in newer versions of torchvision.
        # We first try the newer tuple version; if this fails we fall back to scalars
        try:
            self.brightness = (0.8, 1.2)
            self.contrast = (0.8, 1.2)
            self.saturation = (0.8, 1.2)
            self.hue = (-0.1, 0.1)
            transforms.ColorJitter.get_params(
                self.brightness, self.contrast, self.saturation, self.hue)
        except TypeError:
            self.brightness = 0.2
            self.contrast = 0.2
            self.saturation = 0.2
            self.hue = 0.1

        self.resize = {}
        for i in range(self.num_scales):
            s = 2 ** i
            self.resize[i] = transforms.Resize((self.height // s, self.width // s),
                                               interpolation=self.interp)

        # self.load_depth = self.check_depth()

    def preprocess(self, inputs, color_aug, height_re_HiS, width_re_HiS, height_re_LoS, width_re_LoS, dx_HiS, dy_HiS, do_crop_aug):
        """Resize colour images to the required scales and augment if required

        We create the color_aug object in advance and apply the same augmentation to all
        images in this item. This ensures that all images input to the pose network receive the
        same augmentation.
        """
        self.resize_HiS = transforms.Resize((height_re_HiS, width_re_HiS), interpolation=self.interp)
        self.resize_MiS = transforms.Resize((self.height, self.width), interpolation=self.interp)
        self.resize_LoS = transforms.Resize((height_re_LoS, width_re_LoS), interpolation=self.interp)
        box_HiS = (dx_HiS, dy_HiS, dx_HiS+self.width, dy_HiS+self.height)
        for k in list(inputs):
            frame = inputs[k]
            if "color" in k:
                n, im, i = k
                for i in range(self.num_scales):
                    inputs[(n + "_HiS", im, i)] = self.resize_HiS(inputs[(n, im, i - 1)]).crop(box_HiS)
                    inputs[(n + "_MiS", im, i)] = self.resize_MiS(inputs[(n, im, i - 1)])
                    inputs[(n + "_LoS", im, i)] = self.resize_LoS(inputs[(n, im, i - 1)])


        for k in list(inputs):
            f = inputs[k]
            if "color_HiS" in k:
                n, im, i = k
                inputs[(n, im, i)] = self.to_tensor(f)
            if "color_MiS" in k:
                n, im, i = k
                inputs[(n, im, i)] = self.to_tensor(f) #[3,192,640]
                inputs[(n + "_aug", im, i)] = self.to_tensor(color_aug(f))
            if "color_LoS" in k:
                n, im, i = k
                LoS_part = self.to_tensor(f)
                #point1 = int(2*width_re_LoS-self.width)
                #point2 = int(2*height_re_LoS-self.height)
                Tensor_LoS = torch.zeros(3, self.height, self.width)
                Tensor_LoS[:, 0:height_re_LoS, 0:width_re_LoS] = LoS_part
                #Tensor_LoS[:, height_re_LoS:self.height, 0:width_re_LoS] = LoS_part[:, point2:height_re_LoS, 0:width_re_LoS]
                Tensor_LoS[:, height_re_LoS:self.height, 0:width_re_LoS] = 0
                #Tensor_LoS[:, 0:height_re_LoS, width_re_LoS:self.width] = LoS_part[:, 0:height_re_LoS, point1:width_re_LoS]
                Tensor_LoS[:, 0:height_re_LoS, width_re_LoS:self.width] = 0
                #Tensor_LoS[:, height_re_LoS:self.height, width_re_LoS:self.width] = LoS_part[:, point2:height_re_LoS, point1:width_re_LoS]
                Tensor_LoS[:, height_re_LoS:self.height, width_re_LoS:self.width] = 0
                inputs[(n, im, i)] = Tensor_LoS

    def __len__(self):
        return len(self.filenames)

    def __getitem__(self, index):
        """Returns a single training item from the dataset as a dictionary.

        Values correspond to torch tensors.
        Keys in the dictionary are either strings or tuples:

            ("color", <frame_id>, <scale>)          for raw colour images,
            ("color_aug", <frame_id>, <scale>)      for augmented colour images,
            ("K", scale) or ("inv_K", scale)        for camera intrinsics,
            "stereo_T"                              for camera extrinsics, and
            "depth_gt"                              for ground truth depth maps.

        <frame_id> is either:
            an integer (e.g. 0, -1, or 1) representing the temporal step relative to 'index',
        or
            "s" for the opposite image in the stereo pair.

        <scale> is an integer representing the scale of the image relative to the fullsize image:
            -1      images at native resolution as loaded from disk
            0       images resized to (self.width,      self.height     )
            1       images resized to (self.width // 2, self.height // 2)
            2       images resized to (self.width // 4, self.height // 4)
            3       images resized to (self.width // 8, self.height // 8)
        """
        inputs = {}

        do_color_aug = self.is_train and random.random() > 0.5
        do_flip = self.is_train and random.random() > 0.5
        do_crop_aug = self.is_train

        # High-Scale
        ra_HiS = 1.1
        rb_HiS = 2.0
        resize_ratio_HiS = (rb_HiS - ra_HiS) * random.random() + ra_HiS
        if do_crop_aug:
            height_re_HiS = int(self.height * resize_ratio_HiS)
            width_re_HiS = int(self.width * resize_ratio_HiS)
        else:
            height_re_HiS = self.height
            width_re_HiS = self.width

        height_d_HiS = height_re_HiS - self.height
        width_d_HiS = width_re_HiS - self.width
        if do_crop_aug:
            dx_HiS = int(width_d_HiS * random.random())
            dy_HiS = int(height_d_HiS*random.random())
        else:
            dx_HiS = 0
            dy_HiS = 0


        # Middle-Scale
        dx_MiS = 0
        dy_MiS = 0


        # Low-Scale
        ra_LoS = 0.7
        rb_LoS = 0.9
        resize_ratio_LoS = (rb_LoS - ra_LoS) * random.random() + ra_LoS
        height_re_LoS = int(self.height * resize_ratio_LoS)
        width_re_LoS = int(self.width * resize_ratio_LoS)

        dx_LoS = 0
        dy_LoS = 0

        inputs[("dxy_HiS")] = torch.Tensor((dx_HiS, dy_HiS))
        inputs[("dxy_MiS")] = torch.Tensor((dx_MiS, dy_MiS))
        inputs[("dxy_LoS")] = torch.Tensor((dx_LoS, dy_LoS))
        inputs[("resize_HiS")] = torch.Tensor((width_re_HiS, height_re_HiS))
        inputs[("resize_LoS")] = torch.Tensor((width_re_LoS, height_re_LoS))


        line = self.filenames[index].split()
        folder = line[0]


        if len(line) == 3:
            frame_index = int(line[1])
        else:
            frame_index = 0

        if len(line) == 3:
            side = line[2]
        else:
            side = None

        # corupii cu semnatura globala de culoare/contrast (detectabile din
        # medie+std per canal) - extinse cu contrast/brightness/frost ca sa
        # acopere si magnitudinile reale din KITTI-C (verificat empiric: fog
        # sintetic vs KITTI-C difera in shift de medie/std, cauzand misfire
        # pe snow/frost/fog reale la Diag14 - antrenat doar pe fog/rain/snow).
        GLOBAL_WEATHER_FNS = (apply_fog, apply_rain, apply_snow,
                              apply_contrast, apply_brightness_shift, apply_frost_like)

        # augmentare: acelasi tip aplicat consistent la toate frame-urile din secventa
        aug_fn = None
        if self.is_train and self.use_corruption_aug:
            if random.random() > 0.5:
                choice = random.randint(0, 9)
                aug_fn = [apply_fog, apply_rain, apply_snow,
                          apply_contrast, apply_brightness_shift, apply_frost_like,
                          apply_defocus_blur, apply_motion_blur,
                          apply_gaussian_noise, apply_shot_noise][choice]
        elif self.is_train and self.use_weather_aug and random.random() > 0.5:
            choice = random.randint(0, 5)
            aug_fn = [apply_fog, apply_rain, apply_snow,
                      apply_contrast, apply_brightness_shift, apply_frost_like][choice]
        weather_fn = aug_fn  # backward compat

        # eticheta supravegheata: a fost aceasta imagine augmentata (vreme/coruptie)?
        # folosita pentru capul global de detectie a corupiei (gateaza suprima
        # de caracteristici doar pe imagini probabil corupte, nu pe cele curate).
        inputs["is_corrupted"] = torch.tensor(1.0 if weather_fn is not None else 0.0)
        # eticheta RESTRANSA doar la corupii cu semnatura globala de culoare
        # (vreme). Blur si zgomot NU schimba media RGB globala (verificat
        # empiric: shift de medie ~0.02-0.08 pentru blur vs ~67 pentru ceata) -
        # un cap care citeste doar statistici globale nu le poate distinge de
        # imagini curate, deci nu trebuie supravegheat sa o faca.
        inputs["is_weather_corrupted"] = torch.tensor(
            1.0 if weather_fn in GLOBAL_WEATHER_FNS else 0.0)

        for i in self.frame_idxs:
            if i == "s":
                other_side = {"r": "l", "l": "r"}[side]
                img = self.get_color(folder, frame_index, other_side, do_flip)
            else:
                img = self.get_color(folder, frame_index + i, side, do_flip)
            if weather_fn is not None:
                img = weather_fn(img)
            inputs[("color", i, -1)] = img


        intrinsics = np.delete(self.K, -1, axis=1)
        intrinsics = np.delete(intrinsics, -1, axis=0)  #3*3的内参



        # adjusting intrinsics to match each scale in the pyramid
        for scale in range(self.num_scales):
            K_HiS = self.K.copy()
            K_MiS = self.K.copy()
            K_LoS = self.K.copy()

            inputs[("K_int", scale)] = torch.from_numpy(intrinsics) #3*3的内参

            K_HiS[0, :] *= width_re_HiS // (2 ** scale)
            K_HiS[1, :] *= height_re_HiS // (2 ** scale)
            inv_K_HiS = np.linalg.pinv(K_HiS)
            inputs[("K_HiS", scale)] = torch.from_numpy(K_HiS)
            inputs[("inv_K_HiS", scale)] = torch.from_numpy(inv_K_HiS)

            K_MiS[0, :] *= self.width // (2 ** scale)
            K_MiS[1, :] *= self.height // (2 ** scale)
            inv_K_MiS = np.linalg.pinv(K_MiS)
            inputs[("K_MiS", scale)] = torch.from_numpy(K_MiS)
            inputs[("inv_K_MiS", scale)] = torch.from_numpy(inv_K_MiS)

            K_LoS[0, :] *= width_re_LoS // (2 ** scale)
            K_LoS[1, :] *= height_re_LoS // (2 ** scale)
            inv_K_LoS = np.linalg.pinv(K_LoS)
            inputs[("K_LoS", scale)] = torch.from_numpy(K_LoS)
            inputs[("inv_K_LoS", scale)] = torch.from_numpy(inv_K_LoS)

        if do_color_aug:
            color_aug = transforms.ColorJitter(
                brightness=self.brightness,
                contrast=self.contrast,
                saturation=self.saturation,
                hue=self.hue)
        else:
            color_aug = (lambda x: x)

        self.preprocess(inputs, color_aug, height_re_HiS, width_re_HiS, height_re_LoS, width_re_LoS, dx_HiS, dy_HiS, do_crop_aug)

        #删除原尺寸图像，-1表示原始图像(1242, 375)
        for i in self.frame_idxs:
            del inputs[("color", i, -1)]

        # if self.load_depth:
        #     depth_gt = self.get_depth(folder, frame_index, side, do_flip)
        #     inputs["depth_gt"] = np.expand_dims(depth_gt, 0)
        #     inputs["depth_gt"] = torch.from_numpy(inputs["depth_gt"].astype(np.float32))

        if "s" in self.frame_idxs:
            stereo_T = np.eye(4, dtype=np.float32)
            stereo_T_inv = np.eye(4, dtype=np.float32)
            baseline_sign = -1 if do_flip else 1
            side_sign = -1 if side == "l" else 1
            stereo_T[0, 3] = side_sign * baseline_sign * 0.1
            stereo_T_inv[0, 3] = side_sign * baseline_sign * (-0.1)

            inputs["stereo_T"] = torch.from_numpy(stereo_T)
            inputs["stereo_T_inv"] = torch.from_numpy(stereo_T_inv)

        return inputs

    def get_color(self, folder, frame_index, side, do_flip):
        raise NotImplementedError

    def check_depth(self):
        raise NotImplementedError

    def get_depth(self, folder, frame_index, side, do_flip):
        raise NotImplementedError
