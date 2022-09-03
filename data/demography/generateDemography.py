# %%
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parents[1]))

from utils import *

from rdflib import Literal, XSD, SKOS

from ontoim_py.ontoim import *
from ontoim_py.ns import *

from ontopia_py import ConceptScheme, saveGraph

from ontopia_py.ro import *
from ontopia_py.ti import *
from ontopia_py.clv import *
from ontopia_py.cpv import *

import pandas as pd

# %%
# Get data

config = getConfig("../../conf.ini")

# Create graph
g = createGraph()

POPULATION_DATA = Namespace("https://w3id.org/sona/data/demography/population/")
FOREIGN_CITIZENS_DATA = Namespace("https://w3id.org/sona/data/demography/foreign-citizens/")
CIVIL_STATUS_DATA = Namespace("https://w3id.org/sona/data/demography/civil-status/")
FREQUENT_NAMES_DATA = Namespace("https://w3id.org/sona/data/demography/names/")
FREQUENT_SURNAMES_DATA = Namespace("https://w3id.org/sona/data/demography/surnames/")

# Create a ConceptScheme
# MAIN CONCEPT SCHEME
DEMOGRAPHY_DATASET = ConceptScheme(DEMOGRAPHY_DATA)
DEMOGRAPHY_DATASET.label = [
    Literal("Demographic statistics and civil status", lang="en"),
    Literal("Statistiche demografiche e stato civile", lang="it"),
]
DEMOGRAPHY_DATASET.creator = [ONTO_AUTHOR]
DEMOGRAPHY_DATASET.addToGraph(g)

# POPULATION
POPULATION_DATASET = ConceptScheme(POPULATION_DATA)
POPULATION_DATASET.label = [
    Literal("Population over the years", lang="en"),
    Literal("Numero di cittadini negli anni", lang="it"),
]
POPULATION_DATASET.creator = [ONTO_AUTHOR]
POPULATION_DATASET.addToGraph(g)

# FOREIGN CITIZENS
FOREIGN_CITIZENS_DATASET = ConceptScheme(FOREIGN_CITIZENS_DATA)
FOREIGN_CITIZENS_DATASET.label = [
    Literal("Citizenship of foreign citizens over years", lang="en"),
    Literal("Nazionalità dei cittadini stranieri negli anni", lang="it"),
]
FOREIGN_CITIZENS_DATASET.creator = [ONTO_AUTHOR]
FOREIGN_CITIZENS_DATASET.addToGraph(g)

# CIVIL STATUS
CIVIL_STATUS_DATASET = ConceptScheme(CIVIL_STATUS_DATA)
CIVIL_STATUS_DATASET.label = [
    Literal("Civil status events over years", lang="en"),
    Literal("Eventi di stato civile negli anni", lang="it"),
]
CIVIL_STATUS_DATASET.creator = [ONTO_AUTHOR]
CIVIL_STATUS_DATASET.addToGraph(g)

# NAMES
FREQUENT_NAMES_DATASET = ConceptScheme(FREQUENT_NAMES_DATA)
FREQUENT_NAMES_DATASET.label = [
    Literal("Most frequent names", lang="en"),
    Literal("Nomi più frequenti", lang="it"),
]
FREQUENT_NAMES_DATASET.creator = [ONTO_AUTHOR]
FREQUENT_NAMES_DATASET.addToGraph(g)

# SURNAMES
FREQUENT_SURNAMES_DATASET = ConceptScheme(FREQUENT_SURNAMES_DATA)
FREQUENT_SURNAMES_DATASET.label = [
    Literal("Most frequent surnames", lang="en"),
    Literal("Cognomi più frequenti", lang="it"),
]
FREQUENT_SURNAMES_DATASET.creator = [ONTO_AUTHOR]
FREQUENT_SURNAMES_DATASET.addToGraph(g)

