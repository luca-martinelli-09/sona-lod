# %%
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parents[1]))

from utils import *

from rdflib import Literal, XSD, Graph

from ontoim_py.ontoim import *
from ontoim_py.ns import *

from ontopia_py import ConceptScheme, saveGraph

from ontopia_py.sm import *
from ontopia_py.ro import *
from ontopia_py.ti import *
from ontopia_py.clv import *
from ontopia_py.cpv import *
from ontopia_py.cov import *

# %%
# Get Data from indicepa.gov.it

config = getConfig("../../conf.ini")

ipaCode = config.get("MUNICIPALITY", "ipa_code")

# Create graph
g = createGraph()

# Create a ConceptScheme
MUNICIPALITY_DATASET = ConceptScheme(MUNICIPALITY_DATA)

# %%
# Load data

aooDF = getOpenData("cdaded04-f84e-4193-a720-47d6d5f422aa",
                    baseURL="https://indicepa.gov.it/ipa-dati", whereSQL=f"WHERE \"Codice_IPA\"='{ipaCode}'")

uoDF = getOpenData("b0aa1f6c-f135-4c8a-b416-396fed4e1a5d",
                   baseURL="https://indicepa.gov.it/ipa-dati", whereSQL=f"WHERE \"Codice_IPA\"='{ipaCode}'")

eInvoiceServicesDF = getOpenData("57bd2be0-4d3d-41cd-bdb8-2f0a60d6f490",
                                 baseURL="https://indicepa.gov.it/ipa-dati", whereSQL=f"WHERE \"Codice_IPA\"='{ipaCode}'")

officesDF = pd.concat([aooDF, uoDF], ignore_index=True)

# %%
# Insert referents
referentsDF = officesDF[["Nome_responsabile", "Cognome_responsabile",
                         "Telefono_responsabile", "Mail_responsabile"]].dropna().drop_duplicates(
    subset=["Nome_responsabile", "Cognome_responsabile"])

for _, referent in referentsDF.iterrows():
    nameRef = standardizeName(referent["Nome_responsabile"])
    surnameRef = standardizeName(referent["Cognome_responsabile"])
    mailRef = referent["Mail_responsabile"]
    phoneNumberRef = referent["Telefono_responsabile"]

    referent = Person(
        id="person/" + genNameForID(nameRef + " " + surnameRef),
        baseUri=MUNICIPALITY_DATA,
        dataset=MUNICIPALITY_DATASET,
        titles=[Literal(nameRef + " " + surnameRef, datatype=XSD.string)]
    )

    referent.givenName = Literal(nameRef, datatype=XSD.string)
    referent.familyName = Literal(surnameRef, datatype=XSD.string)

    onlineContactPointReferent = OnlineContactPoint(
        id="ocp/" + genNameForID(nameRef + " " + surnameRef),
        baseUri=MUNICIPALITY_DATA,
        dataset=MUNICIPALITY_DATASET,
        titles=[
            Literal("Online Contact Point for " +
                    nameRef + " " + surnameRef, lang="en"),
            Literal("Contatti per " + nameRef + " " + surnameRef, lang="it")
        ]
    )

    if mailRef != "":
      email = Email(
          id="email/" + genNameForID(mailRef),
          baseUri=MUNICIPALITY_DATA,
          dataset=MUNICIPALITY_DATASET,
          titles=[Literal(mailRef, datatype=XSD.string)]
      )
      email.emailAddress = Literal("mailto:" + mailRef, datatype=XSD.anyURI)
      email.hasEmailType = EmailType(id="042", baseUri=EROGATION_CHANNELS)
      email.addToGraph(g, isTopConcept=False)
      
      onlineContactPointReferent.hasEmail = [email]

    if phoneNumberRef:
      phone = Telephone(
          id="phone/" + phoneNumberRef,
          baseUri=MUNICIPALITY_DATA,
          dataset=MUNICIPALITY_DATASET,
          titles=[Literal(phoneNumberRef, datatype=XSD.string)]
      )
      phone.telephoneNumber = Literal(phoneNumberRef, datatype=XSD.string)
      phone.hasTelephoneType = TelephoneType(id="03", baseUri=EROGATION_CHANNELS)
      phone.addToGraph(g, isTopConcept=False)

      onlineContactPointReferent.hasTelephone = [phone]

    onlineContactPointReferent.addToGraph(g, isTopConcept=False)
    referent.addToGraph(g, isTopConcept=True)

    # Add contact point
    g.add((referent.uriRef, SM["hasOnlineContactPoint"], onlineContactPointReferent.uriRef))
    
# %%
# Insert organization

