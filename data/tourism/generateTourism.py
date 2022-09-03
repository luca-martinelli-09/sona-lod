# %%
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parents[1]))

from utils import *

from rdflib import Literal, XSD, OWL

from ontoim_py.ontoim import *
from ontoim_py.ns import *
from ontoim_py.ontoim.TouristType import Arrival, Presence

from ontopia_py import ConceptScheme, saveGraph

from ontopia_py.ro import *
from ontopia_py.ti import *
from ontopia_py.clv import *
from ontopia_py.cpv import *

import pandas as pd

# %%
# Get Data from indicepa.gov.it

config = getConfig("../../conf.ini")

# Create graph
g = createGraph()

# Create a ConceptScheme
TOURISM_DATASET = ConceptScheme(TOURISM_DATA)

# Set the properties
TOURISM_DATASET.label = [
    Literal("Touristic Arrivals and Presences", lang="en"),
    Literal("Arrivi e presenze turistiche", lang="it"),
]
TOURISM_DATASET.creator = [ONTO_AUTHOR]

# And add to graph
TOURISM_DATASET.addToGraph(g)

# %%
# Load data
tourismDF = getOpenData(config.get("TOURISM", "tourists"), dtype={
    "ANNO": str, "ARRIVI": "Int64", "PRESENZE": "Int64"})

tourismDF
# %%
# Insert concession acts

for _, tourismInfo in tourismDF[tourismDF["COD_ORIGINE"].notna()].iterrows():
    year = tourismInfo["ANNO"]
    codOrigin = tourismInfo["COD_ORIGINE"]
    originName = tourismInfo["ORIGINE"]

    for tType in ["ARRIVI", "PRESENZE"]:
      number = tourismInfo[tType]

      if not pd.isna(number) and number > 0:
        demoReference = Person(
            id="reference/from-" + codOrigin,
            baseUri=TOURISM_DATA,
            dataset=TOURISM_DATASET,
            titles=[Literal("Persona da " + originName, datatype=XSD.string)]
        )

        if len(codOrigin) < 3:
          address = Address(
              id="address/" + codOrigin,
              baseUri=TOURISM_DATA,
              dataset=TOURISM_DATASET,
              titles=[Literal(originName, datatype=XSD.string)]
          )
          address.hasRegion = [Region(id=codOrigin, baseUri=REGIONS)]
          address.hasCountry = [Country(id="ITA", baseUri=ITALY)]
          address.addToGraph(g, isTopConcept=False)

          demoReference.residentIn = [address]
        else:
          demoReference.hasCitizenship = [Country(id=codOrigin, baseUri=COUNTRIES)]

        demoReference.addToGraph(g, isTopConcept=False)

        temporalEntity = Year(
          id="ti/" + year,
          baseUri=TOURISM_DATA,
          dataset=TOURISM_DATASET,
          titles=[Literal(year, datatype=XSD.string)]
        )
        temporalEntity.year = Literal(year, datatype=XSD.gYear)
        temporalEntity.addToGraph(g, isTopConcept=False)

        tourists = Tourists(
          id="{}-{}-{}".format(year, codOrigin, tType.lower()),
          baseUri=TOURISM_DATA,
          dataset=TOURISM_DATASET,
          titles=[Literal("{} turisti{} da {} - {}".format(
            standardizeName(tType),
            "ci" if tType == "ARRIVI" else "che",
            originName, year), datatype=XSD.string)]
        )
        tourists.hasDemographicReference = demoReference
        tourists.observationValue = Literal(number, datatype=XSD.int)
        tourists.hasTouristType = Arrival()if tType == "ARRIVI" else Presence()
        tourists.hasTemporalEntity = temporalEntity

        tourists.addToGraph(g, isTopConcept=True)
# %%
# Insert aggregated data
for year, tourismInfo in tourismDF.groupby(by=["ANNO"]).agg({"ARRIVI": "sum", "PRESENZE": "sum"}).iterrows():
  for tType in ["ARRIVI", "PRESENZE"]:
    number = tourismInfo[tType]

    tourists = Tourists(
        id="{}-{}-{}".format(year, "totale", tType.lower()),
        baseUri=TOURISM_DATA,
        dataset=TOURISM_DATASET,
        titles=[Literal("{} turisti{} totali - {}".format(
            standardizeName(tType),
                "ci" if tType == "ARRIVI" else "che",
                originName, year), datatype=XSD.string)]
    )
    tourists.observationValue = Literal(number, datatype=XSD.int)
    tourists.hasTouristType = Arrival() if tType == "ARRIVI" else Presence()
    tourists.hasTemporalEntity = temporalEntity

    tourists.addToGraph(g, isTopConcept=True)

# %%
# Save graph

saveGraph(g, "tourists")