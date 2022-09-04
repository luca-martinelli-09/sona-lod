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

SCHOOL_DATASET = ConceptScheme(SCHOOL_DATA)

# %%
# Get schools present in municipality

publicSchoolsDF = getOpenData(config.get("SCHOOLS", "public_schools"))
privateSchoolsDF = getOpenData(config.get("SCHOOLS", "private_schools"))

schoolsDF = pd.concat([publicSchoolsDF, privateSchoolsDF])

schoolsDF = schoolsDF.loc[schoolsDF["CODICECOMUNESCUOLA"] == cadastralCode]
schoolCodes = list(schoolsDF["CODICESCUOLA"])

schoolsDF.set_index(["CODICESCUOLA"], inplace=True)

schoolNtoC = {
    "SCUOLA PRIMARIA": "3",
    "SCUOLA INFANZIA": "2",
    "SCUOLA INFANZIA NON STATALE": "2",
    "SCUOLA PRIMO GRADO": "4",
    "SCUOLA SECONDARIA I GRADO": "4"
}

# %%
# Load data

statisticalUrls = config.get("SCHOOLS", "statistic_data").split(" ")

statisticSchoolsDF = pd.DataFrame()
for statUri in statisticalUrls:
    statisticDF = getOpenData(statUri)

    statisticSchoolsDF = pd.concat(
        [statisticSchoolsDF, statisticDF], ignore_index=True)

statisticSchoolsDF = statisticSchoolsDF.loc[
    statisticSchoolsDF["CODICESCUOLA"].isin(schoolCodes)
]
statisticSchoolsDF.reset_index(inplace=True)

statisticSchoolsDF["ANNOCORSO"] = statisticSchoolsDF["ANNOCORSO"].astype(
    "Int64")
statisticSchoolsDF["ANNOCORSOCLASSE"] = statisticSchoolsDF["ANNOCORSOCLASSE"].astype(
    "Int64")
statisticSchoolsDF["ALUNNI"] = statisticSchoolsDF["ALUNNI"].astype(
    "Int64")
statisticSchoolsDF["ALUNNIMASCHI"] = statisticSchoolsDF["ALUNNIMASCHI"].astype(
    "Int64")
statisticSchoolsDF["ALUNNIFEMMINE"] = statisticSchoolsDF["ALUNNIFEMMINE"].astype(
    "Int64")

statisticSchoolsDF

# %%
# Insert data

# Stats for courses and ages
for i, statsInfo in statisticSchoolsDF.iterrows():
    schoolCode = statsInfo["CODICESCUOLA"]
    schoolType = statsInfo["ORDINESCUOLA"]

    isAgeStats = not pd.isna(statsInfo["ALUNNI"])

    academicYear = int(str(statsInfo["ANNOSCOLASTICO"])[:4])

    ageStudents = statsInfo["FASCIAETA"]

    courseYear = statsInfo["ANNOCORSO"] if isAgeStats else statsInfo["ANNOCORSOCLASSE"]

    courseCode = schoolNtoC[schoolType]

    school = School(
        id=schoolCode,
        baseUri=SCHOOL_DATA
    )

    schoolInfo = schoolsDF.loc[schoolCode]
    
    # COURSE
    courseName = "Classe {} - {}, {}".format(
        courseCode,
        standardizeName(schoolType),
        standardizeName(schoolInfo["DENOMINAZIONESCUOLA"])
    )

    course = Course(
        id="course/{}-{}-{}".format(schoolCode, courseCode, courseYear),
        baseUri=SCHOOL_DATA,
        dataset=SCHOOL_DATASET,
        titles=[Literal(courseName, datatype=XSD.string)]
    )

    course.hasSubscribers = []

    school.providesCourse = [course]

    school.addToGraph(g, onlyProperties=True)

    # TEMPORAL ENTITY

    temporalEntity = TimeInterval(
        id="ti/{}-{}".format(academicYear, academicYear + 1),
        baseUri=SCHOOL_DATA,
        dataset=SCHOOL_DATASET,
        titles=[Literal("{}/{}".format(academicYear, academicYear + 1), datatype=XSD.string)]
    )

    temporalEntity.startTime = Literal(str(academicYear) + "-09-01", datatype=XSD.date)
    temporalEntity.endTime = Literal(str(academicYear + 1) + "-07-01", datatype=XSD.date)

    temporalEntity.addToGraph(g, isTopConcept=False)

    # DATA STATISTICS

    if isAgeStats:
        # BY AGE

        ageStudents = ageStudents.replace(" anni", "")

        if ageStudents.startswith(">"):
            ageStudents = ageStudents.replace("> di ", "")
            ageStudents = int(ageStudents) + 1

        elif ageStudents.startswith("<"):
            ageStudents = ageStudents.replace("< di ", "")
            ageStudents = int(ageStudents) - 1
        
        ageStudents = int(ageStudents)

        subscribers = Subscribers(
            id="statistics/" + str(i),
            baseUri=SCHOOL_DATA,
            dataset=SCHOOL_DATASET,
            titles=[
                Literal("Alunni di {} anni - {} - A.A. {}/{}".format(
                    ageStudents,
                    courseName,
                    academicYear,
                    academicYear + 1
                ), datatype=XSD.string)
            ]
        )

        demReference = AlivePerson(
            id="demographic-reference/age-" + str(ageStudents),
            baseUri=SCHOOL_DATA,
            dataset=SCHOOL_DATASET,
            titles=[
                Literal("{} year old person".format(ageStudents), lang="en"),
                Literal("Persona di {} anni".format(ageStudents), lang="it")
            ]
        )
        demReference.age = Literal(ageStudents, datatype=XSD.integer)
        demReference.addToGraph(g, isTopConcept=False)

        subscribers.hasDemographicReference = demReference
        subscribers.hasTemporalEntity = temporalEntity

        subscribers.observationValue = Literal(statsInfo["ALUNNI"], datatype=XSD.positiveInteger)
        
        subscribers.addToGraph(g, isTopConcept=False)

        course.hasSubscribers.append(subscribers)
    else:
        # BY SEX
        
        for sexCode in ["M", "F"]:
            subscribers = Subscribers(
                id="statistics/" + str(i) + sexCode,
                baseUri=SCHOOL_DATA,
                dataset=SCHOOL_DATASET,
                titles=[
                    Literal("{} - {} - A.A. {}/{}".format(
                        "Alunni (maschi)" if sexCode == "M" else "Alunne (femmine)",
                        courseName,
                        academicYear,
                        academicYear + 1
                    ), datatype=XSD.string)
                ]
            )

            demReference = AlivePerson(
                id="demographic-reference/" + sexCode,
                baseUri=SCHOOL_DATA,
                dataset=SCHOOL_DATASET,
                titles=[
                    Literal("Male" if sexCode == "M" else "Female", lang="en"),
                    Literal("Maschio" if sexCode == "M" else "Femmina", lang="it")
                ]
            )
            demReference.hasSex = Sex(id=sexCode, baseUri=PERSON_SEX)
            demReference.addToGraph(g, isTopConcept=False)

            subscribers.hasDemographicReference = demReference
            subscribers.hasTemporalEntity = temporalEntity

            subscribers.observationValue = Literal(
                statsInfo["ALUNNI" + ("MASCHI" if sexCode == "M" else "FEMMINE")], datatype=XSD.positiveInteger)

            subscribers.addToGraph(g, isTopConcept=False)

            course.hasSubscribers.append(subscribers)
    
    course.addToGraph(g, isTopConcept=False)

