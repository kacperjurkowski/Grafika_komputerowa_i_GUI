''' Definicja tytułów sekcji w językach PL, EN. '''

LANG = {
    "pl" : {
        "nav.project"       : "Projekt",
        "nav.files"         : "Pliki projektu",
        "nav.editor"        : "Edytor skrzyżowania",
        "nav.lights"        : "Fazy świateł",
        "nav.simulation"    : "Symulacja",
        "nav.stats"         : "Statystyki",
        "nav.settings"      : "Ustawienia",
    },
    "en" : {
        "nav.project"       : "Project",
        "nav.files"         : "Project files",
        "nav.editor"        : "Junction editor",
        "nav.lights"        : "Light phases editor",
        "nav.simulation"    : "Traffic simulation",
        "nav.stats"         : "Statistics",
        "nav.settings"      : "Settings",
    }
}
_lang = "pl"

''' Ustawienie języka programu'''
def set_lang(code): 
    global _lang
    _lang = code

''' Translacja języka '''
def tr(key):
    return LANG[_lang].get(key, key)