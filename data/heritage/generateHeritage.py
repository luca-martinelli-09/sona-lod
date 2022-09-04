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

municipalityID = config.get("MUNICIPALITY", "municipality_id")

# Create a ConceptScheme
HERITAGE_DATASET = ConceptScheme(HERITAGE_DATA)

# Set the properties
HERITAGE_DATASET.label = [
    Literal("Heritage of Comune di Sona", lang="en"),
    Literal("Patrimonio immobilare del Comune di Sona", lang="it"),
]
HERITAGE_DATASET.creator = [ONTO_AUTHOR]

# And add to graph
HERITAGE_DATASET.addToGraph(g)

# %%
# Load data
heritageDF = getOpenData(config.get("MUNICIPALITY", "heritage"), dtype={
                         "FOGLIO": "Int64", "PROGR_NAZIONALE": "Int64", "PROGR_CIVICO": "Int64"})

# %%
# Insert heritage facilities

insertFacilities = []
insertHeritages = []

municipality = PublicOrganization(
    id=municipalityID,
    baseUri=MUNICIPALITY_DATA
)

municipality.hasHeritage = []

for _, facilityInfo in heritageDF.iterrows():
    facilityCode = facilityInfo["CODICE"]

    miurCode = facilityInfo["CODICE_MIUR"]

    facilityName = facilityInfo["DENOMINAZIONE"]
    heritageName = facilityInfo["NOME_CATEGORIA"]

    heritageCategory = facilityInfo["COD_CATEGORIA"]

    progrNazionale = facilityInfo["PROGR_NAZIONALE"]
    progrCivico = facilityInfo["PROGR_CIVICO"]

    cadastralSheet = facilityInfo["FOGLIO"]
    cadastralMaps = "" if pd.isna(
        facilityInfo["MAPPALE"]) else facilityInfo["MAPPALE"]
    cadastralSubs = "" if pd.isna(
        facilityInfo["SUBALTERNO"]) else facilityInfo["SUBALTERNO"]
    cadastralCategory = facilityInfo["CATEGORIA"]

    isAlreadyInsertFacility = facilityCode in insertFacilities
    insertFacilities.append(facilityCode)

    isAlreadyInsertHeritage = heritageCategory in insertHeritages
    insertHeritages.append(heritageCategory)

    # HERITAGE

    heritage = Heritage(
        id=str(heritageCategory),
        baseUri=HERITAGE_DATA,
        dataset=HERITAGE_DATASET,
        titles=[Literal(heritageName, datatype=XSD.string)]
    )

    heritage.hasHeritageType = HeritageType(
        id=str(heritageCategory),
        baseUri=HERITAGE_TYPES
    )

    # FACILITY

    facility = Facility(
        id="facility/" + str(facilityCode),
        baseUri=HERITAGE_DATA,
        dataset=HERITAGE_DATASET,
        titles=[Literal(facilityName, datatype=XSD.string)]
    )

    facility.POIofficialName = [Literal(facilityName, datatype=XSD.string)]
    facility.ownedBy = [municipality]

    if not pd.isna(progrNazionale):
        address = Address(
            id="ad-{}-{}".format(str(progrNazionale),
                              "snc" if pd.isna(progrCivico) else str(progrCivico)),
            baseUri=ANNCSU
        )
        facility.hasAddress = [address]

    # MIUR

    if not pd.isna(miurCode):
        g.add((facility.uriRef, OWL.sameAs, SCHOOL_DATA[miurCode]))

    # CADASTRAL DATA

    facility.hasCadastralData = []

    if not pd.isna(cadastralSheet):
        for cadastralMap in cadastralMaps.split("-"):
            for cadastralSub in cadastralSubs.split("-"):
                cadastralData = CadastralData(
                    id="cadastre/{}{}{}{}".format(
                        cadastralSheet,
                        "-" + cadastralMap if cadastralMap != "" else "",
                        "-" + cadastralSub if cadastralSub != "" else "",
                        "-" +
                        cadastralCategory.replace(
                            "/", "") if not pd.isna(cadastralCategory) else "",
                    ),
                    baseUri=HERITAGE_DATA,
                    dataset=HERITAGE_DATASET,
                    titles=[
                        Literal("Cadastral data for " +
                                facilityName, lang="en"),
                        Literal("Dati catastali per " +
                                facilityName, lang="it"),
                    ]
                )

                cadastralData.sheet = Literal(
                    cadastralSheet, datatype=XSD.string)
                if cadastralMap != "":
                    cadastralData.map = Literal(
                        cadastralMap, datatype=XSD.string)
                if cadastralSub != "":
                    cadastralData.subordinate = Literal(
                        cadastralSub, datatype=XSD.string)

                if not pd.isna(cadastralCategory):
                    cadastralData.hasCadastralCategory = CadastralCategory(
                        id=cadastralCategory.replace("/", "."),
                        baseUri=CADASTRAL_CATEGORIES
                    )

                cadastralData.addToGraph(g)

                facility.hasCadastralData.append(cadastralData)

    heritage.hasFacility = [facility]
    
    municipality.hasHeritage.append(heritage)

    heritage.addToGraph(g, isTopConcept=True,
                        onlyProperties=isAlreadyInsertHeritage)

    facility.addToGraph(g, isTopConcept=True,
                        onlyProperties=isAlreadyInsertFacility)

municipality.addToGraph(g, onlyProperties=True)
# %%
# Save graph

saveGraph(g, "heritage")
