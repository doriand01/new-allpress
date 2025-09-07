import torch
import allpress
from os import path

dataset = torch.load(path.join(allpress.settings.TEMP_TRAINING_VECTOR_PATH, 'semantic.pth'))

