# %%
# Utils

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parents[1]))

from utils import *

# Pandas and others

import pandas as pd

from rdflib import Literal

from rdflib.namespace import XSD

from alive_progress import alive_bar

# OntoPiA

from ontopia_py import ConceptScheme, saveGraph
from ontopia_py.ns import *
from ontopia_py.clv import *
from ontopia_py.cov import *
from ontopia_py.sm import *
from ontopia_py.acco import *
from ontopia_py.poi import *
from ontopia_py.cpv import *

# %%
# Setup graph and configs

config = getConfig("../../conf.ini")

# Create graph
g = createGraph()

# Create a ConceptScheme
ACCOMMODATION_DATASET = ConceptScheme(ACCO_DATA)

# Set the properties
ACCOMMODATION_DATASET.label = [
    Literal("Strutture ricettive e locazioni turistiche", lang="it"),
    Literal("Accommodation facilities and resorts", lang="en")
]
ACCOMMODATION_DATASET.creator = [ONTO_AUTHOR]

# And add to graph
ACCOMMODATION_DATASET.addToGraph(g)


# %%
# Get the data

# Accomodation facilities
accommodationFacilities = getOpenData(config.get("ACCOMMODATIONS", "accommodation_facilities"), dtype={'IVA': str, 'TELEFONO': str, 'STELLE': str, 'FAX': str})
accommodationFacilities = accommodationFacilities.set_index(
    ["CODICE_IDENTIFICATIVO"])

# Resorts
resorts = getOpenData(config.get("ACCOMMODATIONS", "resorts"), dtype={'IVA': str})
resorts = resorts.set_index(["CODICE_ALLOGGIO"])

# %%
# Features and statuses

features = getOpenData(config.get("ACCOMMODATIONS", "features")).set_index(["CODICE"])
statuses = getOpenData(config.get("ACCOMMODATIONS", "statuses")).set_index(["CODICE"])

for code, feature in features.iterrows():
    osdFeature = OSDFeature(
        id="feature/" + code,
        baseUri=ACCO_DATA,
        dataset=ACCOMMODATION_DATASET,
        titles=[
            Literal(feature["ITA"], lang="it"),
            Literal(feature["ENG"], lang="en")
        ]
    )

    osdFeature.featureName = [
        Literal(feature["ITA"], lang="it"),
        Literal(feature["ENG"], lang="en")
    ]

    osdDescription = OfferedServiceDescription(
        id="service/" + code,
        baseUri=ACCO_DATA,
        dataset=ACCOMMODATION_DATASET,
        titles=[
            Literal(feature["ITA"], lang="it"),
            Literal(feature["ENG"], lang="en")
        ]
    )

    osdDescription.hasOSDFeature = [osdFeature]

    # Add to graph
    osdFeature.addToGraph(g, isTopConcept=False)
    osdDescription.addToGraph(g, isTopConcept=False)


for code, status in statuses.iterrows():
    poiState = POIState(
        id="status/" + code,
        baseUri=ACCO_DATA,
        dataset=ACCOMMODATION_DATASET,
        titles=[
            Literal(status["ITA"], lang="it"),
            Literal(status["ENG"], lang="en")
        ]
    )

    poiState.POIstate = [
        Literal(status["ITA"], lang="it"),
        Literal(status["ENG"], lang="en")
    ]

    poiState.addToGraph(g, isTopConcept=False)


# %%
# Create emails, phones and websites (to avoid repetitions)

allEmails = pd.concat([pd.DataFrame(accommodationFacilities["EMAIL"]),
                       pd.DataFrame(resorts["EMAIL"])]).dropna().drop_duplicates().set_index(["EMAIL"])
for emailAddress, _ in allEmails.iterrows():
    email = Email(
        id="ocp/mail/" + genNameForID(emailAddress),
        baseUri=ACCO_DATA,
        dataset=ACCOMMODATION_DATASET,
        titles=[Literal(emailAddress, datatype=XSD.string)]
    )

    email.hasEmailType = EmailType(id="042", baseUri=EROGATION_CHANNELS)
    email.emailAddress = Literal("mailto:" + emailAddress, datatype=XSD.anyURI)

    email.addToGraph(g, isTopConcept=False)

