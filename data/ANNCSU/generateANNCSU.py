# %%
# Utils
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parents[1]))

from utils import *

# Pandas and others

import pandas as pd
from pykml import parser

from rdflib import Literal

from rdflib.namespace import XSD

from alive_progress import alive_bar

# OntoPiA

from ontopia_py import ConceptScheme, saveGraph
from ontopia_py.ns import *
from ontopia_py.clv import *
from ontopia_py.clv.GeometryType import Polygon, Point


#%%
# Setup graph and configs

config = getConfig("../../conf.ini")

BASE_URL = config.get("API", "base_url")

# Create graph
g = createGraph()

# Create ANNCSU endpoint, with information about the dataset

# Create a ConceptScheme
ANNCSU_DATA = ConceptScheme(ANNCSU)

# Set the properties
ANNCSU_DATA.label = [
    Literal("Anagrafe nazionale numeri civici e strade urbane", lang="it"),
    Literal("Civic Addressing and Street Naming", lang="en")
]
ANNCSU_DATA.creator = [ONTO_AUTHOR]

# And add to graph
ANNCSU_DATA.addToGraph(g)

# %%
# Get the data

datasetID = config.get("ANNCSU", "dataset")

# ANNCSU streets
anncsuAddresses = getOpenData(
    BASE_URL, datasetID, config.get("ANNCSU", "streets"))
anncsuAddresses.set_index("PROGR_NAZIONALE", inplace=True)

# ANNCSU civic numbers
anncsuCivics = getOpenData(BASE_URL, datasetID, config.get("ANNCSU", "civics"))
anncsuCivics.set_index("PROGR_CIVICO", inplace=True)

# ISTAT census sections
censusSectionsObj = getOpenData(BASE_URL,
                                datasetID, config.get("ANNCSU", "census_sections"), rawData=True)

# Since this is a KML file, need to be parsed by pykml
censusSections = parser.parse(censusSectionsObj)


# %%
# Localities

localitiesDF = pd.DataFrame(
    anncsuAddresses["LOCALITA'"]).drop_duplicates().reset_index(drop=True)

# Add localities to graph
with alive_bar(len(localitiesDF), dual_line=True, title='🗺️ Localities') as bar:
    for i, locality in localitiesDF.iterrows():
        localityName = standardizeName(locality["LOCALITA'"])

        bar.text = f'-> Adding {localityName}'

        addressArea = AddressArea(
            id="locality/" + genNameForID(localityName),
            baseUri=ANNCSU,
            dataset=ANNCSU_DATA,
            titles=[
                Literal(localityName, datatype=XSD.string)
            ])

        addressArea.name = [Literal(localityName, datatype=XSD.string)]

        addressArea.addToGraph(g, isTopConcept=True)

        bar()

# %%
# Census sections

placemarks = censusSections.getroot().Document.Folder.Placemark
with alive_bar(len(placemarks), dual_line=True, title='🗺️ Census sections') as bar:
    for pm in placemarks:
        # ISTAT census sections are in the form {city_code}{census_number}, I need only the census number
        censID = int(str(pm.name)[6::])

        bar.text = f'-> Adding {censID}'

        # Get the polygon of census section's boundaries
        polygon = pm.Polygon.outerBoundaryIs.LinearRing.coordinates

        censusSection = CensusSection(
            id="cs/" + str(censID),
            baseUri=ANNCSU,
            dataset=ANNCSU_DATA,
            titles=[
                Literal("Sezione di censimento " + str(censID), lang="it"),
                Literal("Census section " + str(censID), lang="en")
            ])

        geometry = Geometry(
            id="gsc/" + str(censID),
            baseUri=ANNCSU,
            dataset=ANNCSU_DATA,
            titles=[
                Literal("Sezione di censimento " + str(censID), lang="it"),
                Literal("Census section " + str(censID), lang="en")
            ])

        geometry.hasGeometryType = Polygon()
        geometry.serialization = Literal(
            str(polygon).replace(" ", "\n"), datatype=XSD.string)

        censusSection.hasGeometry = [geometry]

        geometry.addToGraph(g, isTopConcept=False)
        censusSection.addToGraph(g, isTopConcept=True)

        bar()

# %%
# Street toponyms

with alive_bar(len(anncsuAddresses), dual_line=True, title='🗺️ Street toponyms') as bar:
    for streetID, address in anncsuAddresses.iterrows():
        # DUG is Denominazione Urbanistica Generica (Via, Piazza, etc...)
        dugName = standardizeName(address["DUG"])
        # The street name
        streetName = standardizeName(address["DENOM_COMPLETA"])

        # Full name of the street (DUG + DENOM)
        fullName = "{} {}".format(
            standardizeName(address["DUG"]),
            standardizeName(address["DENOM_COMPLETA"])
        )

        bar.text = f'-> Adding {fullName}'

        # Create street ref (st-streetID), where streetID is PROGR_NAZIONALE
        streetToponym = StreetToponym(
            id="street/" + str(streetID),
            baseUri=ANNCSU,
            dataset=ANNCSU_DATA,
            titles=[
                Literal(fullName, datatype=XSD.string)
            ])

        streetToponym.toponymQualifier = [
            Literal(dugName, datatype=XSD.string)]
        streetToponym.officialStreetName = [
            Literal(streetName, datatype=XSD.string)]

        streetToponym.addToGraph(g, isTopConcept=False)

        bar()

# %%
# Addresses

