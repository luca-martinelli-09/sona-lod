# %%
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parents[1]))

from utils import *

from rdflib import Graph, Literal, XSD

from ontoim_py.ontoim import *
from ontoim_py.ns import *

from ontopia_py import ConceptScheme, saveGraph

from ontopia_py.sm import *
from ontopia_py.ro import *
from ontopia_py.ti import *
from ontopia_py.clv import *
from ontopia_py.cov import LegalStatus

# %%
# Get Data from indicepa.gov.it

config = getConfig("../../conf.ini")

ipaCode = config.get("MUNICIPALITY", "ipa_code")

# Create graph
g: Graph = createGraph()

# Create a ConceptScheme
MUNICIPALITY_DATA = ConceptScheme(MUN_DATA)

# Set the properties
MUNICIPALITY_DATA.label = [
    Literal("Comune di Sona", datatype=XSD.string),
]
MUNICIPALITY_DATA.creator = [ONTO_AUTHOR]

# And add to graph
MUNICIPALITY_DATA.addToGraph(g)

# %%
# Load data

organizationDF = getDataFromCKANApi(
    "https://indicepa.gov.it/ipa-dati/api/3/action/datastore_search_sql?sql=SELECT%20*%20from%20%22d09adf99-dc10-4349-8c53-27b1e5aa97b6%22%20WHERE%20%22Codice_IPA%22%20=%20%27" + ipaCode + "%27")

# %%
# Insert organization