allPecs = pd.DataFrame(resorts["PEC"]).dropna(
).drop_duplicates().set_index(["PEC"])
for pecAddress, _ in allPecs.iterrows():
    pec = Email(
        id="ocp/pec/" + genNameForID(pecAddress),
        baseUri=ACCO_DATA,
        dataset=ACCOMMODATION_DATASET,
        titles=[Literal(pecAddress, datatype=XSD.string)]
    )

    pec.hasEmailType = EmailType(id="041", baseUri=EROGATION_CHANNELS)
    pec.emailAddress = Literal("mailto:" + pecAddress, datatype=XSD.anyURI)

    pec.addToGraph(g, isTopConcept=False)

allPhones = pd.DataFrame(accommodationFacilities["TELEFONO"])
allPhones['TELEFONO'] = allPhones['TELEFONO'].str.split(",")
allPhones = allPhones.explode(
    'TELEFONO').dropna().drop_duplicates().set_index(["TELEFONO"])
for phoneNumber, _ in allPhones.iterrows():
    phone = Telephone(
        id="ocp/tel/" + genNameForID(phoneNumber),
        baseUri=ACCO_DATA,
        dataset=ACCOMMODATION_DATASET,
        titles=[Literal(phoneNumber, datatype=XSD.string)]
    )

    phone.hasTelephoneType = TelephoneType(id="03", baseUri=EROGATION_CHANNELS)
    phone.telephoneNumber = Literal(phoneNumber, datatype=XSD.string)

    phone.addToGraph(g, isTopConcept=False)

allFaxes = pd.DataFrame(accommodationFacilities["FAX"]).dropna(
).drop_duplicates().set_index(["FAX"])
for faxNumber, _ in allPhones.iterrows():
    fax = Telephone(
        id="ocp/fax/" + genNameForID(faxNumber),
        baseUri=ACCO_DATA,
        dataset=ACCOMMODATION_DATASET,
        titles=[Literal(faxNumber, datatype=XSD.string)]
    )

    fax.hasTelephoneType = TelephoneType(id="033", baseUri=EROGATION_CHANNELS)
    fax.telephoneNumber = Literal(faxNumber, datatype=XSD.string)

    fax.addToGraph(g, isTopConcept=False)

allWebsites = pd.concat([pd.DataFrame(accommodationFacilities["SITO"]),
                         pd.DataFrame(resorts["SITO"])]).dropna().drop_duplicates().set_index(["SITO"])
for websiteUri, _ in allWebsites.iterrows():
    website = WebSite(
        id="ocp/website/" + genNameForID(websiteUri),
        baseUri=ACCO_DATA,
        dataset=ACCOMMODATION_DATASET,
        titles=[Literal(websiteUri, datatype=XSD.string)]
    )

    website.URL = Literal(websiteUri, datatype=XSD.anyURI)

    website.addToGraph(g, isTopConcept=False)


# %%
# Accommodation facilities

