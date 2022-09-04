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

# Set the properties
SCHOOL_DATASET.label = [
    Literal("Schools and Comprehensive Institutes", lang="en"),
    Literal("Scuole e Istituti Comprensivi", lang="it"),
]
SCHOOL_DATASET.creator = [ONTO_AUTHOR]

# And add to graph
SCHOOL_DATASET.addToGraph(g)

# School names to school codes

schoolNtoC = {
    "SCUOLA PRIMARIA": "3",
    "SCUOLA INFANZIA": "2",
    "SCUOLA INFANZIA NON STATALE": "2",
    "SCUOLA PRIMO GRADO": "4"
}

# %%
# Load data

publicSchoolsDF = getOpenData(config.get("SCHOOLS", "public_schools"))
privateSchoolsDF = getOpenData(config.get("SCHOOLS", "private_schools"))

schoolsDF = pd.concat([publicSchoolsDF, privateSchoolsDF])

schoolsDF = schoolsDF.loc[schoolsDF["CODICECOMUNESCUOLA"] == cadastralCode]

schoolCodes = list(schoolsDF["CODICESCUOLA"])

# %%
# Insert data

for _, schoolInfo in schoolsDF.iterrows():
    schoolCode = schoolInfo["CODICESCUOLA"]
    denominazione = standardizeName(schoolInfo["DENOMINAZIONESCUOLA"])

    schoolTypeName = schoolInfo["DESCRIZIONETIPOLOGIAGRADOISTRUZIONESCUOLA"]

    comprehensiveInstituteCode = schoolInfo["CODICEISTITUTORIFERIMENTO"]

    websiteUrl = schoolInfo["SITOWEBSCUOLA"].lower()
    emailAddress = schoolInfo["INDIRIZZOEMAILSCUOLA"].lower()
    pecAddress = schoolInfo["INDIRIZZOPECSCUOLA"].lower()

    isComprehensive = comprehensiveInstituteCode == schoolCode
    isPrivate = pd.isna(comprehensiveInstituteCode)

    address = schoolInfo["INDIRIZZOSCUOLA"]
    progrNazionale, progrCivico = queryStreetCode(
        address) if address != "" else (None, None)
    
    if isComprehensive:
        school = ComprehensiveInstitute(
            id=schoolCode,
            baseUri=SCHOOL_DATA,
            dataset=SCHOOL_DATASET,
            titles=[Literal(denominazione, datatype=XSD.string)]
        )
    else:
        if isPrivate:
            school = PrivateSchool(
                id=schoolCode,
                baseUri=SCHOOL_DATA,
                dataset=SCHOOL_DATASET,
                titles=[Literal(denominazione, datatype=XSD.string)]
            )
        else:
            school = PublicSchool(
                id=schoolCode,
                baseUri=SCHOOL_DATA,
                dataset=SCHOOL_DATASET,
                titles=[Literal(denominazione, datatype=XSD.string)]
            )

        schoolType = schoolNtoC[schoolTypeName]
        school.hasSchoolType = [SchoolType(id=schoolType, baseUri=SCHOOL_TYPES)]
    
    comprehensiveInstitute = ComprehensiveInstitute(
        id=comprehensiveInstituteCode,
        baseUri=SCHOOL_DATA
    )

    if not isPrivate:
        comprehensiveInstituteOrganization = PublicOrganization(
            id="organization/" + comprehensiveInstituteCode,
            baseUri=SCHOOL_DATA
        )
        school.ownedBy = [comprehensiveInstituteOrganization]
    
    # Main info
    school.POIofficialName = [Literal(denominazione, datatype=XSD.string)]
    school.schoolCode = Literal(schoolCode, datatype=XSD.string)

    # Address
    if progrNazionale:
      address = Address(
          id="{}-{}".format(progrNazionale,
                            progrCivico if progrCivico else "snc"),
          baseUri=ANNCSU
      )

      school.hasAddress = [address]

    # Online contact pont
    ocp = OnlineContactPoint(
        id="ocp/" + schoolCode,
        baseUri=SCHOOL_DATA,
        dataset=SCHOOL_DATASET,
        titles=[
            Literal("Online Contact Point for " +
                    denominazione, lang="en"),
            Literal("Contatti per " + denominazione, lang="it"),
        ]
    )

    website = None
    if websiteUrl != "non disponibile":
        website = WebSite(
            id="web/" + genNameForID(websiteUrl),
            baseUri=SCHOOL_DATA,
            dataset=SCHOOL_DATASET,
            titles=[Literal(websiteUrl, datatype=XSD.string)]
        )
        website.URL = Literal(websiteUrl, datatype=XSD.anyURI)
        website.addToGraph(g, isTopConcept=False)

        ocp.hasWebSite = [website]

    email = None
    if emailAddress != "non disponibile":
        email = Email(
            id="email/" + genNameForID(emailAddress),
            baseUri=SCHOOL_DATA,
            dataset=SCHOOL_DATASET,
            titles=[Literal(emailAddress, datatype=XSD.string)]
        )
        email.emailAddress = Literal(
            "mailto:" + emailAddress, datatype=XSD.anyURI)
        email.hasEmailType = EmailType(id="042", baseUri=EROGATION_CHANNELS)
        email.addToGraph(g, isTopConcept=False)

        ocp.hasEmail = [email]

    pec = None
    if pecAddress != "non disponibile":
        pec = Email(
            id="pec/" + genNameForID(pecAddress),
            baseUri=SCHOOL_DATA,
            dataset=SCHOOL_DATASET,
            titles=[Literal(pecAddress, datatype=XSD.string)]
        )
        pec.emailAddress = Literal(
            "mailto:" + pecAddress, datatype=XSD.anyURI)
        pec.hasEmailType = EmailType(id="041", baseUri=EROGATION_CHANNELS)
        pec.addToGraph(g, isTopConcept=False)

        ocp.hasCertifiedEmail = [pec]
    
    if website or email or pec:
        ocp.addToGraph(g, isTopConcept=False)
        
        school.hasOnlineContactPoint = ocp
    
    if not isComprehensive and not isPrivate:
        comprehensiveInstitute.includesSchool = [school]
        comprehensiveInstitute.addToGraph(g, onlyProperties=True)
    
    school.addToGraph(g, isTopConcept=True)

# %%
# Save graph

saveGraph(g, "schools")
# %%