insertedSU = Graph()
insertedSU.parse("./supportUnits.rdf")

for _, office in officesDF.iterrows():
    isAOO = pd.isna(office["Codice_uni_uo"])

    denominazione = office["Denominazione_aoo"] if isAOO else office["Descrizione_uo"]
    denominazione = standardizeName(denominazione)

    publicOrganization = PublicOrganization(
      id=office["Codice_fiscale_ente"],
      baseUri=MUNICIPALITY_DATA
    )

    uoCode = office["Codice_uni_uo"]
    parentUOCode = office["Codice_uni_uo_padre"]
    aooCode = office["Codice_uni_aoo"]

    mails = [
        {"mail": office["Mail1"],
         "type": office["Tipo_Mail1"]},
        {"mail": office["Mail2"],
         "type": office["Tipo_Mail2"]},
        {"mail": office["Mail3"],
         "type": office["Tipo_Mail3"]},
    ]
    phoneNumber = office["Telefono"]
    faxNumber = office["Fax"]

    nameRef = office["Nome_responsabile"]
    surnameRef = office["Cognome_responsabile"]

    institutionDate = office["Data_istituzione"]

    # Office

    if isAOO:
      publicOffice = HomogeneousOrganizationalArea(
        id="aoo/" + aooCode,
        baseUri=MUNICIPALITY_DATA,
        dataset=MUNICIPALITY_DATASET,
        titles=[Literal(denominazione, datatype=XSD.string)]
      )
      publicOffice.AOOIdentifier = Literal(aooCode, datatype=XSD.string)
    else:
      publicOffice = Office(
        id="uo/" + uoCode,
        baseUri=MUNICIPALITY_DATA,
        dataset=MUNICIPALITY_DATASET,
        titles=[Literal(denominazione, datatype=XSD.string)]
      )
      publicOffice.officeIdentifier = Literal(uoCode, datatype=XSD.string)
    
    publicOffice.legalName = [Literal(denominazione, datatype=XSD.string)]
    
    if institutionDate != "":
      publicOffice.foundationDate = Literal(institutionDate, datatype=XSD.date)

    # Parent Departmentes

    publicOffice.isSupportUnitOf = []

    publicOrganization.hasSupportUnit = [publicOffice]
    publicOffice.isSupportUnitOf.append(publicOrganization)

    if not isAOO and parentUOCode != "":
      parentUO = Office(
          id="uo/" + parentUOCode,
          baseUri=MUNICIPALITY_DATA,
      )

      parentUO.hasSupportUnit = [publicOffice]
      publicOffice.isSupportUnitOf.append(parentUO)

      parentUO.addToGraph(g, onlyProperties=True)
    
    if not isAOO and aooCode != "":
      parentAOO = HomogeneousOrganizationalArea(
          id="aoo/" + aooCode,
          baseUri=MUNICIPALITY_DATA,
      )

      publicOffice.isPartOf = parentAOO

      parentAOO.addToGraph(g, onlyProperties=True)
    
    # Address
    alreadyInsertAddress = insertedSU.value(
        publicOffice.uriRef, CLV["hasPrimaryAddress"])

    if alreadyInsertAddress:
      addressID = str(insertedSU.value(publicOffice.uriRef,
                      CLV["hasPrimaryAddress"])).removeprefix(str(ANNCSU))
      address = Address(
          id=addressID,
          baseUri=ANNCSU
      )
      address.uriRef = alreadyInsertAddress
      publicOffice.hasPrimaryAddress = address
    else:
      address = office["Indirizzo"]
      progrNazionale, progrCivico = queryStreetCode(
          address) if address != "" else (None, None)

      if progrNazionale:
        progrCivico = progrCivico if progrCivico else "snc"

        address = Address(
            id="ad-{}-{}".format(progrNazionale, progrCivico),
            baseUri=ANNCSU
        )

        publicOffice.hasPrimaryAddress = address
    
    # Contact Point
    onlineContactPoint = OnlineContactPoint(
        id="ocp/" + (aooCode if isAOO else uoCode),
        baseUri=MUNICIPALITY_DATA,
        dataset=MUNICIPALITY_DATASET,
        titles=[
            Literal("Online Contact Point for " + denominazione, lang="en"),
            Literal("Contatti per " + denominazione, lang="en")
        ]
    )

    onlineContactPoint.hasEmail = []
    onlineContactPoint.hasCertifiedEmail = []
    onlineContactPoint.hasTelephone = []

    for mailInfo in mails:
      if mailInfo["mail"] != "":
        email = Email(
            id="email/" + genNameForID(mailInfo["mail"]),
            baseUri=MUNICIPALITY_DATA,
            dataset=MUNICIPALITY_DATASET,
            titles=[Literal(mailInfo["mail"], datatype=XSD.string)]
        )

        email.emailAddress = Literal(
            "mailto:" + mailInfo["mail"], datatype=XSD.anyURI)

        if mailInfo["type"].lower() == "pec":
          email.hasEmailType = EmailType(id="041", baseUri=EROGATION_CHANNELS)
          onlineContactPoint.hasCertifiedEmail.append(email)
        else:
          email.hasEmailType = EmailType(id="042", baseUri=EROGATION_CHANNELS)
          onlineContactPoint.hasEmail.append(email)

        email.addToGraph(g, isTopConcept=False)

    if phoneNumber != "":
      phone = Telephone(
          id="phone/" + phoneNumber,
          baseUri=MUNICIPALITY_DATA,
          dataset=MUNICIPALITY_DATASET,
          titles=[Literal(phoneNumber, datatype=XSD.string)]
      )
      phone.telephoneNumber = Literal(phoneNumber, datatype=XSD.string)
      phone.hasTelephoneType = TelephoneType(id="03", baseUri=EROGATION_CHANNELS)
      phone.addToGraph(g, isTopConcept=False)

      onlineContactPoint.hasTelephone.append(phone)

      if faxNumber != "":
        fax = Telephone(
            id="fax/" + faxNumber,
            baseUri=MUNICIPALITY_DATA,
            dataset=MUNICIPALITY_DATASET,
            titles=[Literal(faxNumber, datatype=XSD.string)]
        )
        fax.telephoneNumber = Literal(faxNumber, datatype=XSD.string)
        fax.hasTelephoneType = TelephoneType(id="033", baseUri=EROGATION_CHANNELS)
        fax.addToGraph(g, isTopConcept=False)

        onlineContactPoint.hasTelephone.append(fax)

    onlineContactPoint.addToGraph(g, isTopConcept=False)

    publicOffice.hasOnlineContactPoint = onlineContactPoint

    # Referent
    if nameRef != "":
      employment = Employment(
          id="referent/" + (aooCode if isAOO else uoCode),
          baseUri=MUNICIPALITY_DATA,
          dataset=MUNICIPALITY_DATASET,
          titles=[
            Literal("Referent for " + denominazione, lang="en"),
            Literal("Responsabile per " + denominazione, lang="it")
          ]
      )

      referent = Person(
        id="person/" +  genNameForID(nameRef + " " + surnameRef),
        baseUri=MUNICIPALITY_DATA
      )

      employment.employmentFor = publicOffice
      employment.withRole = [Role(
        id="referent",
        baseUri=ROLE_DATA
      )]
      employment.isRoleInTimeOf = [referent]

      employment.addToGraph(g, isTopConcept=False)

      g.add((referent.uriRef, RO["holdsRoleInTime"], employment.uriRef))

      publicOffice.holdEmployment = [employment]

      publicOffice.addToGraph(g, isTopConcept=True)

