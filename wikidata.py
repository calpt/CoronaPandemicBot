from SPARQLWrapper import SPARQLWrapper, JSON
import requests
import logging
import sys
from datetime import datetime

logger = logging.getLogger(__name__)

# set a custom user agent to reduce the chance of getting blocked
user_agent = "coronapandemicbot Python/{}.{}".format(sys.version_info[0], sys.version_info[1])
sparql = SPARQLWrapper("https://query.wikidata.org/sparql", agent=user_agent)

WORLD_MAP="https://upload.wikimedia.org/wikipedia/commons/thumb/3/3b/COVID-19_Outbreak_World_Map_per_Capita.svg/500px-COVID-19_Outbreak_World_Map_per_Capita.svg.png"

cached = {}

# We cannot send an svg as picture in Telegram. So, for svgs, find a matching png.
def _check_path(url):
    r = requests.get(url)
    path = r.url
    if path.endswith(".svg"):
        path = path.replace("/commons/", "/commons/thumb/")
        file_name = path.split('/')[-1]
        return path+"/500px-"+file_name+".png"
    else:
        return path

# add a timestamp parameter to every image link to avoid long caching by Telegram servers
def _add_timestamp(url):
    timestamp = datetime.utcnow().strftime("%Y%m%d%H")
    return "{}?t={}".format(url, timestamp)

def cases_world_map():
    return _add_timestamp(WORLD_MAP)

def cases_country_map(country_code):
    country_code = country_code.upper()
    if country_code in cached:
        return _add_timestamp(cached[country_code])
    sparql.setQuery("""
        PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
        PREFIX p: <http://www.wikidata.org/prop/>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        PREFIX wd: <http://www.wikidata.org/entity/>
        SELECT ?img
        WHERE 
        {{
            ?page p:P31 ?prop.
            ?prop pq:P642 wd:Q84263196.
            ?page wdt:P276 ?country.
            ?country wdt:P297 ?iso2.
            ?country wdt:P298 ?iso3.
            ?page wdt:P1846 ?img.
            FILTER(?iso2 = "{0}" || ?iso3 = "{0}")
        }}""".format(country_code))
    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()['results']['bindings']
        logger.debug(results)
        if len(results) > 0:
            path = _check_path(results[0]['img']['value'])
            cached[country_code] = path
            return _add_timestamp(path)
        else:
            return None
    except Exception as ex:
        logger.info(ex)
        return None