with alive_bar(len(accommodationFacilities), dual_line=True, title='🛏️ Accommodation facilities') as bar:
    for codAccommodation, accoInfo in accommodationFacilities.iterrows():
        denominazione = standardizeName(accoInfo["DENOMINAZIONE"])

        bar.text = f'-> Adding {denominazione}'

        codPOI = accoInfo["COD_POI"]

        codAcco = accoInfo["COD_ACCO"]
        stars = accoInfo["STELLE"]

        vatCode = accoInfo["IVA"]
        phoneNumbers = accoInfo["TELEFONO"]
        faxNumber = accoInfo["FAX"]
        emailAddress = accoInfo["EMAIL"]
        websiteUri = accoInfo["SITO"]

        status = accoInfo["CODICE_STATO"]

        features = accoInfo["SERVIZI"]

        progrNazionale = accoInfo["PROGR_NAZIONALE"]
        progrCivico = accoInfo["PROGR_CIVICO"] if not pd.isna(
            accoInfo["PROGR_CIVICO"]) else "snc"

        # Create accommodation
        accommodation = Accommodation(
            id="accommodation/" + str(codAccommodation),
            baseUri=ACCO_DATA,
            dataset=ACCOMMODATION_DATASET,
            titles=[Literal(denominazione, datatype=XSD.string)]
        )

        accommodation.POIofficialName = [
            Literal(denominazione, datatype=XSD.string)]
        accommodation.hasAccommodationTypology = [
            AccommodationTypology(id=codAcco, baseUri=ACCO_TYPES)]
        accommodation.hasPOICategory = [PointOfInterestCategory(
            id=codPOI, baseUri=POI_CLASSIFICATION)]
        accommodation.accommodationCode = [
            Literal(codAccommodation, datatype=XSD.string)]
        accommodation.hasPOIState = POIState(
            id="status/" + status, baseUri=ACCO_DATA)

        # Organization that own the accommodation
        if not pd.isna(vatCode):
            organization = Organization(
                id=vatCode,
                baseUri=COV_DATA
            )
            accommodation.hasAccommodationOwner = organization

        if not pd.isna(stars):
            accommodation.hasAccommodationClassification = AccommodationStarRating(
                id=str(stars), baseUri=ACCO_STAR_RATINGS)

        # Add features offered
        accommodation.hasOfferedServiceDescription = []
        if not pd.isna(features):
            for feature in str(features).split(","):
                offeredServiceDescription = OfferedServiceDescription(
                    id="service/" + feature,
                    baseUri=ACCO_DATA
                )
                accommodation.hasOfferedServiceDescription.append(
                    offeredServiceDescription)

        # Get address reference
        if not pd.isna(progrNazionale):
            address = Address(
                id="ad-{}-{}".format(progrNazionale, progrCivico),
                baseUri=ANNCSU
            )

            accommodation.hasAddress = [address]

        # Create online contact point
        onlineContactPoint = None
        if not (pd.isna(phoneNumbers) and pd.isna(emailAddress) and pd.isna(websiteUri)):
            onlineContactPoint = OnlineContactPoint(
                id="ocp/" + str(codAccommodation),
                baseUri=ACCO_DATA,
                dataset=ACCOMMODATION_DATASET,
                titles=[
                    Literal("Informazioni di contatto per " +
                            denominazione, lang="it"),
                    Literal("Contact information for " +
                            denominazione, lang="en"),
                ]
            )

            if not pd.isna(phoneNumbers):
                onlineContactPoint.hasTelephone = []
                for phoneNumber in str(phoneNumbers).split(","):
                    phone = Telephone(
                        id="ocp/tel/" + genNameForID(phoneNumber), baseUri=ACCO_DATA)
                    onlineContactPoint.hasTelephone.append(phone)

            if not pd.isna(emailAddress):
                email = Email(id="ocp/mail/" + genNameForID(emailAddress),
                              baseUri=ACCO_DATA)
                onlineContactPoint.hasEmail = [email]

            if not pd.isna(faxNumber):
                fax = Telephone(
                    id="ocp/fax/" + genNameForID(faxNumber), baseUri=ACCO_DATA)
                onlineContactPoint.hasTelephone.append(fax)

            if not pd.isna(websiteUri):
                website = WebSite(
                    id="ocp/website/" + genNameForID(websiteUri),
                    baseUri=ACCO_DATA
                )
                onlineContactPoint.hasWebSite = [website]

        # Add all to graph
        onlineContactPoint.addToGraph(g, isTopConcept=False)
        accommodation.hasOnlineContactPoint = onlineContactPoint
        accommodation.addToGraph(g, isTopConcept=True)

        bar()


# %%
# Owners of resorts

allPeople = pd.DataFrame({"COGNOME": resorts["COGNOME"], "NOME": resorts["NOME"]}).dropna(
).drop_duplicates().set_index(["COGNOME", "NOME"])
for (surname, name), _ in allPeople.iterrows():
    name = standardizeName(name)
    surname = standardizeName(surname)

    person = Person(
        id="person/" + genNameForID(surname) + "-" + genNameForID(name),
        baseUri=ACCO_DATA,
        dataset=ACCOMMODATION_DATASET,
        titles=[Literal(name + " " + surname, datatype=XSD.string)]
    )
    person.givenName = Literal(name, datatype=XSD.string)
    person.familyName = Literal(surname, datatype=XSD.string)

    person.addToGraph(g, isTopConcept=False)


# %%
# Resorts

