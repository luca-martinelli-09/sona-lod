# %%
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parents[1]))

from utils import *

from rdflib import Graph, Literal, XSD

from ontoim_py.ontoim import *
from ontoim_py.ns import *

from ontopia_py import ConceptScheme, saveGraph

from ontopia_py.sm import *
from ontopia_py.ti import *
from ontopia_py.mu import *

# %%
# Get Data from indicepa.gov.it

config = getConfig("../../conf.ini")

# Create graph
g: Graph = createGraph()

# Create a ConceptScheme
WASTE_DATASET = ConceptScheme(WASTE_DATA)

# Set the properties
WASTE_DATASET.label = [
    Literal("Waste production", lang="en"),
    Literal("Produzione di rifiuti", lang="it"),
]
WASTE_DATASET.creator = [ONTO_AUTHOR]

# And add to graph
WASTE_DATASET.addToGraph(g)

# %%
# Load data

wasteDataDF = getOpenData(config.get("WASTE", "waste_production"), dtype={"ANNO": str})

wasteToCode = {
  "ALTRO":"other",
  "INGOMBRANTI":"bulky",
  "CARTA E CARTONE":"paper",
  "FRAZIONE ORGANICA":"organic",
  "LEGNO":"wood",
  "METALLO":"metal",
  "PLASTICA":"plastic",
  "RAEE":"weee",
  "SELETTIVA":"selective",
  "TESSILI":"textiles",
  "VETRO":"glass",
  "DA C&D":"candd",
  "PULIZIA STRADALE":"street"
}

# %%
# Insert data

for _, wasteInfo in wasteDataDF.iterrows():
    productionYear = wasteInfo["ANNO"]

    temporalEntity = Year(
      id="ti/{}".format(productionYear),
      baseUri=WASTE_DATA,
      dataset=WASTE_DATASET,
      titles=[Literal(productionYear, datatype=XSD.string)]
    )
    temporalEntity.year = Literal(productionYear, datatype=XSD.gYear)
    temporalEntity.addToGraph(g, isTopConcept=True)

    measurementUnit = MeasurementUnit(
      id="mu/tons",
      baseUri=WASTE_DATA,
      dataset=WASTE_DATASET,
      titles=[
          Literal("Tons", lang="en"),
          Literal("Tonnellate", lang="it"),
      ]
    )
    measurementUnit.addToGraph(g, isTopConcept=False)

    for k, wasteCode in wasteToCode.items():
      productionValue = wasteInfo[k]

      if not pd.isna(productionValue):
        wasteProductionValue = Value(
            id="value/{}-{}".format(wasteCode, productionYear),
            baseUri=WASTE_DATA,
            dataset=WASTE_DATASET,
            titles=[
                Literal("{} t".format(productionValue))
            ]
        )
        wasteProductionValue.value = [Literal(productionValue, datatype=XSD.float)]
        wasteProductionValue.hasMeasurementUnit = [measurementUnit]
        wasteProductionValue.addToGraph(g, isTopConcept=False)

        waste = WasteProduction(
          id="{}-{}".format(wasteCode, productionYear),
          baseUri=WASTE_DATA,
          dataset=WASTE_DATASET,
          titles=[Literal("Produzione di rifiuti nel {} - {}".format(productionYear, standardizeName(k)), datatype=XSD.string)]
        )
        waste.hasTemporalEntity = temporalEntity
        waste.hasWasteCategory = WasteCategory(id=wasteCode, baseUri=WASTE_CATEGORIES)
        waste.hasValue = [wasteProductionValue]
        waste.addToGraph(g, isTopConcept=True)

# %%
# Save graph

saveGraph(g, "waste")
# %%
