# %%
from ontopia_py.ro import *
from ontopia_py import *

from rdflib import Graph, Literal

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parents[1]))

from utils import *


# %%
# Create graph
g: Graph = createGraph()

# Create a ConceptScheme
ROLE_DATASET = ConceptScheme(ROLE_DATA)

# Set the properties
ROLE_DATASET.label = [
    Literal("Roles", lang="en"),
    Literal("Ruoli", lang="it")
]
ROLE_DATASET.creator = [ONTO_AUTHOR]

# And add to graph
ROLE_DATASET.addToGraph(g)

#%%
# Set data

rolesDF = pd.DataFrame([
    {"id": "mayor", "name_it": "Sindaco", "name_en": "Mayor"},
    {"id": "vicemayor", "name_it": "Vicesindaco", "name_en": "Vice mayor"},
    {"id": "assessor", "name_it": "Assessore", "name_en": "Assessor"},
    {"id": "councilor", "name_it": "Consigliere", "name_en": "Councilor"},
    {"id": "podesta", "name_it": "Podestà", "name_en": "Podesta"},
    {"id": "commissioner", "name_it": "Commissario", "name_en": "Commissioner"},
    {"id": "president", "name_it": "Presidente", "name_en": "President"},
    {"id": "vicepresident", "name_it": "Vicepresidente", "name_en": "Vice president"},
    {"id": "referent", "name_it": "Responsabile", "name_en": "Referent"},
    {"id": "head-teacher", "name_it": "Dirigente scolastico", "name_en": "Head teacher"},
])
rolesDF.set_index("id", inplace=True)
# %%
# Insert social medias

for roleID, roleInfo in rolesDF.iterrows():
    role = Role(
      id=roleID,
      baseUri=ROLE_DATA,
      dataset=ROLE_DATASET,
      titles=[
        Literal(roleInfo["name_en"], lang="en"),
        Literal(roleInfo["name_it"], lang="it")
    ])

    role.name = [
        Literal(roleInfo["name_en"], lang="en"),
        Literal(roleInfo["name_it"], lang="it")
    ]

    role.addToGraph(g, isTopConcept=True)

# %%
# Save graph

saveGraph(g, "roles")