# Add datasets to main demography dataset
g.add((DEMOGRAPHY_DATASET.uriRef, SKOS.hasTopConcept ,POPULATION_DATASET.uriRef))
g.add((DEMOGRAPHY_DATASET.uriRef, SKOS.hasTopConcept ,FOREIGN_CITIZENS_DATASET.uriRef))
g.add((DEMOGRAPHY_DATASET.uriRef, SKOS.hasTopConcept ,CIVIL_STATUS_DATASET.uriRef))
g.add((DEMOGRAPHY_DATASET.uriRef, SKOS.hasTopConcept ,FREQUENT_NAMES_DATASET.uriRef))
g.add((DEMOGRAPHY_DATASET.uriRef, SKOS.hasTopConcept ,FREQUENT_SURNAMES_DATASET.uriRef))

# %%
# Load data
namesFDF = getOpenData(config.get("DEMOGRAPHY", "names_f"), dtype={"NUMERO": "Int64"})
namesFDF["SESSO"] = "F"
namesMDF = getOpenData(config.get("DEMOGRAPHY", "names_m"), dtype={"NUMERO": "Int64"})
namesMDF["SESSO"] = "M"
surnamesFDF = getOpenData(config.get("DEMOGRAPHY", "surnames_f"), dtype={"NUMERO": "Int64"})
surnamesFDF["SESSO"] = "F"
surnamesMDF = getOpenData(config.get("DEMOGRAPHY", "surnames_m"), dtype={"NUMERO": "Int64"})
surnamesMDF["SESSO"] = "M"

namesAndSurnamesDF = pd.concat([namesFDF, namesMDF, surnamesFDF, surnamesMDF])

populationDF = getOpenData(config.get(
    "DEMOGRAPHY", "population"), dtype={"ANNO": str, "M": "Int64", "F": "Int64", "FAMIGLIE": "Int64", "STRANIERI": "Int64"})

civilStatusDF = getOpenData(config.get("DEMOGRAPHY", "civil_status"), dtype={
                            "ANNO": str, "M": "Int64", "F": "Int64", "TOTALE": "Int64"})

citizenshipForeignDF = getOpenData(
    config.get("DEMOGRAPHY", "citizenship_foreigns"), dtype={
        "ANNO": str, "M": "Int64", "F": "Int64", "TOTALE": "Int64"})
# %%
# Insert names and surnames

for _, statsInfo in namesAndSurnamesDF.iterrows():
    number = statsInfo["NUMERO"]
    name = standardizeName(statsInfo["NOME"]) if not pd.isna(statsInfo["NOME"]) else None
    surname = standardizeName(statsInfo["COGNOME"]) if not pd.isna(statsInfo["COGNOME"]) else None
    sex = statsInfo["SESSO"]

    statID = "{}-{}-{}".format(
        "surname" if surname else "name",
        genNameForID(surname) if surname else genNameForID(name),
        sex.lower()
    )

    demoReference = Person(
        id="reference/" + statID,
        baseUri=(FREQUENT_NAMES_DATA if name else FREQUENT_SURNAMES_DATA),
        dataset=(FREQUENT_NAMES_DATASET if name else FREQUENT_SURNAMES_DATASET),
        titles=[Literal("{}".format(surname if surname else name))]
    )
    demoReference.familyName = Literal(surname, datatype=XSD.string) if not pd.isna(surname) else None
    demoReference.givenName = Literal(name, datatype=XSD.string) if not pd.isna(name) else None
    demoReference.hasSex = Sex(id=sex, baseUri=PERSON_SEX)

    demoReference.addToGraph(g, isTopConcept=False)

    demoObservation = Citizens(
      id=statID,
      baseUri=(FREQUENT_NAMES_DATA if name else FREQUENT_SURNAMES_DATA),
      dataset=(FREQUENT_NAMES_DATASET if name else FREQUENT_SURNAMES_DATASET),
      titles=[
        Literal("People with {} {}".format("surname" if surname else "name", surname if surname else name), lang="en"),
        Literal("Persone con {} {}".format("cognome" if surname else "nome", surname if surname else name), lang="it")
      ]
    )

    demoObservation.observationValue = Literal(number, datatype=XSD.nonNegativeInteger)
    demoObservation.hasDemographicReference = demoReference

    demoObservation.addToGraph(g, isTopConcept=True)

# %%
# Population

