# Imports
import configparser
from urllib.request import urlopen

import pandas as pd
import requests
import unidecode
from ontoim_py import createGraph as cg

from rapidfuzz import process, fuzz

# Namespaces constants
from .ns import *

# Get configurations from file


def getConfig(fileName):
    config = configparser.ConfigParser()
    config.read(fileName)

    return config

# Get data from CKAN OpenData portal or offline files


def getOpenData(resID, baseURL=None, whereSQL="", rawData=False, dtype=None, strip=True):
    config = getConfig('../../conf.ini')

    offline = False if baseURL else config.getboolean(
        "API", "use_offline")
    baseURL = baseURL if baseURL else config.get("API", "base_url")

    dataURI = "{}/api/3/action/datastore_search_sql?sql=SELECT * FROM \"{}\" {}".format(
        baseURL, resID, whereSQL) if not offline else "../../off_data/{}".format(resID)
    
    if resID.startswith("http"):
        offline = False
        dataURI = resID

    if rawData:
        if offline:
            return dataURI

        getDataRequest = urlopen(dataURI)

        return getDataRequest

    df = None

    if offline:
        df = pd.read_csv(dataURI, dtype=dtype)
    else:
        if resID.endswith("csv"):
            df = pd.read_csv(dataURI, dtype=dtype)
        else:
            tries = 0
            res = {"success": False}
            while not res["success"] and tries < 20:
                res = requests.get(dataURI).json()
                if res["success"]:
                    df = pd.DataFrame(res["result"]["records"], dtype=dtype)
                    break
                tries += 1

    if strip and not df is None:
        df = df.applymap(lambda x: x.strip() if type(x) == str else x)

    return df

# Standardize name
# Convert name to lower case and capitalize each word


def standardizeName(name):
    name = name.lower().title()

    if name.endswith("a'"):
        name = name.removesuffix("a'") + "à"

    return name.strip()

# Generate ID by name
# Convert in lowercase and replace special characters with dash


def genNameForID(name):
    nameID = ""

    name.replace("'", "")
    name = unidecode.unidecode(name.lower())

    # Replace special chars with -
    for char in name:
        nameID += char if char.isalnum() else "-"

    return nameID


def queryStreetCode(q):
    config = getConfig('../../conf.ini')

    streetsDF = getOpenData(config.get("ANNCSU", "streets")
                            ).set_index(["PROGR_NAZIONALE"])
    civicsDF = getOpenData(config.get("ANNCSU", "civics")
                           ).set_index(["PROGR_CIVICO"])

    streetsForSearchIDs = [(c["PROGR_NAZIONALE"], progrCivico)
                           for progrCivico, c in civicsDF.iterrows()]
    streetsForSearch = ["{} {} {}{} {}".format(
        streetsDF.loc[c["PROGR_NAZIONALE"]]["DUG"],
        streetsDF.loc[c["PROGR_NAZIONALE"]]["DENOM_COMPLETA"],
        c["CIVICO"],
        "" if pd.isna(c["ESPONENTE"]) else c["ESPONENTE"],
        streetsDF.loc[c["PROGR_NAZIONALE"]]["LOCALITA'"],
    ).lower()
        for _, c in civicsDF.iterrows()]

    streetsForSearchIDs.extend([
        (progrNazionale, None) for progrNazionale, _ in streetsDF.iterrows()
    ])
    streetsForSearch.extend(["{} {} {}".format(
        s["DUG"], s["DENOM_COMPLETA"], s["LOCALITA'"]
    ).lower() for _, s in streetsDF.iterrows()])

    searchResults = process.extract(
        q.lower(), streetsForSearch, scorer=fuzz.WRatio, limit=10)

    print(f"\n\n[🔍 RESULTS FOR] {q}")
    for res, val, i in searchResults:
        print(f"{i}) {res} ({val})")

    selectedResult = input("Choose one or type custom search: ")

    if selectedResult.isnumeric():
        return streetsForSearchIDs[int(selectedResult)]
    else:
        return queryStreetCode(selectedResult)

# Generate graph with default namespaces


def createGraph():
    # Create the graph
    g = cg()

    # Data
    g.bind("anncsu", ANNCSU)
    g.bind("accommodation", ACCO_DATA)
    g.bind("organization", COV_DATA)
    g.bind("municipality", MUNICIPALITY_DATA)
    g.bind("social", SOCIAL_DATA)
    g.bind("role", ROLE_DATA)
    g.bind("heritage", HERITAGE_DATA)
    g.bind("school", SCHOOL_DATA)

    return g
