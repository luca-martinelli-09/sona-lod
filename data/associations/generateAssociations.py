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
from ontopia_py.ti import *
from ontopia_py.mu import *
from ontopia_py.cov import *
from ontopia_py.clv import *
from ontopia_py.cpv import *
from ontopia_py.ro import *

# %%
# Get Data from indicepa.gov.it

config = getConfig("../../conf.ini")

# Create graph
g: Graph = createGraph()

# Create a ConceptScheme
ASSOCIATIONS_DATASET = ConceptScheme(ASSOCIATIONS_DATA)

# Set the properties
ASSOCIATIONS_DATASET.label = [
    Literal("Associations", lang="en"),
    Literal("Albo delle associazioni", lang="it"),
]
ASSOCIATIONS_DATASET.creator = [ONTO_AUTHOR]

# And add to graph
ASSOCIATIONS_DATASET.addToGraph(g)

# %%
# Load data

associationsDF = getOpenData(config.get("ASSOCIATIONS", "associations"), dtype={
                             "COD_TIPOLOGIA": str, "CODICE_FISCALE": str, "IVA": str, "TELEFONO": str})

# %%
# Insert data

insertedAssociations = Graph()
insertedAssociations.parse("./associations.rdf");

for _, associationInfo in associationsDF.iterrows():
    denominazione = associationInfo["DENOMINAZIONE"]

    removeFromRegisterDate = associationInfo["RIMOZIONE_ALBO"]

    address = associationInfo["SEDE"]

    associationCategoryCode = associationInfo["COD_TIPOLOGIA"]

    taxCode = associationInfo["CODICE_FISCALE"]
    vatCode = associationInfo["IVA"]

    nameRef = associationInfo["NOME_REFERENTE"]
    surnameRef = associationInfo["COGNOME_REFERENTE"]

    phoneNumber = associationInfo["TELEFONO"]
    mailAddress = associationInfo["EMAIL"]
    pecAddress = associationInfo["PEC"]
    websiteUrl = associationInfo["SITO"]
    youtubeUrl = associationInfo["YOUTUBE"]
    telegramUrl = associationInfo["TELEGRAM"]
    twitterUrl = associationInfo["TWITTER"]
    instagramUrl = associationInfo["INSTAGRAM"]
    facebookUrl = associationInfo["FACEBOOK"]

    associationID = genNameForID(denominazione)
    if not pd.isna(vatCode):
      associationID = vatCode
    if not pd.isna(taxCode):
      associationID = taxCode
    
    # ASSOCIATION

    association = Association(
      id=associationID,
      baseUri=ASSOCIATIONS_DATA,
      dataset=ASSOCIATIONS_DATASET,
      titles=[Literal(denominazione, datatype=XSD.string)]
    )
    association.legalName = [Literal(denominazione, datatype=XSD.string)]

    association.hasAssociationCategory = [AssociationCategory(
      id=associationCategoryCode,
      baseUri=ASSOCIATION_CATEGORIES
    )]

    # IDENTIFIERS

    if not pd.isna(taxCode):
      association.taxCode = Literal(taxCode, datatype=XSD.string)

    if not pd.isna(vatCode):
      association.VATnumber = Literal(vatCode, datatype=XSD.string)

    # ADDRESS

    alreadyInsertAddress = insertedAssociations.value(
        association.uriRef, CLV["hasPrimaryAddress"])
    
    if alreadyInsertAddress:
      addressID = str(insertedAssociations.value(association,
          CLV["hasPrimaryAddress"])).removeprefix(str(ANNCSU))
      address = Address(
        id=addressID,
        baseUri=ANNCSU
      )
      address.uriRef = alreadyInsertAddress
      association.hasPrimaryAddress = address
    else:
      progrNazionale, progrCivico = queryStreetCode(
          address) if address != "" else (None, None)

      if progrNazionale:
        progrCivico = progrCivico if progrCivico else "snc"

        address = Address(
            id="ad-{}-{}".format(progrNazionale, progrCivico),
            baseUri=ANNCSU
        )

        association.hasPrimaryAddress = address
    
    # DATE

    if not pd.isna(removeFromRegisterDate):
        association.associationRemovalFromRegisterDate = Literal(removeFromRegisterDate, datatype=XSD.date)

    # PRESIDENT

    if not pd.isna(nameRef):
      president = Person(
          id="person/" + genNameForID(nameRef + " " + surnameRef),
          baseUri=ASSOCIATIONS_DATA,
          dataset=ASSOCIATIONS_DATASET,
          titles=[Literal(nameRef + " " + surnameRef, datatype=XSD.string)]
      )
      president.familyName = Literal(surnameRef, datatype=XSD.string)
      president.givenName = Literal(nameRef, datatype=XSD.string)
      president.addToGraph(g, isTopConcept=False)

      employment = Employment(
          id="president/" + associationID,
          baseUri=ASSOCIATIONS_DATA,
          dataset=ASSOCIATIONS_DATASET,
          titles=[
              Literal("President of " + denominazione, lang="en"),
              Literal("Presidente di " + denominazione, lang="it")
          ]
      )

      employment.employmentFor = association
      employment.withRole = [Role(
          id="president",
          baseUri=ROLE_DATA
      )]
      employment.isRoleInTimeOf = [president]
      employment.addToGraph(g, isTopConcept=False)

      g.add((president.uriRef, RO["holdsRoleInTime"], employment.uriRef))

      association.holdEmployment = [employment]
      association.hasReferent = [president]
    
    # CONTACT POINT

    onlineContactPoint = OnlineContactPoint(
        id="ocp/" + associationID,
        baseUri=ASSOCIATIONS_DATA,
        dataset=ASSOCIATIONS_DATASET,
        titles=[
            Literal("Online Contact Point for " + denominazione, lang="en"),
            Literal("Contatti per " + denominazione, lang="en")
        ]
    )

    onlineContactPoint.hasEmail = []
    onlineContactPoint.hasCertifiedEmail = []
    onlineContactPoint.hasTelephone = []
    onlineContactPoint.hasUserAccount = []
    onlineContactPoint.hasWebSite = []

    if not pd.isna(mailAddress):
      email = Email(
          id="email/" + genNameForID(mailAddress),
          baseUri=ASSOCIATIONS_DATA,
          dataset=ASSOCIATIONS_DATASET,
          titles=[Literal(mailAddress, datatype=XSD.string)]
      )

      email.emailAddress = Literal(
           "mailto:" + mailAddress, datatype=XSD.anyURI)
      email.hasEmailType = EmailType(id="042", baseUri=EROGATION_CHANNELS)
      onlineContactPoint.hasEmail.append(email)

      email.addToGraph(g, isTopConcept=False)
    
    if not pd.isna(pecAddress):
      pec = Email(
          id="pec/" + genNameForID(pecAddress),
          baseUri=ASSOCIATIONS_DATA,
          dataset=ASSOCIATIONS_DATASET,
          titles=[Literal(pecAddress, datatype=XSD.string)]
      )

      pec.emailAddress = Literal(
          "mailto:" + pecAddress, datatype=XSD.anyURI)
      pec.hasEmailType = EmailType(id="041", baseUri=EROGATION_CHANNELS)
      onlineContactPoint.hasCertifiedEmail.append(pec)

      pec.addToGraph(g, isTopConcept=False)

    if not pd.isna(phoneNumber):
      phone = Telephone(
          id="phone/" + phoneNumber,
          baseUri=ASSOCIATIONS_DATA,
          dataset=ASSOCIATIONS_DATASET,
          titles=[Literal(phoneNumber, datatype=XSD.string)]
      )
      phone.telephoneNumber = Literal(phoneNumber, datatype=XSD.string)
      phone.hasTelephoneType = TelephoneType(
          id="03", baseUri=EROGATION_CHANNELS)
      phone.addToGraph(g, isTopConcept=False)
    
    if not pd.isna(websiteUrl):
      website = WebSite(
          id="website/" + genNameForID(websiteUrl),
          baseUri=ASSOCIATIONS_DATA,
          dataset=ASSOCIATIONS_DATASET,
          titles=[Literal(websiteUrl, datatype=XSD.string)]
      )
      website.URL = Literal(websiteUrl, datatype=XSD.anyURI)
      website.addToGraph(g, isTopConcept=False)

      onlineContactPoint.hasWebSite.append(website)
  
    if not pd.isna(youtubeUrl):
      youtubeAccount = UserAccount(
        id="youtube/" + genNameForID(youtubeUrl),
        baseUri=ASSOCIATIONS_DATA,
        dataset=ASSOCIATIONS_DATASET,
        titles=[Literal(youtubeUrl, datatype=XSD.string)]
      )
      youtubeAccount.userAccountName = Literal(youtubeUrl, datatype=XSD.string)
      youtubeAccount.isAccountIssuedBy = SocialMedia(id="youtube", baseUri=SOCIAL_DATA)
      youtubeAccount.URL = Literal(
          "https://www.youtube.com/c/" + youtubeUrl, datatype=XSD.anyURI)
      youtubeAccount.addToGraph(g, isTopConcept=False)

      onlineContactPoint.hasUserAccount.append(youtubeAccount)

    if not pd.isna(telegramUrl):
      telegramAccount = UserAccount(
        id="telegram/" + genNameForID(telegramUrl),
        baseUri=ASSOCIATIONS_DATA,
        dataset=ASSOCIATIONS_DATASET,
        titles=[Literal(telegramUrl, datatype=XSD.string)]
      )
      telegramAccount.userAccountName = Literal(telegramUrl, datatype=XSD.string)
      telegramAccount.isAccountIssuedBy = SocialMedia(id="telegram", baseUri=SOCIAL_DATA)
      telegramAccount.URL = Literal("https://t.me/" + telegramUrl, datatype=XSD.anyURI)
      telegramAccount.addToGraph(g, isTopConcept=False)

      onlineContactPoint.hasUserAccount.append(telegramAccount)

    if not pd.isna(twitterUrl):
      twitterAccount = UserAccount(
        id="twitter/" + genNameForID(twitterUrl),
        baseUri=ASSOCIATIONS_DATA,
        dataset=ASSOCIATIONS_DATASET,
        titles=[Literal(twitterUrl, datatype=XSD.string)]
      )
      twitterAccount.userAccountName = Literal(twitterUrl, datatype=XSD.string)
      twitterAccount.isAccountIssuedBy = SocialMedia(id="twitter", baseUri=SOCIAL_DATA)
      twitterAccount.URL = Literal("https://twitter.com/" + twitterUrl, datatype=XSD.anyURI)
      twitterAccount.addToGraph(g, isTopConcept=False)

      onlineContactPoint.hasUserAccount.append(twitterAccount)

    if not pd.isna(instagramUrl):
      instagramAccount = UserAccount(
        id="instagram/" + genNameForID(instagramUrl),
        baseUri=ASSOCIATIONS_DATA,
        dataset=ASSOCIATIONS_DATASET,
        titles=[Literal(instagramUrl, datatype=XSD.string)]
      )
      instagramAccount.userAccountName = Literal(instagramUrl, datatype=XSD.string)
      instagramAccount.isAccountIssuedBy = SocialMedia(id="instagram", baseUri=SOCIAL_DATA)
      instagramAccount.URL = Literal(
          "https://instagram.com/" + instagramUrl, datatype=XSD.anyURI)
      instagramAccount.addToGraph(g, isTopConcept=False)

      onlineContactPoint.hasUserAccount.append(instagramAccount)

    if not pd.isna(facebookUrl):
      facebookAccount = UserAccount(
        id="facebook/" + genNameForID(facebookUrl),
        baseUri=ASSOCIATIONS_DATA,
        dataset=ASSOCIATIONS_DATASET,
        titles=[Literal(facebookUrl, datatype=XSD.string)]
      )
      facebookAccount.userAccountName = Literal(facebookUrl, datatype=XSD.string)
      facebookAccount.isAccountIssuedBy = SocialMedia(id="facebook", baseUri=SOCIAL_DATA)
      facebookAccount.URL = Literal("https://facebook.com/" + facebookUrl, datatype=XSD.anyURI)
      facebookAccount.addToGraph(g, isTopConcept=False)

      onlineContactPoint.hasUserAccount.append(facebookAccount)

    if len(onlineContactPoint.hasEmail) + len(onlineContactPoint.hasCertifiedEmail) + len(onlineContactPoint.hasTelephone) + len(onlineContactPoint.hasWebSite) + len(onlineContactPoint.hasUserAccount) > 0:
      association.hasOnlineContactPoint = onlineContactPoint

      onlineContactPoint.addToGraph(g, isTopConcept=False)
    
    association.addToGraph(g, isTopConcept=True)

# %%
# Save graph

saveGraph(g, "associations")
# %%
