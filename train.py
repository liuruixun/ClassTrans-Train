import sys
import os
import time
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import source
import segmentation_models_pytorch as smp
from segmentation_models_pytorch.losses import DiceLoss, SoftCrossEntropyLoss, FocalLoss
import glob
import torchvision.transforms.functional as TF
import math
import cv2
from PIL import Image
import time
import warnings
from pathlib import Path
try:
    from peft import get_peft_config, get_peft_model
except:
    print('install peft if you use LoRA')

from source.model import get_model
from source.load_checkpoint import load_checkpoint
from source.utils import setup_seed


class_rgb = {
    "bg": [0, 0, 0],
    "tree": [34, 97, 38],
    "rangeland": [0, 255, 36],
    "bareland": [128, 0, 0],
    "agric land type 1": [75, 181, 73],
    "road type 1": [255, 255, 255],
    "sea, lake, & pond": [0, 69, 255],
    "building type 1": [222, 31, 7],
}

class_gray = {
    "bg": 0,
    "tree": 1,
    "rangeland": 2,
    "bareland": 3,
    "agric land type 1": 4,
    "road type 1": 5,
    "sea, lake, & pond": 6,
    "building type 1": 7,
}

def label2rgb(a):
    """
    a: labels (HxW)
    """
    out = np.zeros(shape=a.shape + (3,), dtype="uint8")
    for k, v in class_gray.items():
        out[a == v, 0] = class_rgb[k][0]
        out[a == v, 1] = class_rgb[k][1]
        out[a == v, 2] = class_rgb[k][2]
    return out

warnings.filterwarnings("ignore")
os.environ['CUDA_VISIBLE_DEVICES'] = '1'


OEM_ROOT_TRAIN = "../data/"  # Download the 'trainset' and set your data_root to 'trainset' folder
OEM_DATA_DIR = OEM_ROOT_TRAIN+'trainset/'
OEM_DATA_DIR_VAL = OEM_ROOT_TRAIN+'trainset/'
TEST_DIR = OEM_ROOT_TRAIN+'trainset/images'
TRAIN_LIST = OEM_ROOT_TRAIN+"train.txt"
VAL_LIST = OEM_ROOT_TRAIN+"stage1_val.txt"
WEIGHT_DIR = "weight" # path to save weights
OUT_DIR = "result/" # path to save prediction images
os.makedirs(WEIGHT_DIR, exist_ok=True)

seed = 0
base_lr = 5e-4
batch_size = 8
n_epochs = 200
interval = 1
classes = [0, 1, 2, 3, 4, 5, 6, 7]
n_classes = len(classes)
classes_wt = np.ones([n_classes], dtype=np.float32)
setup_seed(seed)
device = "cuda" if torch.cuda.is_available() else "cpu"

print("Number of epochs   :", n_epochs)
print("Number of classes  :", n_classes)
print("Batch size         :", batch_size)
print("Device             :", device)

img_train_pths = [f for f in Path(OEM_DATA_DIR).rglob("*.tif") if "/labels/" in str(f)]
img_val_pths = [f for f in Path(OEM_DATA_DIR_VAL).rglob("*.tif") if "/labels/" in str(f)]
train_pths = [str(f) for f in img_train_pths if f.name in np.loadtxt(TRAIN_LIST, dtype=str)]
val_pths = [str(f) for f in img_val_pths if f.name in np.loadtxt(VAL_LIST, dtype=str)]

print("Total samples      :", len(img_train_pths))
print("Training samples   :", len(train_pths))
print("Validation samples :", len(val_pths))

trainset = source.dataset.Dataset(train_pths, classes=classes, size=512, train=True)
validset = source.dataset.Dataset(val_pths, classes=classes, train=False)

train_loader = DataLoader(trainset, batch_size=batch_size, shuffle=True, num_workers=0)
valid_loader = DataLoader(validset, batch_size=batch_size, shuffle=False, num_workers=0)

# network = get_model(
#     dict(model_name='UPerNet',
#          encoder_name='ViT-B-16',
#          encoder_weights=None,
#          classes=n_classes))

# checkpoint_path = 'pretrain/FP16-ViT-B-16.pt'
# network = load_checkpoint('vit', network, checkpoint_path, strict=True)

# network = get_model(
#     dict(model_name='UPerNet',
#          encoder_name='convnext_base',
#          encoder_weights=None,
#          encoder_depth=4,
#          classes=n_classes))

# checkpoint_path = 'pretrain/SLFFM_convnext_base.pth'
# checkpoint_path = 'pretrain/convnext_base_1k_224_ema.pth'
# network = load_checkpoint('convnext', network, checkpoint_path, strict=False)

# network = get_model(
#     dict(model_name='UPerNet',
#          encoder_name='tu-convnext_base.clip_laiona_320',
#          encoder_weights=None,
#          encoder_depth=4,
#          classes=n_classes))
# checkpoint_path = 'pretrain/open_clip_pytorch_model_convnext-b.bin'
# network = load_checkpoint('convnext-clip', network, checkpoint_path, strict=True)


############################best↓
network = get_model(
    dict(model_name='UPerNet',
         encoder_name='tu-convnext_large_mlp.clip_laion2b_ft_soup_320',
         encoder_weights=None,
         encoder_depth=4,
         classes=n_classes))
checkpoint_path = 'pretrain/open_clip_pytorch_model_convnext-l.bin'
network = load_checkpoint('convnext-clip', network, checkpoint_path, strict=True)