for _, statsInfo in populationDF.iterrows():
  year = statsInfo["ANNO"]
  locality = statsInfo["FRAZIONE"]

  temporalEntity = Year(
    id="ti/" + year,
    baseUri=POPULATION_DATA,
    dataset=POPULATION_DATASET,
    titles=[Literal(year, datatype=XSD.string)]
  )
  temporalEntity.year = Literal(year, datatype=XSD.gYear)
  temporalEntity.addToGraph(g, isTopConcept=False)
  
  for type in ["M", "F", "FAMIGLIE", "STRANIERI"]:
    obsValue = statsInfo[type]

    if not pd.isna(obsValue) and obsValue > 0:
      if type == "M" or type == "F":
        demoReference = Person(
          id="reference/{}".format("male" if type == "M" else "female"),
          baseUri=POPULATION_DATA,
          dataset=POPULATION_DATASET,
          titles=[
            Literal("Male" if type == "M" else "Female", lang="en"),
            Literal("Maschio" if type == "M" else "Femmina", lang="it")
          ]
        )
        demoReference.hasSex = Sex(id=type, baseUri=PERSON_SEX)
      elif type == "FAMIGLIE":
        demoReference = Family(
          id="reference/family",
          baseUri=POPULATION_DATA,
          dataset=POPULATION_DATASET,
          titles=[Literal("Family", lang="en"), Literal("Family", lang="it")]
        )
      elif type == "STRANIERI":
        demoReference = ForeignCitizen(
          id="reference/foreign",
          baseUri=POPULATION_DATA,
          dataset=POPULATION_DATASET,
          titles=[Literal("Foreign citizen", lang="en"), Literal("Cittadino straniero", lang="it")]
        )
      
      demoReference.addToGraph(g, isTopConcept=False)

      demoObservation = Citizens(
        id="{}-{}-{}".format(year, genNameForID(locality), type.lower()),
        baseUri=POPULATION_DATA,
        dataset=POPULATION_DATASET,
        titles=[Literal("Numero di cittadini nel {} a {} - {}".format(year, locality, standardizeName(type)))]
      )
      demoObservation.observationValue = Literal(obsValue, datatype=XSD.nonNegativeInteger)
      demoObservation.hasSpatialCoverage = AddressArea(
        id="locality/" + genNameForID(locality),
        baseUri=ANNCSU
      )
      demoObservation.hasTemporalEntity = temporalEntity
      demoObservation.hasDemographicReference = demoReference

      demoObservation.addToGraph(g, isTopConcept=True)

# %%
# Civil Status

civilStatusToCode = {
  "nati-comune": "A.1",
  "nati-altro-comune": "A.2",
  "nati-dichiarazione-trasmessa": "A.3",
  "nati-genitore-straniero": "A.4",
  "nati-nel-matrimonio": "A.5",
  "nati-fuori-matrimonio": "A.6",
  "nati-parti-plurimi": "A.7",
  "morti-comune": "B.1",
  "morti-altro-comune": "B.2",
  "morti-estero": "B.3",
  "immigrati-altro-comune": "C.1",
  "immigrati-estero": "C.2",
  "immigrati-altro": "C.3",
  "emigrati-altro-comune": "D.1",
  "emigrati-estero": "D.2",
  "emigrati-altro": "D.3",
  "matrimoni-religiosi": "E.1",
  "matrimoni-civili": "E.2",
  "matrimoni-stranieri": "E.3",
  "accordi-extragiudiziali-separazioni": "F.1",
  "accordi-extragiudiziali-divorzi": "F.2",
  "accordi-extragiudiziali-altro": "F.3",
  "unioni-civili-maschi": "G.1",
  "unioni-civili-femmine": "G.2",
  "scioglimento-unioni-civili-maschi": "H.1",
  "scioglimento-unioni-civili-femmine": "H.2",
}

