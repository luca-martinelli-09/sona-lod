# %%
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parents[1]))

from utils import *

from rdflib import Literal, XSD

from ontoim_py.ontoim import *
from ontoim_py.ns import *

from ontopia_py import ConceptScheme, saveGraph

from ontopia_py.ro import *
from ontopia_py.ti import *
from ontopia_py.clv import *
from ontopia_py.cpv import *
from ontopia_py.cov import *

# %%
# Get Data from indicepa.gov.it

config = getConfig("../../conf.ini")

datasetID = config.get("MUNICIPALITY", "dataset")

# Create graph
g = createGraph()

# Create a ConceptScheme
MUNICIPALITY_DATA = ConceptScheme(MUN_DATA)

# %%
# Load data
mayorsDF = getOpenData(datasetID, config.get(
    "MUNICIPALITY", "mayors"), dtype={'Codice_Fiscale_Ente': str})

# %%
# Insert referents
uniqueMyorsDF = mayorsDF[["Nome", "Cognome"]].drop_duplicates()

for _, mayorInfo in uniqueMyorsDF.iterrows():
    nameMayor = mayorInfo["Nome"]
    surnameMayor = mayorInfo["Cognome"]

    mayor = Person(
        id="person/" + genNameForID(nameMayor + " " + surnameMayor),
        baseUri=MUN_DATA,
        dataset=MUNICIPALITY_DATA,
        titles=[Literal(nameMayor + " " + surnameMayor, datatype=XSD.string)]
    )

    mayor.givenName = Literal(nameMayor, datatype=XSD.string)
    mayor.familyName = Literal(surnameMayor, datatype=XSD.string)

    mayor.addToGraph(g, isTopConcept=True)
    
# %%
# Insert organization

for _, mayorInfo in mayorsDF.iterrows():
    mayorName = mayorInfo["Nome"] + " " + mayorInfo["Cognome"]
    mayorID = genNameForID(mayorName)

    mayorRoleCode = mayorInfo["Codice_Ruolo"]

    startDate = mayorInfo["Data_Inizio"]
    endDate = mayorInfo["Data_Fine"]

    publicOrganization = PublicOrganization(
      id=mayorInfo["Codice_Fiscale_Ente"],
      baseUri=MUN_DATA
    )

    dateRangeID = "{}{}".format(
        startDate,
        "-" + endDate if not pd.isna(endDate) else ""
    )

    mayorRoleID = "{}-{}".format(mayorID, dateRangeID)

    mayorRole = Employment(
        id="mayor/" + mayorRoleID,
        baseUri=MUN_DATA,
        dataset=MUNICIPALITY_DATA,
        titles=[Literal("{} ({} - {})".format(mayorName, startDate, endDate), datatype=XSD.string)]
    )

    mayor = Person(
        id="person/" + mayorID,
      baseUri=MUN_DATA
    )

    mayorRole.employmentFor = publicOrganization
    mayorRole.withRole = [Role(
      id=mayorRoleCode,
      baseUri=ROLE_DATA
    )]

    timeInterval = TimeInterval(
      id="ti/" + dateRangeID,
      baseUri=MUN_DATA,
      dataset=MUNICIPALITY_DATA,
      titles=[Literal("{} - {}".format(startDate, endDate), datatype=XSD.string)]
    )
    timeInterval.startTime = Literal(startDate, datatype=XSD.date)
    
    if not pd.isna(endDate):
      timeInterval.endTime = Literal(endDate, datatype=XSD.date)

    mayorRole.isRoleInTimeOf = [mayor]
    mayorRole.hasTemporalEntity = [timeInterval]

    publicOrganization.holdEmployment = [mayorRole]

    timeInterval.addToGraph(g, isTopConcept=False)
    mayorRole.addToGraph(g, isTopConcept=False)
    g.add((mayor.uriRef, RO["holdsRoleInTime"], mayorRole.uriRef))
    publicOrganization.addToGraph(g, onlyProperties=True)

# %%
# Save graph

saveGraph(g, "mayors")