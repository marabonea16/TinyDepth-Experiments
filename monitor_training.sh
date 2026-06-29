#!/bin/bash
# Monitorizeaza antrenarea si reia daca s-a oprit.
# Rulat de cron la fiecare ora.

set -euo pipefail

WORKDIR="/home/ubuntu/TinyDepth"
LOG="/home/ubuntu/monitor_training.log"
HC_URL="https://hc-ping.com/f2d24240-e53d-4315-bf2d-c9bae9778766"

cd "$WORKDIR"

timestamp() { date '+%Y-%m-%d %H:%M:%S'; }

wget -qO- "$HC_URL" > /dev/null 2>&1 || true

SESSION_TS="train_ts"

# -------------------------------------------------------
# URW-Depth-S2-Fix7: configuratia validata empiric prin
# Diag1/7/8 - calib_weight=0.3 (depth ~baseline, sigma
# calibrat dar decade lent), seed=42 fixat, detach() la
# uncertconv, reset_uncert_head (confirmat sigur, Diag8).
# -------------------------------------------------------

S2FIX_DIR="$WORKDIR/models/URW-Depth-S2-Fix7/models"
S2_LATEST="$WORKDIR/models/URW-Depth-S2/models/weights_14"

S2FIX_BASE="--split eigen_zhou --height 192 --width 640 --scales 0 --png \
  --batch_size 4 --num_workers 8 \
  --learning_rate 1e-5 --num_epochs 15 --scheduler_step_size 8 \
  --log_dir models --data_path $WORKDIR \
  --use_feature_suppression --use_weather_aug --use_corruption_aug \
  --calib_weight 0.3 --seed 42 \
  --use_wandb --wandb_project tinydepth"

# URW-Depth-S2-Fix7 ABANDONAT (calib_weight=0.3 protejeaza depth dar sigma
# colapseaza complet pana la finalul epocii 0 - aceeasi tensiune ca Diag1).
echo "$(timestamp) URW-Depth-S2-Fix7 abandoned (sigma collapse, depth/calib tradeoff irreducibil)." >> "$LOG"
exit 0

if [ -d "$S2FIX_DIR/weights_14" ]; then
    echo "$(timestamp) URW-Depth-S2-Fix7 complete. Nothing to do." >> "$LOG"
    exit 0
fi

if pgrep -f "train.py.*model_name URW-Depth-S2-Fix7" > /dev/null 2>&1; then
    echo "$(timestamp) URW-Depth-S2-Fix7 training running. OK." >> "$LOG"
    exit 0
fi

if [ -L "$S2FIX_DIR/weights_latest" ]; then
    LATEST=$(readlink -f "$S2FIX_DIR/weights_latest")
    EPOCH=$(basename "$LATEST" | sed 's/weights_//')
    START=$((EPOCH + 1))
    echo "$(timestamp) Resuming URW-Depth-S2-Fix7 from epoch $START" >> "$LOG"
    CMD="CUDA_VISIBLE_DEVICES=0 python train.py --model_name URW-Depth-S2-Fix7 $S2FIX_BASE \
      --wandb_run_name urw-depth-s2-fix7-w03-final \
      --load_weights_folder $LATEST --start_epoch $START"
else
    echo "$(timestamp) Starting URW-Depth-S2-Fix7 from URW-Depth-S2/weights_14" >> "$LOG"
    CMD="CUDA_VISIBLE_DEVICES=0 python train.py --model_name URW-Depth-S2-Fix7 $S2FIX_BASE \
      --wandb_run_name urw-depth-s2-fix7-w03-final \
      --reset_uncert_head \
      --load_weights_folder $S2_LATEST --start_epoch 0"
fi

tmux kill-session -t "$SESSION_TS" 2>/dev/null || true
tmux new-session -d -s "$SESSION_TS" "bash -c 'cd $WORKDIR && source /home/ubuntu/anaconda3/etc/profile.d/conda.sh && conda activate tinydepth && $CMD; echo DONE; read'"
echo "$(timestamp) Launched URW-Depth-S2-Fix7 in tmux '$SESSION_TS'." >> "$LOG"
