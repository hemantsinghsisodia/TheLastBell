import sys
import numpy as np
from PIL import Image
a=np.asarray(Image.open(sys.argv[1]).convert("RGB"),dtype=np.float64); b=np.asarray(Image.open(sys.argv[2]).convert("RGB"),dtype=np.float64)
print(sys.argv[1].split("/")[-1], "vs", sys.argv[2].split("/")[-1], "mean abs pixel diff (0-255, RGB mean) %.3f  max %.0f" % (np.abs(a-b).mean(), np.abs(a-b).max()))
