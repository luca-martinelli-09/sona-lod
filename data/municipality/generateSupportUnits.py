# %%
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parents[1]))

from utils import *

from rdflib import Literal, XSD

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
MUNICIPALITY_DATA = ConceptScheme(MUN_DATA)

# %%
# Load data

aooDF = getDataFromCKANApi(
    "https://indicepa.gov.it/ipa-dati/api/3/action/datastore_search_sql?sql=SELECT%20*%20from%20%22cdaded04-f84e-4193-a720-47d6d5f422aa%22%20WHERE%20%22Codice_IPA%22%20=%20%27" + ipaCode + "%27")

uoDF = getDataFromCKANApi(
    "https://indicepa.gov.it/ipa-dati/api/3/action/datastore_search_sql?sql=SELECT%20*%20from%20%22b0aa1f6c-f135-4c8a-b416-396fed4e1a5d%22%20WHERE%20%22Codice_IPA%22%20=%20%27" + ipaCode + "%27")

eInvoiceServicesDF = getDataFromCKANApi(
    "https://indicepa.gov.it/ipa-dati/api/3/action/datastore_search_sql?sql=SELECT%20*%20from%20%2257bd2be0-4d3d-41cd-bdb8-2f0a60d6f490%22%20WHERE%20%22Codice_IPA%22%20=%20%27" + ipaCode + "%27"
)

officesDF = pd.concat([aooDF, uoDF], ignore_index=True)

# %%
# Insert referents
referentsDF = officesDF[["Nome_responsabile", "Cognome_responsabile",
                         "Telefono_responsabile", "Mail_responsabile"]].dropna().drop_duplicates(
    subset=["Nome_responsabile", "Cognome_responsabile"])

for _, referent in referentsDF.iterrows():
    nameRef = referent["Nome_responsabile"]
    surnameRef = referent["Cognome_responsabile"]
    mailRef = referent["Mail_responsabile"]
    phoneNumberRef = referent["Telefono_responsabile"]

    referent = Person(
        id="person/" + genNameForID(nameRef + " " + surnameRef),
        baseUri=MUN_DATA,
        dataset=MUNICIPALITY_DATA,
        titles=[Literal(nameRef + " " + surnameRef, datatype=XSD.string)]
    )

    referent.givenName = Literal(nameRef, datatype=XSD.string)
    referent.familyName = Literal(surnameRef, datatype=XSD.string)

    onlineContactPointReferent = OnlineContactPoint(
        id="ocp/" + genNameForID(nameRef + " " + surnameRef),
        baseUri=MUN_DATA,
        dataset=MUNICIPALITY_DATA,
        titles=[
            Literal("Online Contact Point for " +
                    nameRef + " " + surnameRef, lang="en"),
            Literal("Contatti per " + nameRef + " " + surnameRef, lang="it")
        ]
    )

    if mailRef != "":
      email = Email(
          id="email/" + genNameForID(mailRef),
          baseUri=MUN_DATA,
          dataset=MUNICIPALITY_DATA,
          titles=[Literal(mailRef, datatype=XSD.string)]
      )
      email.emailAddress = Literal("mailto:" + mailRef, datatype=XSD.anyURI)
      email.hasEmailType = EmailType(id="042", baseUri=EROGATION_CHANNELS)
      email.addToGraph(g, isTopConcept=False)
      
      onlineContactPointReferent.hasEmail = [email]

    if phoneNumberRef:
      phone = Telephone(
          id="phone/" + phoneNumberRef,
          baseUri=MUN_DATA,
          dataset=MUNICIPALITY_DATA,
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

for _, office in officesDF.iterrows():
    isAOO = pd.isna(office["Codice_uni_uo"])

    denominazione = office["Denominazione_aoo"] if isAOO else office["Descrizione_uo"]

    publicOrganization = PublicOrganization(
      id=office["Codice_fiscale_ente"],
      baseUri=MUN_DATA
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
        baseUri=MUN_DATA,
        dataset=MUNICIPALITY_DATA,
        titles=[Literal(denominazione, datatype=XSD.string)]
      )
      publicOffice.AOOIdentifier = Literal(aooCode, datatype=XSD.string)
    else:
      publicOffice = Office(
        id="uo/" + uoCode,
        baseUri=MUN_DATA,
        dataset=MUNICIPALITY_DATA,
        titles=[Literal(denominazione, datatype=XSD.string)]
      )
      publicOffice.officeIdentifier = Literal(uoCode, datatype=XSD.string)
    
    if institutionDate != "":
      publicOffice.foundationDate = Literal(institutionDate, datatype=XSD.date)

    # Parent Departmentes

    publicOffice.isSupportUnitOf = []

    publicOrganization.hasSupportUnit = [publicOffice]
    publicOffice.isSupportUnitOf.append(publicOrganization)

    if not isAOO and parentUOCode != "":
      parentUO = Office(
          id="uo/" + parentUOCode,
          baseUri=MUN_DATA,
      )

      parentUO.hasSupportUnit = [publicOffice]
      publicOffice.isSupportUnitOf.append(parentUO)

      parentUO.addToGraph(g, onlyProperties=True)
    
    if not isAOO and aooCode != "":
      parentAOO = HomogeneousOrganizationalArea(
          id="aoo/" + aooCode,
          baseUri=MUN_DATA,
      )

      publicOffice.isPartOf = parentAOO

      parentAOO.addToGraph(g, onlyProperties=True)
    
    # Contact Point
    onlineContactPoint = OnlineContactPoint(
        id="ocp/" + (aooCode if isAOO else uoCode),
        baseUri=MUN_DATA,
        dataset=MUNICIPALITY_DATA,
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
            baseUri=MUN_DATA,
            dataset=MUNICIPALITY_DATA,
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
          baseUri=MUN_DATA,
          dataset=MUNICIPALITY_DATA,
          titles=[Literal(phoneNumber, datatype=XSD.string)]
      )
      phone.telephoneNumber = Literal(phoneNumber, datatype=XSD.string)
      phone.hasTelephoneType = TelephoneType(id="03", baseUri=EROGATION_CHANNELS)
      phone.addToGraph(g, isTopConcept=False)

      onlineContactPoint.hasTelephone.append(phone)

      if faxNumber != "":
        fax = Telephone(
            id="fax/" + faxNumber,
            baseUri=MUN_DATA,
            dataset=MUNICIPALITY_DATA,
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
          baseUri=MUN_DATA,
          dataset=MUNICIPALITY_DATA,
          titles=[
            Literal("Referent for " + denominazione, lang="en"),
            Literal("Responsabile per " + denominazione, lang="it")
          ]
      )

      referent = Person(
        id="person/" +  genNameForID(nameRef + " " + surnameRef),
        baseUri=MUN_DATA
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
  uoName = eInvoiceServiceInfo["Descrizione_uo"]
  taxCodeEIS = eInvoiceServiceInfo["Codice_fiscale_sfe"]

  taxCodeValidationDate = eInvoiceServiceInfo["Data_verifica_cf"]
  startingDate = eInvoiceServiceInfo["Data_avvio_sfe"]

  eInvService = eInvoiceService(
      id="service/" + uoCode,
      baseUri=MUN_DATA,
      dataset=MUNICIPALITY_DATA,
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
    baseUri=MUN_DATA
  )

  office.hasEInvoiceService = eInvService

  eInvService.addToGraph(g, isTopConcept=False)

  office.addToGraph(g, onlyProperties=True)

# %%
# Save graph

saveGraph(g, "supportUnits")