with alive_bar(len(resorts), dual_line=True, title='🛏️ Resorts') as bar:
    for codResort, resortInfo in resorts.iterrows():
        denominazione = standardizeName(resortInfo["DENOMINAZIONE"])

        bar.text = f'-> Adding {denominazione}'

        codPOI = resortInfo["COD_POI"]
        codAcco = resortInfo["COD_ACCO"]

        vatCode = resortInfo["IVA"]
        surnameLocator = standardizeName(resortInfo["COGNOME"])
        nameLocator = standardizeName(resortInfo["NOME"])

        emailAddress = resortInfo["EMAIL"]
        pecAddress = resortInfo["PEC"]
        websiteUri = resortInfo["SITO"]

        status = "open"

        totalRooms = resortInfo["NUM_CAMERE"]
        totalBeds = resortInfo["NUM_LETTI"]

        progrNazionale = resortInfo["PROGR_NAZIONALE"]
        progrCivico = resortInfo["PROGR_CIVICO"] if not pd.isna(
            resortInfo["PROGR_CIVICO"]) else "snc"

        # Create accommodation
        accommodation = Accommodation(
            id="resort/" + str(codResort),
            baseUri=ACCO_DATA,
            dataset=ACCOMMODATION_DATASET,
            titles=[Literal(denominazione, datatype=XSD.string)]
        )

        accommodation.POIofficialName = [
            Literal(denominazione, datatype=XSD.string)]
        accommodation.hasAccommodationTypology = [
            AccommodationTypology(id=codAcco, baseUri=ACCO_TYPES)]
        accommodation.hasPOICategory = [PointOfInterestCategory(
            id=codPOI, baseUri=POI_CLASSIFICATION)]
        accommodation.accommodationCode = [
            Literal(codResort, datatype=XSD.string)]
        accommodation.hasPOIState = POIState(
            id="status/" + status, baseUri=ACCO_DATA)

        # Organization or person that own the accommodation
        if not pd.isna(vatCode):
            organization = Organization(
                id=vatCode,
                baseUri=COV_DATA
            )
            accommodation.hasAccommodationOwner = organization
        else:
            person = Person(id="person/" + genNameForID(surnameLocator) +
                            "-" + genNameForID(nameLocator), baseUri=ACCO_DATA)
            accommodation.hasAccommodationOwner = person

        # Get address reference
        if not pd.isna(progrNazionale):
            address = Address(
                id="ad-{}-{}".format(progrNazionale, progrCivico),
                baseUri=ANNCSU
            )

            accommodation.hasAddress = [address]

        # Create online contact point
        onlineContactPoint = None
        if not (pd.isna(emailAddress) and pd.isna(pecAddress) and pd.isna(websiteUri)):
            onlineContactPoint = OnlineContactPoint(
                id="ocp/" + str(codResort),
                baseUri=ACCO_DATA,
                dataset=ACCOMMODATION_DATASET,
                titles=[
                    Literal("Informazioni di contatto per " +
                            denominazione, lang="it"),
                    Literal("Contact information for " +
                            denominazione, lang="en"),
                ]
            )

            if not pd.isna(emailAddress):
                email = Email(id="ocp/mail/" + genNameForID(emailAddress),
                              baseUri=ACCO_DATA)
                onlineContactPoint.hasEmail = [email]

            if not pd.isna(pecAddress):
                pec = Email(id="ocp/pec/" + genNameForID(pecAddress),
                            baseUri=ACCO_DATA)
                onlineContactPoint.hasCertifiedEmail = [pec]

            if not pd.isna(websiteUri):
                website = WebSite(
                    id="ocp/website/" + genNameForID(websiteUri),
                    baseUri=ACCO_DATA
                )
                onlineContactPoint.hasWebSite = [website]
        
        accommodation.totalBed = Literal(totalBeds, datatype=XSD.integer)
        accommodation.totalRoom = Literal(totalRooms, datatype=XSD.integer)

        # Add all to graph
        onlineContactPoint.addToGraph(g, isTopConcept=False)
        accommodation.hasOnlineContactPoint = onlineContactPoint
        accommodation.addToGraph(g, isTopConcept=True)

        bar()


# %%
# Save graph
saveGraph(g, "accommodationFacilities")