# %%
# eInvoice Services

for _, eInvoiceServiceInfo in eInvoiceServicesDF.iterrows():
  uoCode = eInvoiceServiceInfo["Codice_uni_uo"]
  uoName = standardizeName(eInvoiceServiceInfo["Descrizione_uo"])
  taxCodeEIS = eInvoiceServiceInfo["Codice_fiscale_sfe"]

  taxCodeValidationDate = eInvoiceServiceInfo["Data_verifica_cf"]
  startingDate = eInvoiceServiceInfo["Data_avvio_sfe"]

  eInvService = eInvoiceService(
      id="service/" + uoCode,
      baseUri=MUNICIPALITY_DATA,
      dataset=MUNICIPALITY_DATASET,
      titles=[
          Literal("eInvoice Service for " + uoName, lang="en"),
          Literal("Servizio di fatturazione elettronica per " + uoName, lang="it"),
      ]
  )

  eInvService.taxCodeEInvoiceService = Literal(taxCodeEIS, datatype=XSD.string)
  eInvService.taxCodeValidationDate = Literal(taxCodeValidationDate, datatype=XSD.date)
  eInvService.eInvoiceServiceStartingDate = Literal(startingDate, datatype=XSD.date)

  office = Office(
    id="uo/" + uoCode,
    baseUri=MUNICIPALITY_DATA
  )

  office.hasEInvoiceService = eInvService

  eInvService.addToGraph(g, isTopConcept=False)

  office.addToGraph(g, onlyProperties=True)

# %%
# Save graph

saveGraph(g, "supportUnits")