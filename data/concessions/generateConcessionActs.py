# %%
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parents[1]))

from utils import *

from rdflib import Literal, XSD, OWL

from ontoim_py.ontoim import *
from ontoim_py.ns import *

from ontopia_py import ConceptScheme, saveGraph

from ontopia_py.ro import *
from ontopia_py.ti import *
from ontopia_py.clv import *
from ontopia_py.cpv import *

# %%
# Get Data from indicepa.gov.it

config = getConfig("../../conf.ini")

# Create graph
g = createGraph()

# Create a ConceptScheme
CONCESSIONS_DATASET = ConceptScheme(CONCESSIONS_DATA)

# Set the properties
CONCESSIONS_DATASET.label = [
    Literal("Concession Acts", lang="en"),
    Literal("Atti di concessione", lang="it"),
]
CONCESSIONS_DATASET.creator = [ONTO_AUTHOR]

# And add to graph
CONCESSIONS_DATASET.addToGraph(g)

# %%
# Load data
concessionsDF = getOpenData(config.get("MUNICIPALITY", "concession_acts"), dtype={
                         "COD_TIPOLOGIA": str, "COD_STRUTTURA_CONCESSA": str, "NUM_ATTO": str, "COD_BENEFICIARIO": str})

concessionsDF
# %%
# Insert concession acts

for i, concessionInfo in concessionsDF.iterrows():
    actTitle = concessionInfo["TITOLO"]
    actNumber = concessionInfo["NUM_ATTO"]
    actOffice = concessionInfo["COD_UFFICIO"]
    actDate = concessionInfo["DATA_ATTO"]
    actCodBeneficiary = concessionInfo["COD_BENEFICIARIO"]
    actCodType = concessionInfo["COD_TIPOLOGIA"]
    actPaymentAmount = concessionInfo["IMPORTO"]
    actFacility = concessionInfo["COD_STRUTTURA_CONCESSA"]

    concessionAct = ConcessionAct(
      id=str(i + 1),
      baseUri=CONCESSIONS_DATA,
      dataset=CONCESSIONS_DATASET,
      titles=[Literal(standardizeName(actTitle), datatype=XSD.string)]
    )

    concessionAct.actTitle = [Literal(standardizeName(actTitle), datatype=XSD.string)]
    concessionAct.actDate = Literal(actDate, datatype=XSD.date)
    concessionAct.actNumber = Literal(actNumber, datatype=XSD.string)
    concessionAct.hasConcessionActType = [ConcessionActType(
      id=actCodType,
      baseUri=CONCESSION_ACT_TYPES
    )]

    if not pd.isna(actCodBeneficiary):
      concessionAct.hasBeneficiary = [Association(
        id=actCodBeneficiary,
        baseUri=ASSOCIATIONS_DATA
      )]
    
    concessionAct.hasOrganization = [Organization(
      id=actOffice,
      baseUri=MUNICIPALITY_DATA
    )]
    
    concessionAct.paymentAmount = Literal(actPaymentAmount, datatype=XSD.float)
    
    if not pd.isna(actFacility):
      facility = Facility(id=actFacility, baseUri=HERITAGE_DATA)
      facility.concessedWithAct = [concessionAct]

      facility.addToGraph(g, onlyProperties=True)
    
    concessionAct.addToGraph(g, isTopConcept=True)
# %%
# Save graph

saveGraph(g, "concessionActs")
