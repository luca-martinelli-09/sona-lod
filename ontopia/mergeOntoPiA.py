# %%
import os
import shutil
from git import Repo
from rdflib import Graph

# %%

if os.path.exists("./ontopia-repo"):
    shutil.rmtree("./ontopia-repo")

Repo.clone_from(
    "https://github.com/italia/daf-ontologie-vocabolari-controllati.git", "./ontopia-repo")

# %%
# Get ontologies
g = Graph()

for dir, pdir, files in os.walk("./ontopia-repo/Ontologie"):
    if os.path.basename(dir) == "latest":
        for file in files:
            filepath = os.path.join(dir, file)
            if file.endswith(".rdf") and "aligns" not in file:
                g.parse(filepath)

g.serialize("ontopia.ttl", "turtle")
g.serialize("ontopia.rdf", "pretty-xml")
# %%
# Get controlled vocabularies
g = Graph()

for dir, pdir, files in os.walk("./ontopia-repo/VocabolariControllati"):
    for file in files:
        filepath = os.path.join(dir, file)

        if (not dir.endswith("cities")) and (not dir.endswith("scriptR2RML")) and (file.endswith(".rdf") or file.endswith(".ttl")):
            g.parse(filepath)

g.serialize("vocabolari-controllati.ttl", "turtle")
g.serialize("vocabolari-controllati.rdf", "pretty-xml")
# %%
#