for _, statsInfo in civilStatusDF.iterrows():
  year = statsInfo["ANNO"]
  civilStatusEvent = genNameForID(statsInfo["STATO_CIVILE"] + "-" + statsInfo["TIPOLOGIA"])
  statusCode = civilStatusToCode[civilStatusEvent]

  temporalEntity = Year(
      id="ti/" + year,
      baseUri=CIVIL_STATUS_DATA,
      dataset=CIVIL_STATUS_DATASET,
      titles=[Literal(year, datatype=XSD.string)]
  )
  temporalEntity.year = Literal(year, datatype=XSD.gYear)
  temporalEntity.addToGraph(g, isTopConcept=False)

  for type in ["M", "F", "TOTALE"]:
    obsValue = statsInfo[type]

    if obsValue > 0:
      demoReference = None

      if type == "M" or type == "F":
        demoReference = Person(
            id="reference/{}".format("male" if type == "M" else "female"),
            baseUri=CIVIL_STATUS_DATA,
            dataset=CIVIL_STATUS_DATASET,
            titles=[
                Literal("Male" if type == "M" else "Female", lang="en"),
                Literal("Maschio" if type == "M" else "Femmina", lang="it")
            ]
        )
        demoReference.hasSex = Sex(id=type, baseUri=PERSON_SEX)

        demoReference.addToGraph(g, isTopConcept=False)
      
      civilStatus = CivilStatus(
          id="{}-{}-{}".format(year, genNameForID(type), genNameForID(statusCode)),
          baseUri=CIVIL_STATUS_DATA,
          dataset=CIVIL_STATUS_DATASET,
          titles=[Literal("Stato civile nel {} - {} ({}), {}".format(
            year,
            statsInfo["STATO_CIVILE"],
            statsInfo["TIPOLOGIA"],
            standardizeName(type)
          ), datatype=XSD.string)]
      )
      civilStatus.hasCivilStatusCategory = CivilStatusCategory(id=statusCode, baseUri=CIVIL_STATUS_CATEGORIES)
      civilStatus.observationValue = Literal(obsValue, datatype=XSD.nonNegativeInteger)
      civilStatus.hasDemographicReference = demoReference
      civilStatus.hasTemporalEntity = temporalEntity

      civilStatus.addToGraph(g, isTopConcept=True)

# %%
# Foreign citizens for citizenship

for _, statsInfo in citizenshipForeignDF[citizenshipForeignDF["COD_NAZIONE"].notna()].iterrows():
  year = statsInfo["ANNO"]
  codeCountry = statsInfo["COD_NAZIONE"]

  temporalEntity = Year(
      id="ti/" + year,
      baseUri=FOREIGN_CITIZENS_DATA,
      dataset=FOREIGN_CITIZENS_DATASET,
      titles=[Literal(year, datatype=XSD.string)]
  )
  temporalEntity.year = Literal(year, datatype=XSD.gYear)
  temporalEntity.addToGraph(g, isTopConcept=False)

  for type in ["M", "F"]:
    obsValue = statsInfo[type]

    if obsValue > 0:
      demoReference = Person(
          id="reference/{}-{}".format("male" if type == "M" else "female", codeCountry.lower()),
          baseUri=FOREIGN_CITIZENS_DATA,
          dataset=FOREIGN_CITIZENS_DATASET,
          titles=[
              Literal("Male" if type == "M" else "Female", lang="en"),
              Literal("Maschio" if type == "M" else "Femmina", lang="it")
          ]
      )
      demoReference.hasSex = Sex(id=type, baseUri=PERSON_SEX)
      demoReference.hasCitizenship = [Country(id=codeCountry, baseUri=COUNTRIES)]

      demoReference.addToGraph(g, isTopConcept=False)

      foreignCitizens = Citizens(
          id="{}-{}-{}".format(year, genNameForID(type),
                               genNameForID(codeCountry)),
          baseUri=FOREIGN_CITIZENS_DATA,
          dataset=FOREIGN_CITIZENS_DATASET,
          titles=[Literal("Cittadini con cittadinanza {} nel {} - {}".format(
              standardizeName(statsInfo["CITTADINANZA"]),
              year,
              standardizeName(type)
          ), datatype=XSD.string)]
      )
      foreignCitizens.observationValue = Literal(
          obsValue, datatype=XSD.nonNegativeInteger)
      foreignCitizens.hasDemographicReference = demoReference
      foreignCitizens.hasTemporalEntity = temporalEntity

      foreignCitizens.addToGraph(g, isTopConcept=True)
# %%
# Save graph

saveGraph(g, "demography")
