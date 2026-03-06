import os

model_dir = r"D:\AI\Qwen-Image-Layered\model"
total = 0
files = 0
for root, dirs, filenames in os.walk(model_dir):
    for f in filenames:
        fp = os.path.join(root, f)
        total += os.path.getsize(fp)
        files += 1
print(f"File trovati: {files}")
print(f"Dimensione totale: {total / 1024**3:.2f} GB")

import torch
print(f"CUDA disponibile: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0)}")