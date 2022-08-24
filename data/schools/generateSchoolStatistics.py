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

# %%
# Load data

schoolsDF = getOpenData(config.get("SCHOOLS", "public_schools"))

schoolsDF = schoolsDF.loc[schoolsDF["CODICECOMUNESCUOLA"] == cadastralCode]

schoolCodes = list(schoolsDF["CODICESCUOLA"])

statisticSchoolsDF = getOpenData(
    "https://dati.istruzione.it/opendata/opendata/catalogo/elements1/ALUCORSOETASTA20202120210831.csv")

statisticSchoolsDF = statisticSchoolsDF.loc[statisticSchoolsDF["CODICESCUOLA"].isin(
    schoolCodes)]

statisticSchoolsDF

# %%