#########################
# network = get_model(
#     dict(model_name='UPerNet',
#          encoder_name='resnet50',
#          encoder_weights=None,
#          encoder_depth=4,
#          classes=n_classes))
# checkpoint_path = 'initmodel/resnet50_v2.pth'
# network = load_checkpoint('resnet50', network, checkpoint_path, strict=True)
#######################
#########################
# network = get_model(
#     dict(model_name='UPerNet',
#          encoder_name='resnet101',
#          encoder_weights=None,
#          encoder_depth=4,
#          classes=n_classes))
# checkpoint_path = 'initmodel/resnet101_v2.pth'
# network = load_checkpoint('resnet101', network, checkpoint_path, strict=True)
#######################

# network = get_model(
#     dict(model_name='UPerNet',
#          encoder_name='timm-resnest101e',
#          classes=n_classes))


# network = get_model(
#     dict(model_name='UPerNet',
#          encoder_name='tu-convnext_xxlarge.clip_laion2b_soup',
#          encoder_weights=None,
#          encoder_depth=4,
#          classes=n_classes))
# checkpoint_path = 'pretrain/open_clip_pytorch_model_convnext-xxlarge.bin'
# network = load_checkpoint('convnext-clip', network, checkpoint_path, strict=True)

# use LoRA
# peft_config = get_peft_config({
#                 "peft_type": "LORA",
#                 "r": 16,
#                 'target_modules': ["fc1", "fc2"],
#                 "lora_alpha": 32,
#                 "lora_dropout": 0.05,
#                 "bias": "none",
#                 "inference_mode": False,
#             })
# network = get_peft_model(network, peft_config)

# count parameters
params = 0
for p in network.parameters():
    if p.requires_grad:
        params += p.numel()

# criterion = source.losses.CEWithLogitsLoss(weights=classes_wt)
class HybirdLoss(torch.nn.Module):
    def __init__(self):
        super(HybirdLoss, self).__init__()
        self.name = 'CE_DICE'
        self.SCELoss_fn = SoftCrossEntropyLoss(smooth_factor=0.1)
        self.DiceLoss_fn = DiceLoss(mode='multiclass')
        # self.FocalLoss_fn = FocalLoss(mode='multiclass')

    def forward(self, pred, mask):
        loss_sce = self.SCELoss_fn(pred, mask)
        loss_dice = self.DiceLoss_fn(pred, mask)
        # loss_focal = self.FocalLoss_fn(pred, mask)
        loss = loss_sce + loss_dice
        return loss

criterion = HybirdLoss().cuda()
criterion_name = 'CE_DICE'
metric = source.metrics.IoU2()

parameters = []
for name, param in network.named_parameters():
    if not param.requires_grad:
        continue
    if 'encoder' in name:
        parameters.append({'params': param, 'lr': 1e-6})
    else:
        parameters.append({'params': param, 'lr': base_lr})
optimizer = torch.optim.AdamW(parameters, lr=base_lr, weight_decay=1e-2)

scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
            optimizer,
            T_0=n_epochs + 1,
            T_mult=2,
            eta_min=1e-5,
        )
network_fout = f"{network.name}_s{seed}_{criterion.name}"
OUT_DIR += network_fout # path to save prediction images
os.makedirs(OUT_DIR, exist_ok=True)

print("Model output name  :", network_fout)
print("Number of parameters: ", params)

if torch.cuda.device_count() > 1:
    pass
    # print("Number of GPUs :", torch.cuda.device_count())
    # network = torch.nn.DataParallel(network)
    # optimizer = torch.optim.AdamW(
    #     [dict(params=network.module.parameters(), lr=learning_rate)]
    # )

max_score = 0
train_hist = []
valid_hist = []

for epoch in range(1, n_epochs + 1):
  print(f"\nEpoch: {epoch}")

  logs_train = source.runner.train_epoch(
      model=network,
      optimizer=optimizer,
      scheduler=scheduler,
      criterion=criterion,
      metric=metric,
      dataloader=train_loader,
      device=device,
  )
  

  if epoch % interval == 0 or epoch == n_epochs:
    logs_valid = source.runner.valid_epoch(
        model=network,
        criterion=criterion,
        metric=metric,
        dataloader=valid_loader,
        device=device,
    )
    # train_hist.append(logs_train)
    # valid_hist.append(logs_valid)

    score = logs_valid[metric.name]

    if epoch==177:
        #max_score = score
        torch.save(network.state_dict(), os.path.join(WEIGHT_DIR, f"{network_fout}{epoch}.pth"))
        print("Model saved!")

# load network
# network.load_state_dict(torch.load(os.path.join(WEIGHT_DIR, f"{network_fout}.pth")))
network.to(device).eval()

test_pths = glob.glob(TEST_DIR+"/*.tif")
#testset = source.dataset.Dataset(test_pths, classes=classes, train=False)

for fn_img in test_pths:
  img = source.dataset.load_multiband(fn_img)
  h, w = img.shape[:2]
  power = math.ceil(np.log2(h) / np.log2(2))
  shape = (2 ** power, 2 ** power)
  img = cv2.resize(img, shape)

  input = TF.to_tensor(img).unsqueeze(0).float().to(device)

  pred = []
  with torch.no_grad():
      msk = network(input)
      pred = msk.squeeze().cpu().numpy()
  pred = pred.argmax(axis=0).astype("uint8")
  size = pred.shape[0:]
  y_pr = cv2.resize(pred, (w, h), interpolation=cv2.INTER_NEAREST)

  # save image as png
  filename = os.path.splitext(os.path.basename(fn_img))[0]
  y_pr_rgb = label2rgb(y_pr)
  Image.fromarray(y_pr).save(os.path.join(OUT_DIR, filename+'.png'))