# %%
from ontopia_py.sm import *
from ontopia_py import *

from rdflib import Graph, Literal

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parents[1]))

from utils import *


# %%
# Create graph
g: Graph = createGraph()

# Create a ConceptScheme
SOCIALMEDIA_DATA = ConceptScheme(SOCIAL_DATA)

# Set the properties
SOCIALMEDIA_DATA.label = [
    Literal("Social Media", datatype=XSD.string),
]
SOCIALMEDIA_DATA.creator = [ONTO_AUTHOR]

# And add to graph
SOCIALMEDIA_DATA.addToGraph(g)

#%%
socialMediasDF = pd.DataFrame([
    {"id": "twitter", "name": "Twitter"},
    {"id": "facebook", "name": "Facebook"},
    {"id": "youtube", "name": "YouTube"},
    {"id": "linkedin", "name": "Linkedin"},
    {"id": "instagram", "name": "Instagram"},
    {"id": "whatsapp", "name": "WhatsApp"},
    {"id": "telegram", "name": "Telegram"}
])
socialMediasDF.set_index("id", inplace=True)
# %%
# Insert social medias

for socialID, social in socialMediasDF.iterrows():
    socialMedia = SocialMedia(
      id=socialID,
      baseUri=SOCIAL_DATA,
      dataset=SOCIALMEDIA_DATA,
      titles=[Literal(social["name"], datatype=XSD.string)]
    )

    socialMedia.socialMediaName = Literal(social["name"], datatype=XSD.string)

    socialMedia.addToGraph(g, isTopConcept=True)

# %%
# Save graph

saveGraph(g, "socialMedia")