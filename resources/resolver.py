from os.path import dirname, join, basename
import glob
import json

_directory = dirname(__file__)
_lang_dict = {}

# load all language files of form "strings.*.json"
for path in glob.glob(join(_directory, "strings.*.json")):
    lang_code = basename(path).split(".")[1]
    with open(path, 'r', encoding="utf-8") as f:
        _lang_dict[lang_code] = json.load(f)

def resolve(key, lang, *args):
    lang = lang if lang in _lang_dict else "en"
    val = _lang_dict[lang][key]
    if isinstance(val, list):
        return "\n".join(val).format(*args)
    else:
        return val.format(*args)
