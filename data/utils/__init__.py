# Imports
import configparser
from urllib.request import urlopen

from ontoim_py import createGraph as cg

import pandas as pd
import unidecode

# Namespaces constants
from .ns import *
from ontopia_py.ns import ITALY

# Get configurations from file


def getConfig(fileName):
    config = configparser.ConfigParser()
    config.read(fileName)

    return config

# Get data from CKAN OpenData portal


def getOpenData(datasetID, resID, rawData=False, dtype=None, strip=True):
    config = getConfig('../../conf.ini')

    offline = config.getboolean("API", "use_offline")
    baseURL = config.get("API", "base_url")

    dataURI = "{}/dataset/{}/resource/{}/download".format(
        baseURL, datasetID, resID)

    if offline:
        dataURI = "../../off_data/{}/{}".format(
            datasetID, resID)

    if rawData:
        if offline:
            return dataURI

        getDataRequest = urlopen(dataURI)

        return getDataRequest

    df = pd.read_csv(dataURI, dtype=dtype)
    
    if strip:
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

# Generate graph with default namespaces


def createGraph():
    # Create the graph
    g = cg()
    g.bind("italy", ITALY)

    # Data
    g.bind("anncsu", ANNCSU)
    g.bind("accommodation", ACCO_DATA)
    g.bind("organization", COV_DATA)

    return g
