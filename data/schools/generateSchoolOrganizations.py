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
from ontopia_py.cpv import *
from ontopia_py.cov import *

# %%
# Get Data from indicepa.gov.it

config = getConfig("../../conf.ini")

cadastralCode = config.get("MUNICIPALITY", "cadastral_code")

# Create graph
g: Graph = createGraph()

# Create a ConceptScheme
SCHOOL_DATASET = ConceptScheme(SCHOOL_DATA)

# %%
# Load data

organizationDF = getOpenData("d09adf99-dc10-4349-8c53-27b1e5aa97b6",
                             baseURL="https://indicepa.gov.it/ipa-dati",
                             whereSQL=f"WHERE \"Codice_catastale_comune\" = '{cadastralCode}' AND \"Codice_MIUR\" != ''")

# %%
# Insert organization

for _, publicOrganization in organizationDF.iterrows():
    denominazione = standardizeName(publicOrganization["Denominazione_ente"])
    acronym = publicOrganization["Acronimo"]

    taxCode = publicOrganization["Codice_fiscale_ente"]
    miurCode = publicOrganization["Codice_MIUR"]
    ipaCode = publicOrganization["Codice_IPA"]

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

    nameResp = standardizeName(publicOrganization["Nome_responsabile"])
    surnameResp = standardizeName(publicOrganization["Cognome_responsabile"])

    address = publicOrganization["Indirizzo"]
    progrNazionale, progrCivico = queryStreetCode(
        address) if address != "" else (None, None)

    # Create organization

    institute = PublicOrganization(
        id="organization/" + miurCode,
        baseUri=SCHOOL_DATA,
        dataset=SCHOOL_DATASET,
        titles=[Literal(denominazione, datatype=XSD.string)]
    )

    institute.legalName = [Literal(denominazione, datatype=XSD.string)]

    if acronym != "":
      institute.orgAcronym = Literal(acronym, datatype=XSD.string)

    # Identifiers
    institute.taxCode = Literal(taxCode, datatype=XSD.string)
    institute.IPAcode = Literal(ipaCode, datatype=XSD.string)

    # Address
    if progrNazionale:
      address = Address(
          id="{}-{}".format(progrNazionale,
                            progrCivico if progrCivico else "snc"),
          baseUri=ANNCSU
      )

      institute.hasPrimaryAddress = address

    # Contact Point
    onlineContactPoint = OnlineContactPoint(
        id="ocp/" + taxCode,
        baseUri=SCHOOL_DATA,
        dataset=SCHOOL_DATASET,
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
            baseUri=SCHOOL_DATA,
            dataset=SCHOOL_DATASET,
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

    if websiteUrl != "":
      website = WebSite(
          id="website/" + taxCode,
          baseUri=SCHOOL_DATA,
          dataset=SCHOOL_DATASET,
          titles=[Literal(websiteUrl, datatype=XSD.string)]
      )
      website.URL = Literal(websiteUrl, datatype=XSD.anyURI)
      website.addToGraph(g, isTopConcept=False)

      onlineContactPoint.hasWebSite = [website]

    if twitterUrl != "":
      twitterAccount = UserAccount(
          id="social/twitter/" + taxCode,
          baseUri=SCHOOL_DATA,
          dataset=SCHOOL_DATASET,
          titles=[Literal(twitterUrl, datatype=XSD.string)]
      )
      twitterAccount.isAccountIssuedBy = SocialMedia(
          id="twitter", baseUri=SOCIAL_DATA)
      twitterAccount.URL = Literal(twitterUrl, datatype=XSD.anyURI)
      twitterAccount.addToGraph(g, isTopConcept=False)

      onlineContactPoint.hasUserAccount.append(twitterAccount)

    if linkedinUrl != "":
      linkedinAccount = UserAccount(
          id="social/linkedin/" + taxCode,
          baseUri=SCHOOL_DATA,
          dataset=SCHOOL_DATASET,
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
          baseUri=SCHOOL_DATA,
          dataset=SCHOOL_DATASET,
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
          baseUri=SCHOOL_DATA,
          dataset=SCHOOL_DATASET,
          titles=[Literal(youtubeUrl, datatype=XSD.string)]
      )
      youtubeAccount.isAccountIssuedBy = SocialMedia(
          id="youtube", baseUri=SOCIAL_DATA)
      youtubeAccount.URL = Literal(youtubeUrl, datatype=XSD.anyURI)
      youtubeAccount.addToGraph(g, isTopConcept=False)

      onlineContactPoint.hasUserAccount.append(youtubeAccount)

    onlineContactPoint.addToGraph(g, isTopConcept=False)

    institute.hasOnlineContactPoint = onlineContactPoint

    if nameResp != "":
      headTeacherID = genNameForID(nameResp + " " + surnameResp)

      headTeacher = Person(
          id="person/" + headTeacherID,
          baseUri=SCHOOL_DATA,
          dataset=SCHOOL_DATASET,
          titles=[Literal(nameResp + " " + surnameResp, datatype=XSD.string)]
      )

      headTeacher.givenName = Literal(nameResp, datatype=XSD.string)
      headTeacher.familyName = Literal(surnameResp, datatype=XSD.string)

      headTeacher.addToGraph(g, isTopConcept=False)

      headTeacherRole = Employment(
          id="head-teacher/" + headTeacherID,
          baseUri=SCHOOL_DATA,
          dataset=SCHOOL_DATASET,
          titles=[
              Literal("Head teacher for " + denominazione, lang="en"),
              Literal("Dirigente scolastico di " + denominazione, lang="it"),
          ]
      )

      headTeacherRole.addToGraph(g, isTopConcept=False)

      headTeacherRole.employmentFor = institute
      headTeacherRole.withRole = [Role(id="head-teacher", baseUri=ROLE_DATA)]

      institute.holdEmployment = [headTeacherRole]

    institute.addToGraph(g, isTopConcept=True)

# %%
# Save graph

saveGraph(g, "ICOrganizations")