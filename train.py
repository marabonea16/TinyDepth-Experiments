# Copyright Niantic 2019. Patent Pending. All rights reserved.
#
# This software is licensed under the terms of the Monodepth2 licence
# which allows for non-commercial use only, the full terms of which are made
# available in the LICENSE file.


from __future__ import absolute_import, division, print_function

import random
import numpy as np
import torch

from trainer import Trainer
from options import MonodepthOptions

options = MonodepthOptions()
opts = options.parse()

SEED = getattr(opts, "seed", 42)
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)


if __name__ == "__main__":
    trainer = Trainer(opts)
    trainer.train()
