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

from codicefiscale import codicefiscale
from datetime import datetime
import re

# OntoPiA

from ontopia_py import ConceptScheme, saveGraph
from ontopia_py.ns import *
from ontopia_py.clv import *
from ontopia_py.sm import *
from ontopia_py.ti import *
from ontopia_py.cov import LegalStatus, PrivateOrgActivityType, BalanceSheet

# OntoIM

from ontoim_py.ontoim import *
from ontoim_py.ns import *

# %%
# Setup graph and configs

config = getConfig("../../conf.ini")

# Create Graph
g = createGraph()

# Create a ConceptScheme
ORGANIZATIONS_DATASET = ConceptScheme(COV_DATA)

# Set the properties
ORGANIZATIONS_DATASET.label = [
    Literal("Imprese", lang="it"),
    Literal("Companies", lang="en")
]
ORGANIZATIONS_DATASET.creator = [ONTO_AUTHOR]

# And add to graph
ORGANIZATIONS_DATASET.addToGraph(g)


# %%
# Get the data

# Organizations
organizations = getOpenData(config.get("ORGANIZATIONS", "organizations"), dtype={'PARTITA-IVA': str, 'C-FISCALE': str})
organizations = organizations.set_index(["PRG"])
organizations['PROGR_NAZIONALE'] = organizations['PROGR_NAZIONALE'].astype('Int64')
organizations['PROGR_CIVICO'] = organizations['PROGR_CIVICO'].astype('Int64')
organizations['AA-ADD'] = organizations['AA-ADD'].astype('Int64')
organizations['IND'] = organizations['IND'].astype('Int64')
organizations['DIP'] = organizations['DIP'].astype('Int64')

# Sort in order to have all sites first and then all the local units
organizations = organizations.sort_values(["UL-SEDE"])

legalStatuses = getOpenData(config.get("ORGANIZATIONS", "legal_statuses")).set_index(["CODICE"])
# %%
# Create emails, phones and websites (to avoid repetitions)

allPecs = pd.DataFrame(organizations["IND_PEC"]).dropna(
).drop_duplicates().set_index(["IND_PEC"])
for pecAddress, _ in allPecs.iterrows():
    pecAddress = pecAddress.lower()
    pec = Email(
        id="pec/" + genNameForID(pecAddress),
        baseUri=COV_DATA,
        dataset=ORGANIZATIONS_DATASET,
        titles=[Literal(pecAddress, datatype=XSD.string)]
    )

    pec.hasEmailType = EmailType(id="041", baseUri=EROGATION_CHANNELS)
    pec.emailAddress = Literal("mailto:" + pecAddress, datatype=XSD.anyURI)

    pec.addToGraph(g, isTopConcept=False)


# %%

def getDemographicFromCF(codFiscale):
    codes = []

    if codicefiscale.is_valid(codFiscale):
        data = codicefiscale.decode(codFiscale)

        if data["sex"] == "F":
            codes.append("1")
        
        if datetime.now().year - data["birthdate"].year <= 30:
            codes.append("2")

        if data["birthplace"] is None or data["birthplace"]["province"] == "EE":
            codes.append("3")
    
    return codes

# %%
# Insert data

insertedVATs = []

