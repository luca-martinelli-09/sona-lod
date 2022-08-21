# %%
# Utils

from rdflib import Literal, Graph, URIRef
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parents[1]))

from utils import *

# Pandas and others

import pandas as pd
from pykml import parser


from rdflib.namespace import XSD, OWL

from alive_progress import alive_bar

# OntoPiA

from ontopia_py import ConceptScheme, saveGraph
from ontopia_py.ns import *
from ontopia_py.clv import *
from ontopia_py.clv.GeometryType import Polygon, Point


#%%
# Setup graph and configs

config = getConfig("../../conf.ini")

# Create graph
g : Graph = createGraph()

# Create ANNCSU endpoint, with information about the dataset

# Create a ConceptScheme
ANNCSU_DATASET = ConceptScheme(ANNCSU)

# Set the properties
ANNCSU_DATASET.label = [
    Literal("Anagrafe nazionale numeri civici e strade urbane", lang="it"),
    Literal("Civic Addressing and Street Naming", lang="en")
]
ANNCSU_DATASET.creator = [ONTO_AUTHOR]

# And add to graph
ANNCSU_DATASET.addToGraph(g)

# %%
# Get the data

# ANNCSU streets
anncsuAddresses = getOpenData(config.get("ANNCSU", "streets"))
anncsuAddresses.set_index("PROGR_NAZIONALE", inplace=True)

# ANNCSU civic numbers
anncsuCivics = getOpenData(config.get("ANNCSU", "civics"))
anncsuCivics.set_index("PROGR_CIVICO", inplace=True)

# ISTAT census sections
censusSectionsObj = getOpenData(config.get("ANNCSU", "census_sections"), rawData=True)

# Since this is a KML file, need to be parsed by pykml
censusSections = parser.parse(censusSectionsObj)

# %%

# Add Sona

Sona = City(
    id="023083",
    baseUri=ANNCSU,
    dataset=ANNCSU_DATASET,
    titles=[Literal("Sona", datatype=XSD.string)]
)

Sona.hasHigherRank = [
    Country(id="ITA", baseUri=ITALY),
    GeographicalDistribution(id="2", baseUri=GEO_DISTRIBUTION),
    Region(id="05", baseUri=REGIONS),
    Province(id="023", baseUri=PROVINCES)
]

Sona.hasDirectHigherRank = [
    Province(id="023", baseUri=PROVINCES)
]

Sona.name = [Literal("Sona", datatype=XSD.string)]

Sona.addToGraph(g, isTopConcept=True)

g.add((Sona.uriRef, OWL.sameAs, URIRef("http://dbpedia.org/resource/Sona,_Veneto")))
g.add((Sona.uriRef, OWL.sameAs, URIRef("http://dati.beniculturali.it/mibact/luoghi/resource/City/Sona")))
g.add((Sona.uriRef, OWL.sameAs, URIRef("https://w3id.org/arco/resource/City/sona")))
g.add((Sona.uriRef, OWL.sameAs, URIRef("http://dati.san.beniculturali.it/SAN/luogo_Sona")))
g.add((Sona.uriRef, OWL.sameAs, URIRef("http://dati.isprambiente.it/id/place/23083")))
g.add((Sona.uriRef, OWL.sameAs, URIRef("https://dati.beniculturali.it/lodview/iccd/schede/resource/City/SONA")))
g.add((Sona.uriRef, OWL.sameAs, URIRef("https://dati.beniculturali.it/lodview/iccu/anagrafe/resource/City/023083")))
g.add((Sona.uriRef, OWL.sameAs, URIRef("http://dati.san.beniculturali.it/ASI/UA03483")))
g.add((Sona.uriRef, OWL.sameAs, City(id="023083-(1975-01-29)", baseUri=CITIES).uriRef))

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
            dataset=ANNCSU_DATASET,
            titles=[
                Literal(localityName, datatype=XSD.string)
            ])

        addressArea.name = [Literal(localityName, datatype=XSD.string)]

        addressArea.situatedWithin = [Sona]

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
            dataset=ANNCSU_DATASET,
            titles=[
                Literal("Sezione di censimento " + str(censID), lang="it"),
                Literal("Census section " + str(censID), lang="en")
            ])

        geometry = Geometry(
            id="gsc/" + str(censID),
            baseUri=ANNCSU,
            dataset=ANNCSU_DATASET,
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
            dataset=ANNCSU_DATASET,
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
        postCode = config.get("ANNCSU", "post_code")

        # Get census ref
        censID = int(civic["SEZIONE_DI_CENSIMENTO"])

        censusSection = CensusSection(id="cs/" + str(censID), baseUri=ANNCSU)
        streetToponym = StreetToponym(
            id="street/" + str(streetID), baseUri=ANNCSU)

        civicNumbering = CivicNumbering(
            id="civic/" + str(civicID),
            baseUri=ANNCSU,
            dataset=ANNCSU_DATASET,
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
            dataset=ANNCSU_DATASET,
            titles=[
                Literal(fullName, datatype=XSD.string)
            ])

        address.postCode = Literal(postCode, datatype=XSD.int)

        address.hasNumber = civicNumbering

        address.hasStreetToponym = streetToponym
        address.hasCensusSection = censusSection
        address.hasAddressArea = [addressArea]
        address.hasCity = [Sona]
        address.hasProvince = [Province(id="023", baseUri=PROVINCES)]
        address.hasRegion = [Region(id="05", baseUri=REGIONS)]
        address.hasAddressComponent = [
            GeographicalDistribution(id="2", baseUri=GEO_DISTRIBUTION)]
        address.hasCountry = [Country(id="ITA", baseUri=ITALY)]

        # Create geometry for Address with geographic positioning
        geometry = None
        if not pd.isna(longitude) and not pd.isna(latitude):
            geometry = Geometry(
                id="gcn/" + str(civicID),
                baseUri=ANNCSU,
                dataset=ANNCSU_DATASET,
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
            
            geometry.addToGraph(g, isTopConcept=False)
        
        civicNumbering.addToGraph(g, isTopConcept=False)
        address.addToGraph(g, isTopConcept=False)

        bar()


# %%
# SNC Addresses

with alive_bar(len(anncsuAddresses), dual_line=True, title='🏠 SNC Addresses') as bar:
    for streetID, addressInfo in anncsuAddresses.iterrows():
        # Civic full name
        civicFullName = "snc"

        # PostCode from configuration
        postCode = config.get("ANNCSU", "post_code")

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
            dataset=ANNCSU_DATASET,
            titles=[
                Literal(fullName, datatype=XSD.string)
            ])

        address.postCode = Literal(postCode, datatype=XSD.int)

        address.hasStreetToponym = streetToponym
        address.hasAddressArea = [addressArea]
        address.hasCity = [Sona]
        address.hasProvince = [Province(id="023", baseUri=PROVINCES)]
        address.hasRegion = [Region(id="05", baseUri=REGIONS)]
        address.hasAddressComponent = [
            GeographicalDistribution(id="2", baseUri=GEO_DISTRIBUTION)]
        address.hasCountry = [Country(id="ITA", baseUri=ITALY)]

        address.addToGraph(g, isTopConcept=False)

        bar()


# %%
# Save graph

saveGraph(g, "anncsu")