with alive_bar(len(anncsuCivics), dual_line=True, title='🏠 Addresses') as bar:
    for civicID, civic in anncsuCivics.iterrows():
        # Civic attributes
        civicNumber = civic["CIVICO"]
        civicExponent = civic["ESPONENTE"]
        civicPeculiarity = civic["SPECIFICITA"]
        civicMeter = civic["SISTEMA_METRICO"]
        streetID = civic["PROGR_NAZIONALE"]

        # Civic full name (eg: 10/A)
        civicFullName = "{}{}{}{}".format(
            civicNumber if not pd.isna(civicNumber) else "",
            "/" + civicExponent if not pd.isna(civicExponent) else "",
            civicMeter if not pd.isna(civicMeter) else "",
            " " + civicPeculiarity if not pd.isna(civicPeculiarity) else "",
        )

        # Get address information from streetID
        addressInfo = anncsuAddresses.loc[streetID]

        # PostCode from configuration
        postCode = config.get("ANNCSU", "postCode")

        # Get census ref
        censID = int(civic["SEZIONE_DI_CENSIMENTO"])

        censusSection = CensusSection(id="cs/" + str(censID), baseUri=ANNCSU)
        streetToponym = StreetToponym(
            id="street/" + str(streetID), baseUri=ANNCSU)

        civicNumbering = CivicNumbering(
            id="civic/" + str(civicID),
            baseUri=ANNCSU,
            dataset=ANNCSU_DATA,
            titles=[
                Literal(civicFullName, datatype=XSD.string)
            ])

        # Get address coordinates
        longitude = civic["COORDINATA_X"]
        latitude = civic["COORDINATA_Y"]
        altitude = civic["COORDINATA_Z"]

        # Get locality ref from address
        localityName = standardizeName(addressInfo["LOCALITA'"])
        addressArea = AddressArea(
            id="locality/" + genNameForID(localityName),
            baseUri=ANNCSU
        )

        # Create full name (dug street name, civic - postCode, locality)
        fullName = "{} {}, {} - {}, {}".format(
            standardizeName(addressInfo["DUG"]),
            standardizeName(addressInfo["DENOM_COMPLETA"]),
            civicFullName, postCode, localityName
        )

        bar.text = f'-> Adding {fullName}'

        # Add attributes
        if not pd.isna(civicNumber):
            civicNumbering.streetNumber = Literal(
                civicNumber, datatype=XSD.int)

        if not pd.isna(civicExponent):
            civicNumbering.exponent = Literal(
                civicExponent, datatype=XSD.string)

        if not pd.isna(civicPeculiarity):
            civicNumbering.peculiarity = Literal(
                civicPeculiarity, datatype=XSD.string)

        if not pd.isna(civicMeter):
            civicNumbering.metric = Literal(civicMeter, datatype=XSD.int)

        # Create final Address ref
        address = Address(
            id="ad-" + str(streetID) + "-" + str(civicID),
            baseUri=ANNCSU,
            dataset=ANNCSU_DATA,
            titles=[
                Literal(fullName, datatype=XSD.string)
            ])

        address.hasStreetToponym = streetToponym
        address.hasNumber = civicNumbering
        address.hasCensusSection = censusSection
        address.hasAddressArea = [addressArea]

        # Create geometry for Address with geographic positioning
        geometry = None
        if not pd.isna(longitude) and not pd.isna(latitude):
            geometry = Geometry(
                id="gcn/" + str(civicID),
                baseUri=ANNCSU,
                dataset=ANNCSU_DATA,
                titles=[
                    Literal(fullName, datatype=XSD.string)
                ]
            )

            geometry.hasGeometryType = Point()
            geometry.lat = Literal(latitude, datatype=XSD.double)
            geometry.long = Literal(longitude, datatype=XSD.double)

            if not pd.isna(altitude):
                geometry.alt = Literal(altitude, datatype=XSD.double)

            address.hasGeometry = [geometry]

        address.postCode = Literal(postCode, datatype=XSD.int)

        city = City(id=config.get("ANNCSU", "ontopia_ref"), baseUri=CITIES)
        address.hasCity = [city]

        if geometry:
            geometry.addToGraph(g, isTopConcept=False)
        civicNumbering.addToGraph(g, isTopConcept=False)
        address.addToGraph(g, isTopConcept=False)

        bar()


# %%
# SNC Addresses

with alive_bar(len(anncsuAddresses), dual_line=True, title='🏠 SNC Addresses') as bar:
    for streetID, addressInfo in anncsuAddresses.iterrows():
        # Civic attributes
        postCode = config.get("ANNCSU", "postCode")

        # Civic full name
        civicFullName = "snc"

        # PostCode from configuration
        postCode = config.get("ANNCSU", "postCode")

        # Get street toponym
        streetToponym = StreetToponym(
            id="street/" + str(streetID), baseUri=ANNCSU)

        # Get locality ref from address
        localityName = standardizeName(addressInfo["LOCALITA'"])
        addressArea = AddressArea(
            id="locality/" + genNameForID(localityName),
            baseUri=ANNCSU
        )

        # Create full name (dug street name, civic - postCode, locality)
        fullName = "{} {}, {} - {}, {}".format(
            standardizeName(addressInfo["DUG"]),
            standardizeName(addressInfo["DENOM_COMPLETA"]),
            civicFullName, postCode, localityName
        )

        bar.text = f'-> Adding {fullName}'

        # Create final Address ref
        address = Address(
            id="ad-" + str(streetID) + "-snc",
            baseUri=ANNCSU,
            dataset=ANNCSU_DATA,
            titles=[
                Literal(fullName, datatype=XSD.string)
            ])

        address.hasStreetToponym = streetToponym
        address.hasAddressArea = [addressArea]

        address.postCode = Literal(postCode, datatype=XSD.int)

        city = City(id=config.get("ANNCSU", "ontopia_ref"), baseUri=CITIES)
        address.hasCity = [city]

        address.addToGraph(g, isTopConcept=False)

        bar()


# %%
# Save graph

saveGraph(g, "anncsu")