with alive_bar(len(organizations), dual_line=True, title='🏭 Organizations') as bar:
    for _, organizationInfo in organizations.iterrows():
        denominazione = standardizeName(organizationInfo["DENOMINAZIONE"])

        bar.text = f'-> Adding {denominazione}'

        vatCode = organizationInfo["PARTITA-IVA"]
        taxCode = organizationInfo["C-FISCALE"]
        reaCode = organizationInfo["PRV"] + str(organizationInfo["N-REA"])
        numArtisanRegister = organizationInfo["N-ALBO-AA"]
        
        if vatCode == "0":
            vatCode = taxCode
        else:
            vatCode = vatCode.zfill(11)

        codTipologia = legalStatuses.loc[organizationInfo["NG"]]["COD_ISTAT"].split(",")[0]
        registerSections = organizationInfo["SEZ-REG-IMP"]
        codsAteco = organizationInfo["CODICI-ATTIVITA"]
        demographicCategories = getDemographicFromCF(taxCode)

        pecAddress = organizationInfo["IND_PEC"]
        
        accreditationDate = organizationInfo["DT-ISCR-RI"]
        artisanRegistrationDate = organizationInfo["DT-ISCR-AA"]
        startActivityDate = organizationInfo["DT-INI-AT"]
        endActivityDate = organizationInfo["DT-CES-AT"]
        liquidationDate = organizationInfo["DT-LIQUID"]
        bankruptcyDate = organizationInfo["DT-FALLIM"]

        if pd.isna(startActivityDate):
            startActivityDate = organizationInfo["DT-APER-UL"]
        
        indipendentEmployees = organizationInfo["IND"] if not pd.isna(organizationInfo["IND"]) else 0
        dipendentEmployees = organizationInfo["DIP"] if not pd.isna(organizationInfo["DIP"]) else 0
        numEmployees = indipendentEmployees + dipendentEmployees

        availableMoneys = organizationInfo["CAPITALE"]
        valutaBalance = organizationInfo["VALUTA-CAPITALE"]
        
        referenceYear = organizationInfo["AA-ADD"]
        
        isMainSite = organizationInfo["UL-SEDE"] == "SEDE"
        progrNazionale = organizationInfo["PROGR_NAZIONALE"]
        progrCivico = organizationInfo["PROGR_CIVICO"] if not pd.isna(
            organizationInfo["PROGR_CIVICO"]) else "snc"
        
        # CHECK IF ALREADY INSERT (AND ADD LOCAL UNIT ADDRESS)

        notFirstInsert = vatCode in insertedVATs
        insertedVATs.append(vatCode)

        if notFirstInsert:
            organization = PrivateOrganization(
                id=str(vatCode),
                baseUri=COV_DATA
            )

            if not pd.isna(progrNazionale):
                address = Address(
                    id="ad-{}-{}".format(progrNazionale, progrCivico),
                    baseUri=ANNCSU
                )

                organization.hasLocalUnitAddress = [address]
            
                organization.addToGraph(g, onlyProperties=True)

            bar()
            continue

        # CREATE ORGANIZATION

        organization = PrivateOrganization(
            id=str(vatCode),
            baseUri=COV_DATA,
            dataset=ORGANIZATIONS_DATASET,
            titles=[Literal(denominazione, datatype=XSD.string)]
        )

        if not pd.isna(numArtisanRegister):
            organization = ArtisanOrganization(
                id=str(vatCode),
                baseUri=COV_DATA,
                dataset=ORGANIZATIONS_DATASET,
                titles=[Literal(denominazione, datatype=XSD.string)]
            )

        # ORGANIZATION IDENTIFIERS
        organization.legalName = [Literal(denominazione, datatype=XSD.string)]
        organization.VATnumber = Literal(vatCode, datatype=XSD.string)
        # omitted for privacy: organization.taxCode = Literal(taxCode, datatype=XSD.string)
        organization.REANumber = Literal(reaCode, datatype=XSD.string)

        if not pd.isna(numArtisanRegister):
            organization.artisanRegisterCode = Literal(
                numArtisanRegister, datatype=XSD.string)

        # ORGANIZATION SECTIONS AND STATUSES

        organization.hasLegalStatus = LegalStatus(
            id=codTipologia.replace(".", ""),
            baseUri=ORG_LEGAL_STATUS
        )

        if not pd.isna(registerSections) and registerSections.strip() != "":
            organization.hasOrganizationSection = [
                OrganizationSection(
                    id=section.strip(),
                    baseUri=ORGANIZATION_SECTIONS
                )
                for section in registerSections.split("-")
            ]

        if not pd.isna(codsAteco) and codsAteco.strip() != "":
            organization.hasPrivateOrgActivityType = [
                PrivateOrgActivityType(
                    id=re.sub("[^0-9]", "", ateco),
                    baseUri=ORG_ATECO
                )
                for ateco in codsAteco.split("/")
            ]
        
        if len(demographicCategories) > 0:
            organization.hasDemographicCategory = [
                CompanyDemographicCategory(
                    id=demographicCategory,
                    baseUri=COMPANY_DEMOGRAPHIC_CATEGORIES
                )
                for demographicCategory in demographicCategories
            ]
        
        # ORGANIZATION LIFE DATES
        
        if not pd.isna(accreditationDate):
            accreditationDate = datetime.strptime(
                accreditationDate, "%d/%m/%Y")
            organization.accreditationDate = Literal(
                accreditationDate, datatype=XSD.date)
        
        if not pd.isna(artisanRegistrationDate):
            artisanRegistrationDate = datetime.strptime(
                artisanRegistrationDate, "%d/%m/%Y")
            organization.artisanRegistrationDate = Literal(
                artisanRegistrationDate, datatype=XSD.date)
        
        if not pd.isna(startActivityDate):
            startActivityDate = datetime.strptime(
                startActivityDate, "%d/%m/%Y")
            organization.startingActivityDate = Literal(
                startActivityDate, datatype=XSD.date)

        if not pd.isna(endActivityDate):
            endActivityDate = datetime.strptime(
                endActivityDate, "%d/%m/%Y")
            organization.endActivityDate = Literal(
                endActivityDate, datatype=XSD.date)
        
        if not pd.isna(liquidationDate):
            liquidationDate = datetime.strptime(
                liquidationDate, "%d/%m/%Y")
            organization.liquidationDate = Literal(
                liquidationDate, datatype=XSD.date)

        if not pd.isna(bankruptcyDate):
            bankruptcyDate = datetime.strptime(
                bankruptcyDate, "%d/%m/%Y")
            organization.bankruptcyDate = Literal(
                bankruptcyDate, datatype=XSD.date)

        # ORGANIZATION ADDRESS

        if not pd.isna(progrNazionale):
            address = Address(
                id="ad-{}-{}".format(progrNazionale, progrCivico),
                baseUri=ANNCSU
            )

            if isMainSite:
                organization.hasPrimaryAddress = address
            else:
                organization.hasLocalUnitAddress = [address]
        
        # ORGANIZATION EMPLOYEES

        if not pd.isna(referenceYear) and numEmployees > 0:
            employees = Employees(
                id="stats/{}-{}".format(str(vatCode), str(referenceYear)),
                baseUri=COV_DATA,
                dataset=ORGANIZATIONS_DATASET,
                titles=[
                    Literal("Number of employees of {} in {}".format(
                        str(denominazione), str(referenceYear)), lang="en"),
                    Literal("Numero di dipendenti di {} in {}".format(
                        str(denominazione), str(referenceYear)), lang="it")
                ]
            )

            temporalEntity = Year(
                id="ti/{}-{}".format(str(vatCode), str(referenceYear)),
                baseUri=COV_DATA,
                dataset=ORGANIZATIONS_DATASET,
                titles=[
                    Literal("Temporal reference for the employees number of {} in {}".format(
                        str(denominazione), str(referenceYear)), lang="en"),
                    Literal("Riferimento temporale per il numero di dipendenti di {} in {}".format(
                        str(denominazione), str(referenceYear)), lang="it")
                ]
            )

            temporalEntity.year = Literal(referenceYear, datatype=XSD.gYear)
            temporalEntity.isTemporalEntityOf = [employees]

            employees.hasTemporalEntity = temporalEntity
            employees.observationValue = Literal(numEmployees, datatype=XSD.positiveInteger)

            employees.addToGraph(g, isTopConcept=False)
            temporalEntity.addToGraph(g, isTopConcept=False)

            organization.hasEmployees = [employees]
        
        # ORGANIZATION BALANCE SHEET

        if not pd.isna(availableMoneys):
            availableMoneys = float(availableMoneys.replace(".", "").replace(",", "."))

            if valutaBalance != "EURO":
                availableMoneys = availableMoneys / 1936.27
            
            balanceSheet = BalanceSheet(
                id="capital/" + str(vatCode),
                baseUri=COV_DATA,
                dataset=ORGANIZATIONS_DATASET,
                titles=[
                    Literal("Capital of {}".format(
                        denominazione), lang="en"),
                    Literal("Capitale di {}".format(
                        denominazione), lang="it"),
                ]
            )

            balanceSheet.totalAmount = Literal(availableMoneys, datatype=XSD.float)

            balanceSheet.addToGraph(g, isTopConcept=False)
            organization.hasBalanceSheet = [balanceSheet]

        # ORGANIZATION CONTACT POINT
        
        onlineContactPoint = OnlineContactPoint(
            id="ocp/" + str(vatCode),
            baseUri=COV_DATA,
            dataset=ORGANIZATIONS_DATASET,
            titles=[
                Literal("Informazioni di contatto per " +
                        denominazione, lang="it"),
                Literal("Contact information for " + denominazione, lang="en"),
            ]
        )

        if not pd.isna(pecAddress):
            pec = Email(
                id="pec/" + genNameForID(pecAddress),
                baseUri=COV_DATA
            )
            onlineContactPoint.hasCertifiedEmail = [pec]

            organization.hasOnlineContactPoint = onlineContactPoint

            onlineContactPoint.addToGraph(g, isTopConcept=False)

        organization.addToGraph(g, isTopConcept=True)

        bar()


# %%
# Save graph
saveGraph(g, "organizations")