for _, publicOrganization in organizationDF.iterrows():
    denominazione = publicOrganization["Denominazione_ente"]
    acronym = publicOrganization["Acronimo"]

    taxCode = publicOrganization["Codice_fiscale_ente"]
    ipaCode = publicOrganization["Codice_IPA"]
    istatMunicipalityCode = publicOrganization["Codice_comune_ISTAT"]
    istatCode = publicOrganization["Codice_ISTAT"]
    cadastralCode = publicOrganization["Codice_catastale_comune"]
    postCode = publicOrganization["CAP"]

    legalStatus = publicOrganization["Codice_natura"]
    codAteco = publicOrganization["Codice_ateco"]

    websiteUrl = publicOrganization["Sito_istituzionale"]
    twitterUrl = publicOrganization["Url_twitter"]
    youtubeUrl = publicOrganization["Url_youtube"]
    facebookUrl = publicOrganization["Url_facebook"]
    linkedinUrl = publicOrganization["Url_linkedin"]
    mails = [
        {"mail": publicOrganization["Mail1"],
         "type": publicOrganization["Tipo_Mail1"]},
        {"mail": publicOrganization["Mail2"],
         "type": publicOrganization["Tipo_Mail2"]},
        {"mail": publicOrganization["Mail3"],
         "type": publicOrganization["Tipo_Mail3"]},
        {"mail": publicOrganization["Mail4"],
         "type": publicOrganization["Tipo_Mail4"]},
        {"mail": publicOrganization["Mail5"],
         "type": publicOrganization["Tipo_Mail5"]},
    ]

    nameResp = publicOrganization["Nome_responsabile"]
    surnameResp = publicOrganization["Cognome_responsabile"]
    titleResp = publicOrganization["Titolo_responsabile"]

    # Create organization

    municipality = PublicOrganization(
        id=taxCode,
        baseUri=MUN_DATA,
        dataset=MUNICIPALITY_DATA,
        titles=[Literal(denominazione, datatype=XSD.string)]
    )

    municipality.legalName = [Literal(denominazione, datatype=XSD.string)]

    if acronym != "":
      municipality.orgAcronym = Literal(acronym, datatype=XSD.string)

    # Identifiers
    municipality.taxCode = Literal(taxCode, datatype=XSD.string)
    municipality.IPAcode = Literal(ipaCode, datatype=XSD.string)

    # Codice comune ISTAT
    municipalityIdentifier = Identifier(
        id="id/" + istatMunicipalityCode,
        baseUri=MUN_DATA,
        dataset=MUNICIPALITY_DATA
    )
    municipalityIdentifier.identifier = Literal(
        istatMunicipalityCode, datatype=XSD.string)
    municipalityIdentifier.identifierType = Literal(
        "Codice comune ISTAT", datatype=XSD.string)
    municipalityIdentifier.addToGraph(g, isTopConcept=False)

    # Codice ISTAT
    istatIdentifier = Identifier(
        id="id/" + istatCode,
        baseUri=MUN_DATA,
        dataset=MUNICIPALITY_DATA
    )
    istatIdentifier.identifier = Literal(
        istatCode, datatype=XSD.string)
    istatIdentifier.identifierType = Literal(
        "Codice ISTAT", datatype=XSD.string)
    istatIdentifier.addToGraph(g, isTopConcept=False)

    # Codice catastale
    cadastralIdentifier = Identifier(
        id="id/" + cadastralCode,
        baseUri=MUN_DATA,
        dataset=MUNICIPALITY_DATA
    )
    cadastralIdentifier.identifier = Literal(
        cadastralCode, datatype=XSD.string)
    cadastralIdentifier.identifierType = Literal(
        "Codice catastale", datatype=XSD.string)
    cadastralIdentifier.addToGraph(g, isTopConcept=False)

    municipality.hasAlternativeIdentifier = [municipalityIdentifier,
                                             istatIdentifier,
                                             cadastralIdentifier]

    # Statuses

    municipality.hasLegalStatus = LegalStatus(
        id=legalStatus,
        baseUri=ORG_LEGAL_STATUS
    )

    # Contact Point
    onlineContactPoint = OnlineContactPoint(
      id="ocp/" + taxCode,
      baseUri=MUN_DATA,
      dataset=MUNICIPALITY_DATA,
      titles=[
          Literal("Online Contact Point for " + denominazione, lang="en"),
          Literal("Contatti per " + denominazione, lang="en")
      ]
    )

    onlineContactPoint.hasEmail = []
    onlineContactPoint.hasCertifiedEmail = []
    onlineContactPoint.hasUserAccount = []

    for mailInfo in mails:
      if mailInfo["mail"] != "":
        email = Email(
            id="email/" + genNameForID(mailInfo["mail"]),
            baseUri=MUN_DATA,
            dataset=MUNICIPALITY_DATA,
            titles=[Literal(mailInfo["mail"], datatype=XSD.string)]
        )

        email.emailAddress = Literal("mailto:" + mailInfo["mail"], datatype=XSD.anyURI)

        if mailInfo["type"].lower() == "pec":
          email.hasEmailType = EmailType(id="041", baseUri=EROGATION_CHANNELS)
          onlineContactPoint.hasCertifiedEmail.append(email)
        else:
          email.hasEmailType = EmailType(id="042", baseUri=EROGATION_CHANNELS)
          onlineContactPoint.hasEmail.append(email)
        
        email.addToGraph(g, isTopConcept=False)
    
    if websiteUrl != "":
      website = WebSite(
        id="website/" + taxCode,
        baseUri=MUN_DATA,
        dataset=MUNICIPALITY_DATA,
        titles=[Literal(websiteUrl, datatype=XSD.string)]
      )
      website.URL = Literal(websiteUrl, datatype=XSD.anyURI)
      website.addToGraph(g, isTopConcept=False)
      
      onlineContactPoint.hasWebSite = [website]
    
    if twitterUrl != "":
      twitterAccount = UserAccount(
        id="social/twitter/" + taxCode,
        baseUri=MUN_DATA,
        dataset=MUNICIPALITY_DATA,
        titles=[Literal(twitterUrl, datatype=XSD.string)]
      )
      twitterAccount.isAccountIssuedBy = SocialMedia(id="twitter", baseUri=SOCIAL_DATA)
      twitterAccount.URL = Literal(twitterUrl, datatype=XSD.anyURI)
      twitterAccount.addToGraph(g, isTopConcept=False)

      onlineContactPoint.hasUserAccount.append(twitterAccount)
    
    if linkedinUrl != "":
      linkedinAccount = UserAccount(
          id="social/linkedin/" + taxCode,
          baseUri=MUN_DATA,
          dataset=MUNICIPALITY_DATA,
          titles=[Literal(linkedinUrl, datatype=XSD.string)]
      )
      linkedinAccount.isAccountIssuedBy = SocialMedia(
          id="linkedin", baseUri=SOCIAL_DATA)
      linkedinAccount.URL = Literal(linkedinUrl, datatype=XSD.anyURI)
      linkedinAccount.addToGraph(g, isTopConcept=False)

      onlineContactPoint.hasUserAccount.append(linkedinAccount)
    
    if facebookUrl != "":
      facebookAccount = UserAccount(
          id="social/facebook/" + taxCode,
          baseUri=MUN_DATA,
          dataset=MUNICIPALITY_DATA,
          titles=[Literal(facebookUrl, datatype=XSD.string)]
      )
      facebookAccount.isAccountIssuedBy = SocialMedia(
          id="facebook", baseUri=SOCIAL_DATA)
      facebookAccount.URL = Literal(facebookUrl, datatype=XSD.anyURI)
      facebookAccount.addToGraph(g, isTopConcept=False)

      onlineContactPoint.hasUserAccount.append(facebookAccount)
    
    if youtubeUrl != "":
      youtubeAccount = UserAccount(
          id="social/youtube/" + taxCode,
          baseUri=MUN_DATA,
          dataset=MUNICIPALITY_DATA,
          titles=[Literal(youtubeUrl, datatype=XSD.string)]
      )
      youtubeAccount.isAccountIssuedBy = SocialMedia(
          id="youtube", baseUri=SOCIAL_DATA)
      youtubeAccount.URL = Literal(youtubeUrl, datatype=XSD.anyURI)
      youtubeAccount.addToGraph(g, isTopConcept=False)

      onlineContactPoint.hasUserAccount.append(youtubeAccount)
    
    onlineContactPoint.addToGraph(g, isTopConcept=False)

    municipality.hasOnlineContactPoint = onlineContactPoint

    municipality.addToGraph(g, isTopConcept=True)

# %%
# Save graph

saveGraph(g, "municipality")