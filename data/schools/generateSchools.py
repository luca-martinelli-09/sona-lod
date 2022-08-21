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

# %%
# Load data

schoolsDF = getOpenData(config.get("SCHOOLS", "public_schools"))

schoolsDF = schoolsDF.loc[schoolsDF["CODICECOMUNESCUOLA"] == cadastralCode]

schoolsDF
# %%
# Save graph

saveGraph(g, "schools")