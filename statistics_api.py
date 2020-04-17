import requests

BASE_URL="https://corona.lmao.ninja/v2/"

class CovidApi:
    """A simple wrapper for the NovelCOVID API (https://github.com/NovelCOVID/API).
    """
    def __init__(self):
        self.countries = self._all_countries()
        self.name_map = self._build_name_map(self.countries)

    def _build_name_map(self, countries):
        name_map = {}
        for iso2, country in countries.items():
            name_map[country['iso2'].lower()] = iso2
            name_map[country['iso3'].lower()] = iso2
            name_map[country['name'].lower()] = iso2
        return name_map

    def _all_countries(self):
        response = requests.get(BASE_URL+"countries")
        if response.status_code == 200:
            countries = {}
            for item in response.json():
                iso2 = item['countryInfo']['iso2']
                if iso2:
                    countries[iso2] = item['countryInfo']
                    countries[iso2]['name'] = item['country']
            return countries
        else:
            return {}

    def cases_world(self):
        response = requests.get(BASE_URL+"all")
        if response.status_code == 200:
            return response.json()
        else:
            return None

    def cases_country_list(self, sort_by="cases"):
        response = requests.get(BASE_URL+"countries", params={'sort': sort_by})
        if response.status_code == 200:
            return [item for item in response.json() if item['countryInfo']['iso2']]
        else:
            return []

    def cases_country(self, country):
        country_code = self.name_map[country.lower()]
        response = requests.get(BASE_URL+"countries/{}".format(country_code))
        if response.status_code == 200:
            data = response.json()
            del data['countryInfo']
            return data
        else:
            return None