# %%

# Stats for entire school
sumDataDF = statisticSchoolsDF.groupby(
    by=["CODICESCUOLA", "ANNOSCOLASTICO"], dropna=False).sum()

for (schoolCode, academicYear), statsInfo in sumDataDF.iterrows():
    academicYear = int(str(academicYear)[:4])

    school = School(
        id=schoolCode,
        baseUri=SCHOOL_DATA
    )

    schoolInfo = schoolsDF.loc[schoolCode]

    # TEMPORAL ENTITY

    temporalEntity = TimeInterval(
        id="ti/{}-{}".format(academicYear, academicYear + 1),
        baseUri=SCHOOL_DATA,
        dataset=SCHOOL_DATASET,
        titles=[Literal("{}/{}".format(academicYear,
                        academicYear + 1), datatype=XSD.string)]
    )

    temporalEntity.startTime = Literal(
        str(academicYear) + "-09-01", datatype=XSD.date)
    temporalEntity.endTime = Literal(
        str(academicYear + 1) + "-07-01", datatype=XSD.date)

    temporalEntity.addToGraph(g, isTopConcept=False)

    # DATA STATISTICS

    for sexCode in ["M", "F"]:
        subscribers = Subscribers(
            id="statistics/{}-{}-{}".format(schoolCode, sexCode, academicYear),
            baseUri=SCHOOL_DATA,
            dataset=SCHOOL_DATASET,
            titles=[
                Literal("{} - {} - A.A. {}/{}".format(
                    "Alunni (maschi)" if sexCode == "M" else "Alunne (femmine)",
                    standardizeName(schoolInfo["DENOMINAZIONESCUOLA"]),
                    academicYear,
                    academicYear + 1
                ), datatype=XSD.string)
            ]
        )

        demReference = AlivePerson(
            id="demographic-reference/" + sexCode,
            baseUri=SCHOOL_DATA,
            dataset=SCHOOL_DATASET,
            titles=[
                Literal("Male" if sexCode == "M" else "Female", lang="en"),
                Literal("Maschio" if sexCode ==
                        "M" else "Femmina", lang="it")
            ]
        )
        demReference.hasSex = Sex(id=sexCode, baseUri=PERSON_SEX)
        demReference.addToGraph(g, isTopConcept=False)

        subscribers.hasDemographicReference = demReference
        subscribers.hasTemporalEntity = temporalEntity

        subscribers.observationValue = Literal(
            statsInfo["ALUNNI" + ("MASCHI" if sexCode == "M" else "FEMMINE")], datatype=XSD.positiveInteger)

        subscribers.addToGraph(g, isTopConcept=False)

        school.hasSubscribers = [subscribers]
        school.addToGraph(g, onlyProperties=True)
# %%
# Save graph

saveGraph(g, "schoolsStatistics")

# %%
