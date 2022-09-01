# %%
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parents[1]))

import os

from utils import createGraph
from ontopia_py import saveGraph

# %%

g = createGraph()

for dir, _, files in os.walk("./"):
    for file in files:
      if not file.endswith("sona.rdf"):
        filepath = os.path.join(dir, file)
        if file.endswith(".rdf"):
          g.parse(filepath)

# %%
saveGraph(g, "sona")