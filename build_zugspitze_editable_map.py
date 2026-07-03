import base64
import heapq
import html
import json
import math
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE_GPX = ROOT / "zugspitze_reintal_route_v2.gpx"
SOURCE_KML = ROOT / "zugspitze_reintal_map_v2.kml"

OUT_HTML = ROOT / "zugspitze_reintal_editable_map.html"
OUT_INDEX = ROOT / "index.html"
OUT_PRINT = ROOT / "print.html"
OUT_OFFLINE_README = ROOT / "OFFLINE_README.txt"
OUT_OFFLINE_ZIP = ROOT / "zugspitze_offline_pack.zip"
OUT_JSON = ROOT / "zugspitze_reintal_editable_points.json"
OUT_GPX = ROOT / "zugspitze_reintal_corrected_route.gpx"
OUT_KML = ROOT / "zugspitze_reintal_corrected_map.kml"
OUT_DESCENT_GPX = ROOT / "zugspitze_descent_options.gpx"
OUT_DESCENT_KML = ROOT / "zugspitze_descent_options.kml"
OSM_CACHE = ROOT / "zugspitze_reintal_osm_highways_cache.json"
DESCENT_OSM_CACHE = ROOT / "zugspitze_descent_osm_highways_cache.json"
OFFLINE_OSM_CACHE = ROOT / "zugspitze_offline_osm_cache.json"
LEAFLET_CSS_CACHE = ROOT / "leaflet_1_9_4.css"
LEAFLET_JS_CACHE = ROOT / "leaflet_1_9_4.js"
LEAFLET_CSS_URL = "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css"
LEAFLET_JS_URL = "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"
PUBLIC_MAP_URL = "https://anton5267.github.io/zugspitze-reintal-offline-map/"


KLAMMAUSGANG = (47.460017, 11.123798)
BOCKHUETTE = (47.418172, 11.094303)

POI = [
    {"id": "01", "name": "Kainzenbad", "lat": 47.483200, "lon": 11.128290, "kind": "poi", "note": "Старт логістики / паркінг"},
    {"id": "02", "name": "Parkplatz Skistadion", "lat": 47.482395, "lon": 11.117842, "kind": "poi", "note": "Фактичний старт GPX"},
    {"id": "03", "name": "Nordportal Partnachklamm", "lat": 47.475589, "lon": 11.114167, "kind": "poi", "note": "Вхід у Partnachklamm"},
    {"id": "04", "name": "Klammausgang / Südportal", "lat": 47.460017, "lon": 11.123798, "kind": "risk", "note": "Не йти прямо на червону ділянку. Звідси на обхід через Partnachalm."},
    {"id": "05", "name": "Partnachalm", "lat": 47.462900, "lon": 11.118870, "kind": "hut", "note": "Ключова точка обходу"},
    {"id": "06", "name": "Streichla / Hoher Weg", "lat": 47.468150, "lon": 11.118650, "kind": "check", "note": "Орієнтир перед виходом на Hoher Weg"},
    {"id": "07", "name": "Bockhütte", "lat": 47.418172, "lon": 11.094303, "kind": "hut", "note": "Повернення на основний Reintal-маршрут"},
    {"id": "08", "name": "Reintalangerhütte", "lat": 47.405319, "lon": 11.035681, "kind": "hut", "note": "Контрольна точка / хата"},
    {"id": "09", "name": "Knorrhütte", "lat": 47.410018, "lon": 11.012785, "kind": "hut", "note": "Контроль перед Zugspitzplatt"},
    {"id": "10", "name": "Sonnalpin / Gletscherbahn Talstation", "lat": 47.413623, "lon": 10.980062, "kind": "risk", "note": "Контроль перед фінальною альпійською ділянкою"},
    {"id": "11", "name": "Münchner Haus", "lat": 47.421024, "lon": 10.984644, "kind": "hut", "note": "Гірський будинок біля вершини"},
    {"id": "12", "name": "Zugspitze", "lat": 47.421219, "lon": 10.986307, "kind": "summit", "note": "Вершина"},
]

WATER = [
    {"id": "W1", "name": "Partnach біля Bockhütte", "lat": 47.418250, "lon": 11.093850, "note": "Потік; воду фільтрувати/очищати"},
    {"id": "W2", "name": "Витоки Partnach біля Reintalangerhütte", "lat": 47.404600, "lon": 11.032800, "note": "Потоки / витоки; воду фільтрувати/очищати"},
    {"id": "W3", "name": "Сервіс / вода у Partnachalm", "lat": 47.462900, "lon": 11.118870, "note": "Сервіс залежить від роботи об'єкта; перевірити на місці"},
    {"id": "W4", "name": "Сервіс / вода у Reintalangerhütte", "lat": 47.405319, "lon": 11.035681, "note": "Хата у сезон; не планувати без власного запасу"},
    {"id": "W5", "name": "Сервіс / вода у Knorrhütte", "lat": 47.410018, "lon": 11.012785, "note": "Хата у сезон; вище надійних природних джерел менше"},
]

SOURCE_CHECK_DATE = "03.07.2026"

SOURCE_CHECKS = [
    {
        "id": "SRC-01",
        "name": "Partnachklamm",
        "url": "https://www.partnachklamm.de/de/Zeiten%20-%20Preise",
        "note": "Клямм відкрита; шлях після Partnachklamm у напрямку Bockhütte/Reintal вказано як закритий приблизно до 13.07.2026; обхід через Partnachalm.",
    },
    {
        "id": "SRC-02",
        "name": "DAV Sicher auf die Zugspitze",
        "url": "https://www.alpenverein.de/artikel/sicher-auf-die-zugspitze_d6656f66-4dc5-4e9c-bd6e-ca81704a79f5",
        "note": "Reintal довгий і віддалений; ризики: туман на Zugspitzplatt, снігові поля, осип/скелі у фіналі, рішення про Bahn біля Sonnalpin.",
    },
    {
        "id": "SRC-03",
        "name": "Zugspitze facilities",
        "url": "https://zugspitze.de/en/Service-information/Facilities",
        "note": "Станом на перевірку: Cable car Zugspitze, cogwheel train і Gletscherbahn позначені відкритими; перед виходом перевірити ще раз.",
    },
]

SAFETY_LINKS = [
    {
        "name": "Partnachklamm статус",
        "url": "https://www.partnachklamm.de/de/Zeiten%20-%20Preise",
        "note": "Перевірити відкриття клямму і закриття напрямку Bockhütte/Reintal у день виходу.",
    },
    {
        "name": "Zugspitze timetable / facilities",
        "url": "https://zugspitze.de/en/Service-information/Facilities",
        "note": "Перевірити Cable car, Gletscherbahn, cogwheel train і останні рейси вниз.",
    },
    {
        "name": "DAV Bergwetter",
        "url": "https://www.alpenverein.de/bergwetter/alpen/allgauer-und-bayerische-alpen-west-osterreich-nord",
        "note": "Гірська погода, грози, вітер, видимість і температура на висоті.",
    },
    {
        "name": "DWD Südbayern",
        "url": "https://www.dwd.de/DE/wetter/vorhersage_aktuell/suedbayern/vhs_suedbay_node.html",
        "note": "Офіційний прогноз DWD для південної Баварії, включно з температурою на Zugspitze.",
    },
    {
        "name": "Lawinenwarndienst Bayern",
        "url": "https://lawinenwarndienst.bayern.de/",
        "note": "Якщо є сніг/снігові поля, перевірити лавинну ситуацію навіть улітку після холодних періодів.",
    },
    {
        "name": "SOS EU ALP",
        "url": "https://www.leitstelle.tirol/leistungen/soseualpapp/",
        "note": "Корисний emergency app для Альп; 112 залишається головним номером.",
    },
]

PRE_DEPARTURE_CHECKS = [
    "Partnachklamm: перевірити, чи актуальний обхід через Partnachalm / Hoher Weg.",
    "Погода: гроза, вітер, туман, температура на Zugspitzplatt/вершині.",
    "Сніг/снігові поля: перевірити Lawinenwarndienst Bayern і свіжі умови.",
    "Bahn: перевірити останні рейси Gletscherbahn, Cable car Zugspitze, Zugspitzbahn.",
    "GPX: імпортувати основний GPX і спуски в Organic Maps / Mapy.cz / Garmin.",
    "Офлайн-мапи: завантажити Bayern/Tirol у навігаторі до виходу.",
    "Телефон: 100% заряд, павербанк, кабель, режим економії не має вбити GPS.",
    "Вода: стартувати із запасом; природну воду фільтрувати/очищати.",
    "Час: якщо біля Knorrhütte або Sonnalpin пізно, не дотискати маршрут.",
    "SOS: 112, координати копіюються з popup/GPS, print.html зберегти або роздрукувати.",
]

IPHONE_OFFLINE_STEPS = [
    "Перед походом відкрити GitHub Pages і перевірити, що карта завантажилась.",
    "У навігаторі обов'язково імпортувати GPX: HTML у Safari не замінює офлайн-навігацію.",
    "В Organic Maps або Mapy.cz завантажити офлайн-мапи Bayern/Tirol.",
    "Зберегти GPX/KML і print.html у Files / iCloud Drive, щоб мати резерв без Safari.",
    "Дати Safari/навігатору доступ до Location; на маршруті перевірити GPS ще біля старту.",
    "Не покладатися на онлайн-супутник без інтернету; default-шар карти - офлайн OSM-вектор.",
]

SONNALPIN_DECISION = {
    "name": "Sonnalpin: точка рішення",
    "lat": 47.413623,
    "lon": 10.980062,
    "go": [
        "Є запас часу до останнього спуску Bahn.",
        "Немає грози, туману, сильного вітру або різкого погіршення погоди.",
        "Є сили, вода, теплий шар і нормальна видимість.",
        "Фінальна Schutt/Schrofen ділянка суха або прогнозовано безпечна.",
    ],
    "stop": [
        "Втома, судоми, нестача води або темп сильно впав.",
        "Туман на Zugspitzplatt, гроза, сильний вітер, мокрий камінь або снігові поля.",
        "Немає запасу часу до останньої Bahn.",
        "Є сумнів - обрати Gletscherbahn/Zugspitzbahn, не фінальний підйом.",
    ],
}

DECISION_POINTS = [
    {
        "id": "D01",
        "name": "Klammausgang: обхід",
        "lat": 47.460017,
        "lon": 11.123798,
        "kind": "route_decision",
        "priority": 1,
        "source": "Partnachklamm / скрін користувача",
        "url": "https://www.partnachklamm.de/de/Zeiten%20-%20Preise",
        "note": "Не йти прямо в закритий червоний коридор; переходити на Partnachalm / Hoher Weg.",
        "open_hint": "Ключова точка обходу.",
        "show_by_default": True,
    },
    {
        "id": "D02",
        "name": "Partnachalm: тримати Hoher Weg",
        "lat": 47.462900,
        "lon": 11.118870,
        "kind": "route_decision",
        "priority": 1,
        "source": "OSM / маршрут обходу",
        "url": "",
        "note": "Після Partnachalm не зрізати прямо до Bockhütte; тримати зелений обхід лівіше/західніше закритої ділянки.",
        "open_hint": "Контроль правильного обходу.",
        "show_by_default": True,
    },
    {
        "id": "D03",
        "name": "Bockhütte: контроль стану",
        "lat": 47.418172,
        "lon": 11.094303,
        "kind": "route_decision",
        "priority": 1,
        "source": "OSM / маршрут",
        "url": "https://xn--bockhtte-b6a.de/die-huette/",
        "note": "Повернення в Reintal. Перевірити воду/час/стан ніг перед довгою долиною.",
        "open_hint": "Їжа/напої без ночівлі.",
        "show_by_default": True,
    },
    {
        "id": "D04",
        "name": "Reintalangerhütte: рішення по темпу",
        "lat": 47.405319,
        "lon": 11.035681,
        "kind": "route_decision",
        "priority": 1,
        "source": "DAV / маршрут",
        "url": "https://www.alpenverein-muenchen-oberland.de/huetten/alpenvereinshuetten/reintalangerhuette",
        "note": "Якщо пізно або сильна втома, це логічна точка зупинки/переоцінки плану.",
        "open_hint": "Планова ночівля тільки з бронюванням.",
        "show_by_default": True,
    },
    {
        "id": "D05",
        "name": "Knorrhütte: останній великий контроль",
        "lat": 47.410018,
        "lon": 11.012785,
        "kind": "route_decision",
        "priority": 1,
        "source": "DAV / маршрут",
        "url": "https://www.alpenverein-muenchen-oberland.de/huetten/alpenvereinshuetten/knorrhuette",
        "note": "Перед Zugspitzplatt перевірити погоду, воду, час і варіанти Bahn.",
        "open_hint": "Вузол Reintal/Gatterl.",
        "show_by_default": True,
    },
    {
        "id": "D06",
        "name": "Sonnalpin: Bahn або фінал",
        "lat": 47.413623,
        "lon": 10.980062,
        "kind": "critical_decision",
        "priority": 1,
        "source": "DAV / Zugspitze facilities",
        "url": "https://zugspitze.de/en/Service-information/Facilities",
        "note": "Якщо втома, туман, сніг, гроза або мало часу - обрати Bahn. Фінальний підйом не дотискати через его.",
        "open_hint": "Перевірити останній рейс.",
        "show_by_default": True,
    },
    {
        "id": "D07",
        "name": "Zugspitze: спуск без ризику",
        "lat": 47.421219,
        "lon": 10.986307,
        "kind": "descent_decision",
        "priority": 1,
        "source": "Маршрут / Zugspitze facilities",
        "url": "https://zugspitze.de/en/Service-information/Facilities",
        "note": "Після вершини найпростіший спуск - Bahn. Пішохідні червоні/технічні варіанти не планувати.",
        "open_hint": "Обрати спуск у вкладці Спуск.",
        "show_by_default": True,
    },
]

HUTS = [
    {
        "id": "H01",
        "name": "Partnachalm",
        "lat": 47.462900,
        "lon": 11.118870,
        "kind": "hut_food",
        "priority": 1,
        "source": "OSM / маршрут обходу",
        "url": "",
        "note": "Ключова точка зеленого обходу через Hoher Weg.",
        "open_hint": "Сервіс перевірити перед виходом.",
        "show_by_default": True,
    },
    {
        "id": "H02",
        "name": "Bockhütte",
        "lat": 47.418172,
        "lon": 11.094303,
        "kind": "hut_food_no_sleep",
        "priority": 1,
        "source": "Офіційна сторінка Bockhütte / OSM",
        "url": "https://xn--bockhtte-b6a.de/die-huette/",
        "note": "Їжа/напої у сезон; повернення зеленого обходу в Reintal.",
        "open_hint": "Без ночівлі; зазвичай кінець червня - 2-га неділя вересня.",
        "show_by_default": True,
    },
    {
        "id": "H03",
        "name": "Reintalangerhütte",
        "lat": 47.405319,
        "lon": 11.035681,
        "kind": "dav_hut",
        "priority": 1,
        "source": "DAV München & Oberland",
        "url": "https://www.alpenverein-muenchen-oberland.de/huetten/alpenvereinshuetten/reintalangerhuette",
        "note": "Основна DAV-хата в Reintal, логічна ночівля/контрольна точка.",
        "open_hint": "DAV: відкрито; бронювання тільки онлайн.",
        "show_by_default": True,
    },
    {
        "id": "H04",
        "name": "Knorrhütte",
        "lat": 47.410018,
        "lon": 11.012785,
        "kind": "dav_hut",
        "priority": 1,
        "source": "DAV München & Oberland",
        "url": "https://www.alpenverein-muenchen-oberland.de/huetten/alpenvereinshuetten/knorrhuette",
        "note": "Ключова хата перед Zugspitzplatt; вузол для Reintal/Gatterl.",
        "open_hint": "DAV: відкрито; бронювання 2026 онлайн.",
        "show_by_default": True,
    },
    {
        "id": "H05",
        "name": "Münchner Haus",
        "lat": 47.421068,
        "lon": 10.984897,
        "kind": "summit_hut",
        "priority": 2,
        "source": "DAV / OSM",
        "url": "https://www.alpenverein-muenchen-oberland.de/huetten/selbstversorgerhuetten/muenchner-haus",
        "note": "Хата біля вершини Zugspitze.",
        "open_hint": "Ночівлю/місця перевіряти напряму перед плануванням.",
        "show_by_default": True,
    },
    {
        "id": "H06",
        "name": "Eckbauer",
        "lat": 47.465822,
        "lon": 11.133028,
        "kind": "hut_food",
        "priority": 3,
        "source": "OSM",
        "url": "",
        "note": "Їжа/орієнтир східніше Partnachklamm, корисно для запасного плану.",
        "open_hint": "Не на основній лінії маршруту; перевірити години.",
        "show_by_default": True,
    },
]

OVERNIGHT = [
    {
        "id": "O01",
        "name": "Reintalangerhütte",
        "lat": 47.405319,
        "lon": 11.035681,
        "kind": "official_hut",
        "priority": 1,
        "source": "DAV München & Oberland",
        "url": "https://www.alpenverein-muenchen-oberland.de/huetten/alpenvereinshuetten/reintalangerhuette",
        "note": "Планова ночівля тільки з бронюванням.",
        "open_hint": "Відкрито; бронювання онлайн.",
        "show_by_default": False,
    },
    {
        "id": "O02",
        "name": "Knorrhütte",
        "lat": 47.410018,
        "lon": 11.012785,
        "kind": "official_hut",
        "priority": 1,
        "source": "DAV München & Oberland",
        "url": "https://www.alpenverein-muenchen-oberland.de/huetten/alpenvereinshuetten/knorrhuette",
        "note": "Планова ночівля/резервний варіант перед або після вершини.",
        "open_hint": "Відкрито; бронювання 2026 онлайн.",
        "show_by_default": False,
    },
    {
        "id": "O03",
        "name": "Münchner Haus",
        "lat": 47.421068,
        "lon": 10.984897,
        "kind": "official_hut",
        "priority": 2,
        "source": "DAV / OSM",
        "url": "https://www.alpenverein-muenchen-oberland.de/huetten/selbstversorgerhuetten/muenchner-haus",
        "note": "Ночівля на вершині можлива тільки після перевірки місць/умов.",
        "open_hint": "Перевірити актуальний режим напряму.",
        "show_by_default": False,
    },
    {
        "id": "O04",
        "name": "Camping Erlebnis Zugspitze",
        "lat": 47.480592,
        "lon": 11.054203,
        "kind": "official_campsite",
        "priority": 2,
        "source": "Camping Resort Zugspitze / OSM",
        "url": "https://www.camping-resort-zugspitze.de/en/",
        "note": "Офіційний 3-star кемпінг у Grainau, корисно для логістики до/після походу.",
        "open_hint": "Бронювання/місця перевіряти напряму.",
        "show_by_default": False,
    },
    {
        "id": "O05",
        "name": "Camping Resort Zugspitze",
        "lat": 47.477903,
        "lon": 11.053471,
        "kind": "official_campsite",
        "priority": 2,
        "source": "Camping Resort Zugspitze / OSM",
        "url": "https://www.camping-resort-zugspitze.de/en/",
        "note": "Офіційний 5-star кемпінг у Grainau.",
        "open_hint": "Бронювання/місця перевіряти напряму.",
        "show_by_default": False,
    },
    {
        "id": "O06",
        "name": "5-Sterne-Camping Zugspitz Resort",
        "lat": 47.427295,
        "lon": 10.940006,
        "kind": "official_campsite",
        "priority": 3,
        "source": "Zugspitz Resort / OSM",
        "url": "https://www.zugspitz-resort.at/en/camping/",
        "note": "Офіційний кемпінг в Ehrwald, корисний для Gatterl-логістики.",
        "open_hint": "Сайт вказує year-round camping; бронювання перевірити напряму.",
        "show_by_default": False,
    },
    {
        "id": "O07",
        "name": "Аварійний shelter біля Graseck",
        "lat": 47.466387,
        "lon": 11.121766,
        "kind": "emergency_shelter",
        "priority": 4,
        "source": "OSM",
        "url": "",
        "note": "Тільки аварійна точка/укриття, не планова ночівля.",
        "open_hint": "Не планувати як кемпінг або бронь.",
        "show_by_default": False,
    },
]

WATER_SOURCES = [
    {
        "id": "W01",
        "name": "Питна вода біля Bockhütte",
        "lat": 47.418035,
        "lon": 11.094346,
        "kind": "drinking_water",
        "priority": 1,
        "source": "OSM",
        "url": "",
        "note": "OSM drinking_water; перевірити на місці, мати запас/фільтр.",
        "open_hint": "Не покладатися як на єдине джерело.",
        "show_by_default": True,
    },
    {
        "id": "W02",
        "name": "Partnach біля Bockhütte",
        "lat": 47.418250,
        "lon": 11.093850,
        "kind": "stream",
        "priority": 2,
        "source": "Маршрут / OSM",
        "url": "",
        "note": "Потік; воду фільтрувати/очищати.",
        "open_hint": "Природне джерело, якість не гарантується.",
        "show_by_default": True,
    },
    {
        "id": "W03",
        "name": "Veitsbrünnl",
        "lat": 47.405762,
        "lon": 11.013326,
        "kind": "drinking_water_spring",
        "priority": 1,
        "source": "OSM",
        "url": "",
        "note": "Джерело/питна вода біля Knorrhütte; перевірити на місці.",
        "open_hint": "Мати запас, не планувати без резерву.",
        "show_by_default": True,
    },
    {
        "id": "W04",
        "name": "Питна вода біля Knorrhütte",
        "lat": 47.409917,
        "lon": 11.013103,
        "kind": "drinking_water",
        "priority": 1,
        "source": "OSM",
        "url": "",
        "note": "OSM drinking_water поруч з Knorrhütte; перевірити на місці.",
        "open_hint": "Сервіс/доступність залежить від умов.",
        "show_by_default": True,
    },
    {
        "id": "W05",
        "name": "Partnachursprung",
        "lat": 47.405979,
        "lon": 11.028410,
        "kind": "spring",
        "priority": 2,
        "source": "OSM",
        "url": "",
        "note": "Джерело Partnach; цікава точка, воду фільтрувати/очищати.",
        "open_hint": "Короткий відхід від хати; не обов'язкова точка.",
        "show_by_default": True,
    },
    {
        "id": "W06",
        "name": "Сервіс / вода у Partnachalm",
        "lat": 47.462900,
        "lon": 11.118870,
        "kind": "service_water",
        "priority": 2,
        "source": "Маршрут / OSM",
        "url": "",
        "note": "Сервіс залежить від роботи об'єкта.",
        "open_hint": "Перевірити перед виходом.",
        "show_by_default": True,
    },
    {
        "id": "W07",
        "name": "Питна вода Skistadion",
        "lat": 47.481376,
        "lon": 11.116178,
        "kind": "drinking_water",
        "priority": 2,
        "source": "OSM",
        "url": "",
        "note": "Точка для стартового набору води біля Skistadion.",
        "open_hint": "Перевірити фактичну доступність.",
        "show_by_default": True,
    },
    {
        "id": "W08",
        "name": "Питна вода на Hoher Weg",
        "lat": 47.443913,
        "lon": 11.099339,
        "kind": "drinking_water",
        "priority": 2,
        "source": "OSM",
        "url": "",
        "note": "Корисна точка на зеленому обході; перевірити вручну.",
        "open_hint": "Не покладатися як на єдине джерело.",
        "show_by_default": True,
    },
    {
        "id": "W09",
        "name": "Фонтан / Sonnalpin",
        "lat": 47.413126,
        "lon": 10.979774,
        "kind": "fountain",
        "priority": 2,
        "source": "OSM",
        "url": "",
        "note": "Точка біля Sonnalpin/Zugspitzplatt; перевірити доступність.",
        "open_hint": "Залежить від роботи інфраструктури.",
        "show_by_default": True,
    },
    {
        "id": "W10",
        "name": "Сервіс / вода Reintalangerhütte",
        "lat": 47.405319,
        "lon": 11.035681,
        "kind": "service_water",
        "priority": 1,
        "source": "DAV / маршрут",
        "url": "https://www.alpenverein-muenchen-oberland.de/huetten/alpenvereinshuetten/reintalangerhuette",
        "note": "Сервіс у хаті; не планувати без власного запасу.",
        "open_hint": "Відкрито за DAV станом на перевірку.",
        "show_by_default": True,
    },
]

TOILETS = [
    {
        "id": "T01",
        "name": "Туалет Skistadion",
        "lat": 47.482175,
        "lon": 11.117866,
        "kind": "toilets",
        "priority": 1,
        "source": "OSM",
        "url": "",
        "note": "Стартова зона.",
        "open_hint": "Перевірити на місці.",
        "show_by_default": False,
    },
    {
        "id": "T02",
        "name": "Туалет Partnachklamm / Graseck",
        "lat": 47.469556,
        "lon": 11.119379,
        "kind": "toilets",
        "priority": 1,
        "source": "OSM",
        "url": "",
        "note": "Корисно перед/після Partnachklamm і перед обходом.",
        "open_hint": "Перевірити на місці.",
        "show_by_default": False,
    },
    {
        "id": "T03",
        "name": "Туалет на Hoher Weg",
        "lat": 47.444008,
        "lon": 11.099198,
        "kind": "toilets",
        "priority": 2,
        "source": "OSM",
        "url": "",
        "note": "OSM-точка біля зеленого обходу.",
        "open_hint": "Перевірити вручну.",
        "show_by_default": False,
    },
    {
        "id": "T04",
        "name": "Туалет Zugspitze summit",
        "lat": 47.421433,
        "lon": 10.984246,
        "kind": "toilets",
        "priority": 1,
        "source": "OSM",
        "url": "",
        "note": "Інфраструктура біля вершини.",
        "open_hint": "Залежить від роботи об'єктів.",
        "show_by_default": False,
    },
    {
        "id": "T05",
        "name": "Туалет Sonnalpin",
        "lat": 47.413432,
        "lon": 10.979923,
        "kind": "toilets",
        "priority": 1,
        "source": "OSM",
        "url": "",
        "note": "Інфраструктура біля Zugspitzplatt/Sonnalpin.",
        "open_hint": "Залежить від роботи об'єктів.",
        "show_by_default": False,
    },
]

EMERGENCY = [
    {
        "id": "E01",
        "name": "Bergwacht Garmisch-Partenkirchen",
        "lat": 47.484563,
        "lon": 11.126613,
        "kind": "mountain_rescue",
        "priority": 1,
        "source": "OSM",
        "url": "",
        "note": "Гірська рятувальна служба. Номер екстреної допомоги: 112.",
        "open_hint": "Аварійна інформація, не туристична точка.",
        "show_by_default": False,
    },
    {
        "id": "E02",
        "name": "Klinikum Garmisch-Partenkirchen",
        "lat": 47.483391,
        "lon": 11.127927,
        "kind": "hospital",
        "priority": 1,
        "source": "OSM",
        "url": "",
        "note": "Лікарня біля стартового району. Номер екстреної допомоги: 112.",
        "open_hint": "Для аварійної логістики.",
        "show_by_default": False,
    },
    {
        "id": "E03",
        "name": "Defibrillator Graseck",
        "lat": 47.469527,
        "lon": 11.119341,
        "kind": "defibrillator",
        "priority": 2,
        "source": "OSM",
        "url": "",
        "note": "AED біля Graseck/Partnachalm. Номер екстреної допомоги: 112.",
        "open_hint": "Аварійна точка.",
        "show_by_default": False,
    },
    {
        "id": "E04",
        "name": "Emergency phone Graseck",
        "lat": 47.467334,
        "lon": 11.120147,
        "kind": "emergency_phone",
        "priority": 2,
        "source": "OSM",
        "url": "",
        "note": "Аварійний телефон. Номер екстреної допомоги: 112.",
        "open_hint": "Перевірити фактичну доступність.",
        "show_by_default": False,
    },
    {
        "id": "E05",
        "name": "Defibrillator Skistadion",
        "lat": 47.481376,
        "lon": 11.116692,
        "kind": "defibrillator",
        "priority": 2,
        "source": "OSM",
        "url": "",
        "note": "AED біля старту. Номер екстреної допомоги: 112.",
        "open_hint": "Аварійна точка.",
        "show_by_default": False,
    },
]

TRANSPORT = [
    {
        "id": "TR01",
        "name": "Bus Skistadion",
        "lat": 47.482528,
        "lon": 11.117771,
        "kind": "bus_stop",
        "priority": 1,
        "source": "OSM",
        "url": "",
        "note": "Автобус біля старту/фінішу.",
        "open_hint": "Розклад перевірити перед поїздкою.",
        "show_by_default": False,
    },
    {
        "id": "TR02",
        "name": "Kainzenbad BZB halt",
        "lat": 47.483026,
        "lon": 11.116250,
        "kind": "rail_halt",
        "priority": 1,
        "source": "OSM",
        "url": "",
        "note": "Зупинка Bayerische Zugspitzbahn біля стартового району.",
        "open_hint": "Розклад перевірити.",
        "show_by_default": False,
    },
    {
        "id": "TR03",
        "name": "Zugspitzplatt",
        "lat": 47.413746,
        "lon": 10.980627,
        "kind": "rail_station",
        "priority": 1,
        "source": "OSM / zugspitze.de",
        "url": "https://zugspitze.de/en/Service-information/Facilities",
        "note": "Станція/вузол для Gletscherbahn і Zahnradbahn.",
        "open_hint": "Станом на перевірку Zugspitze facilities позначені open; перевірити ще раз.",
        "show_by_default": False,
    },
    {
        "id": "TR04",
        "name": "Eibsee BZB station",
        "lat": 47.456368,
        "lon": 10.993871,
        "kind": "rail_station",
        "priority": 1,
        "source": "OSM / zugspitze.de",
        "url": "https://zugspitze.de/en/Service-information/Facilities",
        "note": "Транспортний вузол для спуску Bahn/Eibsee/Garmisch.",
        "open_hint": "Розклад і останню поїздку перевірити.",
        "show_by_default": False,
    },
    {
        "id": "TR05",
        "name": "Garmisch-Partenkirchen BZB",
        "lat": 47.489652,
        "lon": 11.096565,
        "kind": "rail_station",
        "priority": 1,
        "source": "OSM",
        "url": "",
        "note": "Повернення в місто після Bahn/Eibsee.",
        "open_hint": "Розклад перевірити.",
        "show_by_default": False,
    },
    {
        "id": "TR06",
        "name": "Hammersbach",
        "lat": 47.466040,
        "lon": 11.046395,
        "kind": "rail_halt",
        "priority": 2,
        "source": "OSM",
        "url": "",
        "note": "Корисна станція для Höllental/логістики, не основний план.",
        "open_hint": "Розклад перевірити.",
        "show_by_default": False,
    },
    {
        "id": "TR07",
        "name": "Kreuzeck-/Alpspitzbahn",
        "lat": 47.472041,
        "lon": 11.062864,
        "kind": "rail_station",
        "priority": 2,
        "source": "OSM",
        "url": "",
        "note": "Корисний вузол для запасних варіантів/спусків.",
        "open_hint": "Розклад перевірити.",
        "show_by_default": False,
    },
    {
        "id": "TR08",
        "name": "Ehrwalder Almbahn Talstation",
        "lat": 47.387490,
        "lon": 10.938554,
        "kind": "cable_car",
        "priority": 2,
        "source": "OSM / Ehrwalder Almbahn",
        "url": "https://www.almbahn.at/de/sommer/wandern-bergsteigen/gatterl-tour/",
        "note": "Логістика для Gatterl/Ehrwald.",
        "open_hint": "Графік і останню поїздку перевірити.",
        "show_by_default": False,
    },
    {
        "id": "TR09",
        "name": "Tiroler Zugspitzbahn Talstation",
        "lat": 47.426491,
        "lon": 10.942844,
        "kind": "cable_car",
        "priority": 2,
        "source": "OSM / Tiroler Zugspitzbahn",
        "url": "https://www.zugspitze.at/en/peak/mountain-climbing/gatterl-tour/",
        "note": "Австрійський транспортний варіант для Gatterl.",
        "open_hint": "Графік і квитки перевірити.",
        "show_by_default": False,
    },
]

VIEWPOINTS = [
    {
        "id": "V01",
        "name": "Partnachursprung",
        "lat": 47.405979,
        "lon": 11.028410,
        "kind": "natural_view",
        "priority": 2,
        "source": "OSM",
        "url": "",
        "note": "Короткий відхід біля Reintalangerhütte; джерело Partnach.",
        "open_hint": "Не обов'язкова точка маршруту.",
        "show_by_default": False,
    },
    {
        "id": "V02",
        "name": "Zugspitzplatt",
        "lat": 47.413746,
        "lon": 10.980627,
        "kind": "viewpoint",
        "priority": 2,
        "source": "DAV / OSM",
        "url": "https://www.alpenverein.de/artikel/sicher-auf-die-zugspitze_d6656f66-4dc5-4e9c-bd6e-ca81704a79f5",
        "note": "Важлива орієнтаційна зона; у тумані бути особливо уважним.",
        "open_hint": "Контроль погоди обов'язковий.",
        "show_by_default": False,
    },
    {
        "id": "V03",
        "name": "Zugspitze summit",
        "lat": 47.421219,
        "lon": 10.986307,
        "kind": "summit_view",
        "priority": 1,
        "source": "Маршрут / OSM",
        "url": "",
        "note": "Вершина, 2962 м.",
        "open_hint": "Натовпи/погода/канатки перевірити.",
        "show_by_default": False,
    },
]

RISK_POINTS = [
    {
        "id": "R01",
        "name": "Не йти прямо після Klammausgang",
        "lat": 47.460017,
        "lon": 11.123798,
        "kind": "closure_decision",
        "priority": 1,
        "source": "Partnachklamm / скрін користувача",
        "url": "https://www.partnachklamm.de/de/Zeiten%20-%20Preise",
        "note": "Червоний напрямок Bockhütte/Reintal закритий приблизно до 13.07.2026; йти зеленим обходом через Partnachalm.",
        "open_hint": "Перевірити статус у день виходу.",
        "show_by_default": True,
    },
    {
        "id": "R02",
        "name": "Закрита лісова дорога",
        "lat": 47.444000,
        "lon": 11.111000,
        "kind": "closed_segment",
        "priority": 1,
        "source": "Partnachklamm / KML",
        "url": "https://www.partnachklamm.de/de/Zeiten%20-%20Preise",
        "note": "Червоний коридор не використовувати; він лишається на карті як заборона.",
        "open_hint": "Орієнтир для уникнення.",
        "show_by_default": True,
    },
    {
        "id": "R03",
        "name": "Sonnalpin: точка рішення",
        "lat": 47.413623,
        "lon": 10.980062,
        "kind": "decision_point",
        "priority": 1,
        "source": "DAV",
        "url": "https://www.alpenverein.de/artikel/sicher-auf-die-zugspitze_d6656f66-4dc5-4e9c-bd6e-ca81704a79f5",
        "note": "Якщо втома, туман або погода псується, DAV радить обрати Bahn замість фінального підйому.",
        "open_hint": "Перевірити останній рейс.",
        "show_by_default": True,
    },
    {
        "id": "R04",
        "name": "Zugspitzplatt: туман",
        "lat": 47.412800,
        "lon": 10.995000,
        "kind": "fog_risk",
        "priority": 1,
        "source": "DAV",
        "url": "https://www.alpenverein.de/artikel/sicher-auf-die-zugspitze_d6656f66-4dc5-4e9c-bd6e-ca81704a79f5",
        "note": "DAV окремо попереджає про обережність на Zugspitzplatt у тумані.",
        "open_hint": "Навігація і погода критичні.",
        "show_by_default": True,
    },
    {
        "id": "R05",
        "name": "Фінальна Schutt/Schrofen ділянка",
        "lat": 47.417600,
        "lon": 10.982200,
        "kind": "alpine_risk",
        "priority": 1,
        "source": "DAV",
        "url": "https://www.alpenverein.de/artikel/sicher-auf-die-zugspitze_d6656f66-4dc5-4e9c-bd6e-ca81704a79f5",
        "note": "Фінальний підйом має осип/скельні місця, місцями страховані ділянки, можливі снігові поля.",
        "open_hint": "Не йти в погану погоду або при втомі.",
        "show_by_default": True,
    },
    {
        "id": "R06",
        "name": "Bayernsteig / Stopselzieher не планувати",
        "lat": 47.456368,
        "lon": 10.993871,
        "kind": "closed_alternative",
        "priority": 2,
        "source": "DAV",
        "url": "https://www.alpenverein.de/artikel/sicher-auf-die-zugspitze_d6656f66-4dc5-4e9c-bd6e-ca81704a79f5",
        "note": "DAV пише, що Bayernsteig 812 від Eibsee до Wiener-Neustädter-Hütte закритий з 2024 через поганий стан.",
        "open_hint": "Не показано як нормальний варіант спуску.",
        "show_by_default": True,
    },
]

# OSM ways used by the forced detour route if a bbox Overpass query is unavailable.
ROUTE_WAY_IDS = [
    36337160,
    1306385574,
    45766679,
    45766678,
    1306387405,
    1306387406,
    23943079,
    36365527,
    36365521,
    36365516,
    35170390,
    35170227,
    89212925,
    36545912,
    38020466,
    26181728,
]


def haversine(a, b):
    lat1, lon1 = a
    lat2, lon2 = b
    radius = 6371000
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(x))


def load_source_gpx_points():
    root = ET.parse(SOURCE_GPX).getroot()
    return [
        (float(node.attrib["lat"]), float(node.attrib["lon"]))
        for node in root.findall(".//{*}trkpt")
    ]


def close_enough(point, target, meters=25):
    return haversine(point, target) <= meters


def parse_kml_linestring_by_name(name):
    text = SOURCE_KML.read_text(encoding="utf-8")
    pattern = (
        r"<Placemark><name>"
        + re.escape(name)
        + r"</name>.*?<coordinates>(.*?)</coordinates>"
    )
    match = re.search(pattern, text, flags=re.S)
    if not match:
        return []
    points = []
    for chunk in match.group(1).split():
        lon, lat, *_ = chunk.split(",")
        points.append((float(lat), float(lon)))
    return points


def fetch_osm_highways():
    if OSM_CACHE.exists():
        return json.loads(OSM_CACHE.read_text(encoding="utf-8"))

    payload = fetch_osm_route_ways_from_main_api()
    OSM_CACHE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload

    bbox = (47.410, 11.075, 47.480, 11.135)
    query = f"""
[out:json][timeout:60];
(
  way["highway"~"^(path|track|footway|steps|service|pedestrian|unclassified)$"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
);
(._;>;);
out body;
"""
    endpoints = [
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass-api.de/api/interpreter",
        "https://overpass.openstreetmap.ru/api/interpreter",
    ]
    last_error = None
    for endpoint in endpoints:
        request = urllib.request.Request(
            endpoint,
            data=urllib.parse.urlencode({"data": query}).encode(),
            headers={"User-Agent": "Codex local Zugspitze route builder"},
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.load(response)
                OSM_CACHE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                return payload
        except Exception as error:
            last_error = error
    payload = fetch_osm_route_ways_from_main_api()
    OSM_CACHE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def fetch_osm_route_ways_from_main_api():
    nodes = {}
    ways = {}
    for way_id in ROUTE_WAY_IDS:
        request = urllib.request.Request(
            f"https://www.openstreetmap.org/api/0.6/way/{way_id}/full",
            headers={"User-Agent": "Codex local Zugspitze route builder"},
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            root = ET.fromstring(response.read())
        for node in root.findall("node"):
            nodes[int(node.attrib["id"])] = {
                "type": "node",
                "id": int(node.attrib["id"]),
                "lat": float(node.attrib["lat"]),
                "lon": float(node.attrib["lon"]),
            }
        for way in root.findall("way"):
            way_nodes = [int(nd.attrib["ref"]) for nd in way.findall("nd")]
            tags = {tag.attrib["k"]: tag.attrib["v"] for tag in way.findall("tag")}
            ways[int(way.attrib["id"])] = {
                "type": "way",
                "id": int(way.attrib["id"]),
                "nodes": way_nodes,
                "tags": tags,
            }
    return {"elements": [*nodes.values(), *ways.values()]}


def build_osm_detour():
    data = fetch_osm_highways()
    nodes = {item["id"]: item for item in data["elements"] if item["type"] == "node"}
    ways = [item for item in data["elements"] if item["type"] == "way"]
    way_by_id = {way["id"]: way for way in ways}
    node_ways = {}
    for way in ways:
        for node_id in way.get("nodes", []):
            node_ways.setdefault(node_id, []).append(way)

    def coord(node_id):
        node = nodes[node_id]
        return (node["lat"], node["lon"])

    # These are the direct valley/original Reintal ways matching the red closed corridor.
    # They are excluded only from the green detour graph.
    closed_valley_way_ids = {
        512562022,
        230563342,
        230563341,
        230563340,
        36356826,
        36359372,
        36359371,
        36355954,
        45766680,
    }

    graph = {}
    for way in ways:
        tags = way.get("tags", {})
        if tags.get("access") == "private" or tags.get("foot") == "no":
            continue
        if way["id"] in closed_valley_way_ids:
            continue

        way_nodes = [node_id for node_id in way.get("nodes", []) if node_id in nodes]
        for a, b in zip(way_nodes, way_nodes[1:]):
            distance = haversine(coord(a), coord(b))
            graph.setdefault(a, []).append((b, distance, way["id"]))
            graph.setdefault(b, []).append((a, distance, way["id"]))

    def nearest(point, allowed_way_ids=None):
        best = None
        for node_id, node in nodes.items():
            if allowed_way_ids:
                way_ids = {way["id"] for way in node_ways.get(node_id, [])}
                if not way_ids.intersection(allowed_way_ids):
                    continue
            distance = haversine(point, (node["lat"], node["lon"]))
            if best is None or distance < best[0]:
                best = (distance, node_id)
        if best is None:
            raise RuntimeError(f"No OSM node found near {point}")
        return best[1]

    def shortest(start, target):
        queue = [(0, start)]
        previous = {start: (0, None, None)}
        settled = set()
        while queue:
            distance, node_id = heapq.heappop(queue)
            if node_id in settled:
                continue
            settled.add(node_id)
            if node_id == target:
                break
            for other_id, edge_distance, way_id in graph.get(node_id, []):
                next_distance = distance + edge_distance
                if other_id not in previous or next_distance < previous[other_id][0]:
                    previous[other_id] = (next_distance, node_id, way_id)
                    heapq.heappush(queue, (next_distance, other_id))
        if target not in previous:
            raise RuntimeError(f"No OSM route between {start} and {target}")

        path = []
        used_ways = []
        current = target
        while current is not None:
            path.append(current)
            _, parent, way_id = previous[current]
            if way_id is not None:
                used_ways.append(way_id)
            current = parent
        path.reverse()
        used_ways.reverse()
        return path, used_ways

    forced = [
        ("Klammausgang", KLAMMAUSGANG, None),
        ("Partnachalm", (47.462900, 11.118870), None),
        ("середина Hoher Weg", (47.4491327, 11.1054779), {36365527, 36365521}),
        ("південний Hoher Weg", (47.4431138, 11.0974843), {36365521}),
        ("міст біля Bockhütte", (47.4179786, 11.0941708), {26181727, 26181728, 36543674, 23941520}),
    ]

    forced_nodes = [(name, nearest(point, allowed)) for name, point, allowed in forced]
    route_nodes = []
    used_ways = []
    for (_, start), (_, target) in zip(forced_nodes, forced_nodes[1:]):
        segment_nodes, segment_ways = shortest(start, target)
        if route_nodes:
            route_nodes.extend(segment_nodes[1:])
        else:
            route_nodes.extend(segment_nodes)
        used_ways.extend(segment_ways)

    route_points = [KLAMMAUSGANG]
    route_points.extend(coord(node_id) for node_id in route_nodes)
    route_points.append(BOCKHUETTE)

    check_points = [
        {
            "id": f"ОБХІД-{index:02d}",
            "name": name,
            "lat": round(coord(node_id)[0], 7),
            "lon": round(coord(node_id)[1], 7),
            "note": "З OSM / перевірити вручну",
        }
        for index, (name, node_id) in enumerate(forced_nodes, start=1)
    ]
    check_points[0]["lat"], check_points[0]["lon"] = KLAMMAUSGANG
    check_points[-1]["lat"], check_points[-1]["lon"] = BOCKHUETTE

    used_way_ids = []
    for way_id in used_ways:
        if not used_way_ids or used_way_ids[-1] != way_id:
            used_way_ids.append(way_id)

    used_way_summary = []
    for way_id in used_way_ids:
        tags = way_by_id[way_id].get("tags", {})
        used_way_summary.append(
            {
                "osm_way_id": way_id,
                "name": tags.get("name", ""),
                "ref": tags.get("ref", ""),
                "highway": tags.get("highway", ""),
                "sac_scale": tags.get("sac_scale", ""),
            }
        )

    return route_points, check_points, used_way_summary


def replace_detour_in_track(source_points, detour_points):
    start_index = next(i for i, point in enumerate(source_points) if close_enough(point, KLAMMAUSGANG))
    end_index = next(
        i
        for i, point in enumerate(source_points[start_index:], start=start_index)
        if close_enough(point, BOCKHUETTE, meters=35)
    )
    return source_points[:start_index] + detour_points + source_points[end_index + 1 :]


def split_route_segments(corrected_points):
    def find(target):
        return min(range(len(corrected_points)), key=lambda index: haversine(corrected_points[index], target))

    indexes = {
        "Kainzenbad → Klammausgang": (0, find(KLAMMAUSGANG)),
        "Обхід через Partnachalm / Hoher Weg": (find(KLAMMAUSGANG), find(BOCKHUETTE)),
        "Bockhütte → Reintalangerhütte": (find(BOCKHUETTE), find((47.405319, 11.035681))),
        "Reintalangerhütte → Knorrhütte": (find((47.405319, 11.035681)), find((47.410018, 11.012785))),
        "Knorrhütte → Sonnalpin": (find((47.410018, 11.012785)), find((47.413623, 10.980062))),
        "Sonnalpin → Zugspitze": (find((47.413623, 10.980062)), len(corrected_points) - 1),
    }
    return {
        name: corrected_points[start : end + 1]
        for name, (start, end) in indexes.items()
        if start <= end
    }


def point_description(point):
    parts = []
    for key in ("note", "open_hint"):
        value = point.get(key)
        if value:
            parts.append(value)
    if point.get("source"):
        parts.append(f"Джерело: {point['source']}")
    if point.get("url"):
        parts.append(point["url"])
    if point.get("kind"):
        parts.append(f"Тип: {point['kind']}")
    return " | ".join(parts)


def export_map_points():
    groups = [
        HUTS,
        OVERNIGHT,
        WATER_SOURCES,
        TOILETS,
        EMERGENCY,
        TRANSPORT,
        VIEWPOINTS,
        RISK_POINTS,
        DECISION_POINTS,
        POI,
    ]
    points = []
    seen = set()
    for group in groups:
        for point in group:
            key = (
                point["name"].casefold(),
                round(point["lat"], 5),
                round(point["lon"], 5),
            )
            if key in seen:
                continue
            seen.add(key)
            points.append(point)
    return points


def fetch_descent_osm_highways():
    if DESCENT_OSM_CACHE.exists():
        return json.loads(DESCENT_OSM_CACHE.read_text(encoding="utf-8"))

    bbox = (47.360, 10.920, 47.500, 11.150)
    query = f"""
[out:json][timeout:90];
(
  way["highway"~"^(path|track|footway|steps|service|pedestrian|unclassified|residential|tertiary|secondary|living_street)$"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
);
(._;>;);
out body;
"""
    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.openstreetmap.ru/api/interpreter",
    ]
    last_error = None
    for endpoint in endpoints:
        request = urllib.request.Request(
            endpoint,
            data=urllib.parse.urlencode({"data": query}).encode(),
            headers={"User-Agent": "Codex local Zugspitze descent route builder"},
        )
        try:
            with urllib.request.urlopen(request, timeout=80) as response:
                payload = json.load(response)
            DESCENT_OSM_CACHE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            return payload
        except Exception as error:
            last_error = error
    raise RuntimeError(f"Could not fetch descent OSM data: {last_error}")


def offline_payload_has_context(payload):
    has_transport = False
    has_water = False
    for item in payload.get("elements", []):
        if item.get("type") != "way":
            continue
        tags = item.get("tags", {})
        has_transport = has_transport or "railway" in tags or "aerialway" in tags
        has_water = has_water or tags.get("natural") == "water" or "waterway" in tags
    return has_transport and has_water


def merge_osm_payloads(*payloads):
    elements = {}
    for payload in payloads:
        for item in payload.get("elements", []):
            if "type" in item and "id" in item:
                elements[(item["type"], item["id"])] = item
    return {"elements": list(elements.values())}


def fetch_offline_osm_features():
    if OFFLINE_OSM_CACHE.exists():
        cached = json.loads(OFFLINE_OSM_CACHE.read_text(encoding="utf-8"))
        if offline_payload_has_context(cached):
            return cached

    bbox = (47.360, 10.920, 47.500, 11.150)
    extra_query = f"""
[out:json][timeout:60];
(
  way["railway"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
  way["aerialway"~"^(cable_car|gondola|mixed_lift|chair_lift|drag_lift)$"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
  way["waterway"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
  way["natural"="water"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
);
(._;>;);
out body;
"""
    endpoints = [
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass-api.de/api/interpreter",
        "https://overpass.openstreetmap.ru/api/interpreter",
    ]
    highway_payload = fetch_descent_osm_highways()
    last_error = None
    for endpoint in endpoints:
        request = urllib.request.Request(
            endpoint,
            data=urllib.parse.urlencode({"data": extra_query}).encode(),
            headers={"User-Agent": "Codex local Zugspitze offline map builder"},
        )
        try:
            with urllib.request.urlopen(request, timeout=70) as response:
                extra_payload = json.load(response)
            payload = merge_osm_payloads(highway_payload, extra_payload)
            OFFLINE_OSM_CACHE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            return payload
        except Exception as error:
            last_error = error

    OFFLINE_OSM_CACHE.write_text(json.dumps(highway_payload, ensure_ascii=False), encoding="utf-8")
    print(f"WARNING: offline OSM extras unavailable, using highway-only cache: {last_error}")
    return highway_payload


def build_walking_graph(osm_payload):
    nodes = {item["id"]: item for item in osm_payload["elements"] if item["type"] == "node"}
    ways = [item for item in osm_payload["elements"] if item["type"] == "way"]
    graph = {}
    node_ways = {}

    def coord(node_id):
        node = nodes[node_id]
        return (node["lat"], node["lon"])

    for way in ways:
        tags = way.get("tags", {})
        if not tags.get("highway"):
            continue
        if tags.get("access") in {"private", "no"} or tags.get("foot") == "no":
            continue
        way_nodes = [node_id for node_id in way.get("nodes", []) if node_id in nodes]
        for node_id in way_nodes:
            node_ways.setdefault(node_id, []).append(way)
        for a, b in zip(way_nodes, way_nodes[1:]):
            distance = haversine(coord(a), coord(b))
            graph.setdefault(a, []).append((b, distance, way["id"]))
            graph.setdefault(b, []).append((a, distance, way["id"]))

    return nodes, ways, graph, node_ways


def nearest_graph_node(point, nodes, graph, node_ways=None, allowed_way_names=None, max_meters=450):
    allowed_way_names = {name.casefold() for name in (allowed_way_names or [])}
    best = None
    for node_id, node in nodes.items():
        if node_id not in graph:
            continue
        if allowed_way_names and node_ways:
            way_names = {
                way.get("tags", {}).get("name", "").casefold()
                for way in node_ways.get(node_id, [])
            }
            if not allowed_way_names.intersection(way_names):
                continue
        distance = haversine(point, (node["lat"], node["lon"]))
        if best is None or distance < best[0]:
            best = (distance, node_id)
    if best is None or best[0] > max_meters:
        raise RuntimeError(f"No OSM graph node close enough to {point}; best={best}")
    return best[1]


def shortest_graph_path(start, target, nodes, graph):
    target_coord = (nodes[target]["lat"], nodes[target]["lon"])
    queue = [(haversine((nodes[start]["lat"], nodes[start]["lon"]), target_coord), 0, start)]
    previous = {start: (0, None)}
    settled = set()
    while queue:
        _, distance, node_id = heapq.heappop(queue)
        if node_id in settled:
            continue
        settled.add(node_id)
        if node_id == target:
            break
        for other_id, edge_distance, _ in graph.get(node_id, []):
            next_distance = distance + edge_distance
            if other_id not in previous or next_distance < previous[other_id][0]:
                previous[other_id] = (next_distance, node_id)
                estimate = next_distance + haversine((nodes[other_id]["lat"], nodes[other_id]["lon"]), target_coord)
                heapq.heappush(queue, (estimate, next_distance, other_id))
    if target not in previous:
        raise RuntimeError(f"No OSM walking route between {start} and {target}")

    path = []
    current = target
    while current is not None:
        path.append(current)
        _, current = previous[current]
    path.reverse()
    return path


def osm_walking_route(points, nodes, graph, node_ways=None):
    route = []
    for start_point, target_point in zip(points, points[1:]):
        start_node = nearest_graph_node(start_point, nodes, graph, node_ways=node_ways)
        target_node = nearest_graph_node(target_point, nodes, graph, node_ways=node_ways)
        node_path = shortest_graph_path(start_node, target_node, nodes, graph)
        segment = [start_point]
        segment.extend((nodes[node_id]["lat"], nodes[node_id]["lon"]) for node_id in node_path)
        segment.append(target_point)
        if route and haversine(route[-1], segment[0]) < 8:
            route.extend(segment[1:])
        else:
            route.extend(segment)
    return route


def route_slice(points, start, target):
    start_index = min(range(len(points)), key=lambda index: haversine(points[index], start))
    target_index = min(range(len(points)), key=lambda index: haversine(points[index], target))
    if start_index <= target_index:
        return points[start_index : target_index + 1]
    return list(reversed(points[target_index : start_index + 1]))


def merge_route_parts(*parts):
    merged = []
    for part in parts:
        if not part:
            continue
        if merged and haversine(merged[-1], part[0]) < 12:
            merged.extend(part[1:])
        else:
            merged.extend(part)
    return merged


def safe_osm_route(points, nodes, graph, node_ways, fallback):
    try:
        return osm_walking_route(points, nodes, graph, node_ways=node_ways)
    except Exception as error:
        print(f"WARNING: fallback schematic route used for {points}: {error}")
        return fallback


def replace_start_connector(points):
    if len(points) < 2:
        return points
    kainzenbad = (47.483200, 11.128290)
    skistadion = (47.482395, 11.117842)
    if not (close_enough(points[0], kainzenbad, meters=120) and close_enough(points[1], skistadion, meters=120)):
        return points

    descent_osm = fetch_descent_osm_highways()
    nodes, _, graph, node_ways = build_walking_graph(descent_osm)
    connector = safe_osm_route(
        [points[0], points[1]],
        nodes,
        graph,
        node_ways,
        [points[0], points[1]],
    )
    return merge_route_parts(connector, points[1:])


def build_descent_options(corrected_points):
    summit = (47.421068, 10.984897)
    sonnalpin = (47.413623, 10.980062)
    knorrhuette = (47.410018, 11.012785)
    skistadion = (47.482395, 11.117842)
    kainzenbad = (47.483200, 11.128290)
    eibsee = (47.456368, 10.993871)
    garmisch_bzb = (47.489652, 11.096565)
    tiroler_zugspitzbahn = (47.426491, 10.942844)
    hoellentalangerhuette = (47.437930, 11.025166)
    hammersbach = (47.466040, 11.046395)
    alpspitze = (47.429390, 11.048800)

    sonnalpin_index = min(range(len(corrected_points)), key=lambda index: haversine(corrected_points[index], sonnalpin))
    reintal_from_sonnalpin = list(reversed(corrected_points[: sonnalpin_index + 1]))

    descent_osm = fetch_descent_osm_highways()
    descent_nodes, _, descent_graph, descent_node_ways = build_walking_graph(descent_osm)
    start_connector = safe_osm_route(
        [skistadion, kainzenbad],
        descent_nodes,
        descent_graph,
        descent_node_ways,
        [skistadion, kainzenbad],
    )

    def replace_kainzenbad_tail(line):
        if not line:
            return line
        if haversine(line[-1], kainzenbad) > 150:
            return line
        skistadion_index = min(range(len(line)), key=lambda index: haversine(line[index], skistadion))
        if haversine(line[skistadion_index], skistadion) > 80:
            return line
        return merge_route_parts(line[: skistadion_index + 1], start_connector)

    reintal_from_sonnalpin = replace_kainzenbad_tail(reintal_from_sonnalpin)
    reintal_full_line = replace_kainzenbad_tail([[lat, lon] for lat, lon in reversed(corrected_points)])

    gatterl_points = [
        {
            "id": "G01",
            "name": "Zugspitze / Münchner Haus",
            "lat": 47.421068,
            "lon": 10.984897,
            "kind": "descent_check",
            "note": "Старт порівняння спуску; не фінальне рішення маршруту.",
        },
        {
            "id": "G02",
            "name": "Sonnalpin / Zugspitzplatt",
            "lat": 47.413623,
            "lon": 10.980062,
            "kind": "descent_check",
            "note": "Точка рішення: при втомі або поганій погоді краще Bahn.",
        },
        {
            "id": "G03",
            "name": "Knorrhütte",
            "lat": 47.410018,
            "lon": 11.012785,
            "kind": "descent_hut",
            "note": "Вузол Reintal/Gatterl.",
        },
        {
            "id": "G04",
            "name": "Gatterl",
            "lat": 47.396354,
            "lon": 11.016521,
            "kind": "descent_pass",
            "note": "Перехід у бік Австрії; маршрут тільки для досвідчених у добру погоду.",
        },
        {
            "id": "G05",
            "name": "Hochfeldernalm",
            "lat": 47.384099,
            "lon": 10.996027,
            "kind": "descent_hut",
            "note": "Орієнтир на офіційному описі Gatterl Tour.",
        },
        {
            "id": "G06",
            "name": "Pestkapelle",
            "lat": 47.380053,
            "lon": 10.983480,
            "kind": "descent_check",
            "note": "Орієнтир перед Ehrwalder Alm.",
        },
        {
            "id": "G07",
            "name": "Tirolerhaus / Ehrwalder Alm",
            "lat": 47.385293,
            "lon": 10.969200,
            "kind": "descent_food",
            "note": "Логістична точка біля Ehrwalder Alm.",
        },
        {
            "id": "G08",
            "name": "Ehrwalder Almbahn Talstation",
            "lat": 47.387490,
            "lon": 10.938554,
            "kind": "descent_transport",
            "note": "Вихід до транспорту з боку Ehrwald.",
        },
    ]
    bahn_eibsee_points = [
        {
            "id": "BE01",
            "name": "Zugspitze / Münchner Haus",
            "lat": 47.421068,
            "lon": 10.984897,
            "kind": "cable_car_station",
            "note": "Вершина; Cable car Zugspitze вниз до Eibsee.",
        },
        {
            "id": "BE02",
            "name": "Eibsee",
            "lat": 47.456368,
            "lon": 10.993871,
            "kind": "cable_car_station",
            "note": "Низ Cable car Zugspitze; далі Zugspitzbahn/транспорт до Garmisch.",
        },
        {
            "id": "BE03",
            "name": "Garmisch-Partenkirchen BZB",
            "lat": 47.489652,
            "lon": 11.096565,
            "kind": "rail_station",
            "note": "Фініш логістики у Garmisch-Partenkirchen.",
        },
    ]
    bahn_sonnalpin_points = [
        {
            "id": "BS01",
            "name": "Zugspitze / Münchner Haus",
            "lat": 47.421068,
            "lon": 10.984897,
            "kind": "gletscherbahn_station",
            "note": "Вершина; Gletscherbahn вниз до Sonnalpin.",
        },
        {
            "id": "BS02",
            "name": "Sonnalpin / Zugspitzplatt",
            "lat": 47.413623,
            "lon": 10.980062,
            "kind": "gletscherbahn_station",
            "note": "Пересадка на cogwheel train.",
        },
        {
            "id": "BS03",
            "name": "Riffelriß",
            "lat": 47.434108,
            "lon": 10.986306,
            "kind": "rail_station",
            "note": "Проміжна станція Bayerische Zugspitzbahn.",
        },
        {
            "id": "BS04",
            "name": "Eibsee",
            "lat": 47.456368,
            "lon": 10.993871,
            "kind": "rail_station",
            "note": "Станція біля Eibsee.",
        },
        {
            "id": "BS05",
            "name": "Garmisch-Partenkirchen BZB",
            "lat": 47.489652,
            "lon": 11.096565,
            "kind": "rail_station",
            "note": "Bayerische Zugspitzbahn у Garmisch-Partenkirchen.",
        },
    ]
    tiroler_points = [
        {
            "id": "TZ01",
            "name": "Zugspitze / Münchner Haus",
            "lat": 47.421068,
            "lon": 10.984897,
            "kind": "cable_car_station",
            "note": "Вершина; Tiroler Zugspitzbahn вниз до Ehrwald/Obermoos.",
        },
        {
            "id": "TZ02",
            "name": "Tiroler Zugspitzbahn Talstation",
            "lat": 47.426491,
            "lon": 10.942844,
            "kind": "cable_car_station",
            "note": "Австрійська сторона; потрібна логістика назад до Garmisch/Grainau.",
        },
    ]
    stopselzieher_points = [
        {
            "id": "SZ01",
            "name": "Zugspitze / Münchner Haus",
            "lat": 47.421068,
            "lon": 10.984897,
            "kind": "blocked_descent",
            "note": "НЕ планувати без спорядження/досвіду; показано тільки для орієнтації.",
        },
        {
            "id": "SZ02",
            "name": "Wiener-Neustädter-Hütte",
            "lat": 47.423226,
            "lon": 10.970251,
            "kind": "blocked_descent",
            "note": "Вузол Stopselzieher/Österreichisches Schneekar.",
        },
        {
            "id": "SZ03",
            "name": "Tiroler Zugspitzbahn Talstation",
            "lat": 47.426491,
            "lon": 10.942844,
            "kind": "blocked_descent",
            "note": "Підхід з Tiroler Talstation не є Bayernsteig 812, але сам маршрут не простий.",
        },
        {
            "id": "SZ04",
            "name": "Eibsee / Bayernsteig 812",
            "lat": 47.456368,
            "lon": 10.993871,
            "kind": "closed_route",
            "note": "Bayernsteig 812 від Eibsee закритий з 2024; НЕ планувати.",
        },
    ]
    hoellental_points = [
        {
            "id": "HT01",
            "name": "Zugspitze",
            "lat": 47.421219,
            "lon": 10.986307,
            "kind": "blocked_descent",
            "note": "Höllental униз без Klettersteig-set/каски/льодовикового спорядження не планувати.",
        },
        {
            "id": "HT02",
            "name": "Höllentalangerhütte",
            "lat": 47.437930,
            "lon": 11.025166,
            "kind": "blocked_descent",
            "note": "Орієнтир у Höllental; вище є Klettersteig/льодовик.",
        },
        {
            "id": "HT03",
            "name": "Hammersbach",
            "lat": 47.466040,
            "lon": 11.046395,
            "kind": "rail_station",
            "note": "Вихід до транспорту, але сам маршрут з вершини технічний.",
        },
    ]
    jubilaeumsgrat_points = [
        {
            "id": "JG01",
            "name": "Zugspitze",
            "lat": 47.421219,
            "lon": 10.986307,
            "kind": "alpine_climb",
            "note": "Jubiläumsgrat не є нормальним спуском; це серйозна альпійська гребенева траверса.",
        },
        {
            "id": "JG02",
            "name": "Jubiläumsgrat / ridge",
            "lat": 47.425800,
            "lon": 11.016600,
            "kind": "alpine_climb",
            "note": "Схематична небезпечна ділянка; не планувати без альпійського досвіду.",
        },
        {
            "id": "JG03",
            "name": "Alpspitze",
            "lat": 47.429390,
            "lon": 11.048800,
            "kind": "alpine_climb",
            "note": "Фініш гребеня; далі складна логістика/спуск, не варіант для цього походу.",
        },
    ]
    summit_to_sonnalpin = route_slice(corrected_points, summit, sonnalpin)
    summit_to_knorr = route_slice(corrected_points, summit, knorrhuette)
    gatterl_tail = safe_osm_route(
        [
            knorrhuette,
            (47.396354, 11.016521),
            (47.3897203, 11.0044278),
            (47.3875393, 10.9956309),
            (47.380053, 10.983480),
            (47.385293, 10.969200),
            (47.387490, 10.938554),
        ],
        descent_nodes,
        descent_graph,
        descent_node_ways,
        [[point["lat"], point["lon"]] for point in gatterl_points[2:]],
    )
    gatterl_line = merge_route_parts(summit_to_knorr, gatterl_tail)
    stopselzieher_line = safe_osm_route(
        [(47.421068, 10.984897), (47.423226, 10.970251), (47.426491, 10.942844), (47.456368, 10.993871)],
        descent_nodes,
        descent_graph,
        descent_node_ways,
        [[point["lat"], point["lon"]] for point in stopselzieher_points],
    )
    hoellental_line = safe_osm_route(
        [(47.421219, 10.986307), hoellentalangerhuette, hammersbach],
        descent_nodes,
        descent_graph,
        descent_node_ways,
        [[point["lat"], point["lon"]] for point in hoellental_points],
    )
    jubilaeumsgrat_line = safe_osm_route(
        [(47.421219, 10.986307), alpspitze],
        descent_nodes,
        descent_graph,
        descent_node_ways,
        [[point["lat"], point["lon"]] for point in jubilaeumsgrat_points],
    )
    return [
        {
            "id": "descent_bahn_eibsee",
            "name": "Спуск: Cable car → Eibsee → Garmisch",
            "select_label": "Bahn Eibsee",
            "kind": "easy_transport_return",
            "status": "простий / рекомендовано",
            "recommendation": "recommended",
            "show_by_default": False,
            "source": "zugspitze.de facilities / tickets",
            "url": "https://zugspitze.de/en/Service-information/Facilities",
            "note": "Найпростіший спуск без пішої техніки: Cable car Zugspitze до Eibsee, далі транспорт.",
            "line": [summit, eibsee, garmisch_bzb],
            "points": bahn_eibsee_points,
        },
        {
            "id": "descent_bahn_sonnalpin",
            "name": "Спуск: Gletscherbahn → Sonnalpin → Zugspitzbahn",
            "select_label": "Bahn Sonnalpin",
            "kind": "easy_transport_return",
            "status": "простий / рекомендовано",
            "show_by_default": False,
            "source": "zugspitze.de facilities / BZB логістика",
            "url": "https://zugspitze.de/en/Service-information/Facilities",
            "note": "Безпечний варіант: з вершини Gletscherbahn до Sonnalpin, потім cogwheel train вниз.",
            "line": [summit, sonnalpin, (47.434108, 10.986306), eibsee, garmisch_bzb],
            "points": bahn_sonnalpin_points,
            "recommendation": "recommended",
        },
        {
            "id": "descent_tiroler_zugspitzbahn",
            "name": "Спуск: Tiroler Zugspitzbahn → Ehrwald",
            "select_label": "Bahn Ehrwald",
            "kind": "easy_transport_return",
            "status": "простий / логістика Австрія",
            "show_by_default": False,
            "source": "zugspitze.at",
            "url": "https://www.zugspitze.at/en/home/",
            "note": "Простий спуск канаткою на австрійський бік; треба окремо продумати повернення до Garmisch/Grainau.",
            "line": [summit, tiroler_zugspitzbahn],
            "points": tiroler_points,
            "recommendation": "recommended",
        },
        {
            "id": "descent_reintal_sonnalpin",
            "name": "Спуск: Gletscherbahn → Reintal назад",
            "select_label": "Reintal від Sonnalpin",
            "kind": "long_walking_return",
            "status": "пішки / дуже довго",
            "show_by_default": False,
            "source": "Поточний виправлений маршрут + DAV",
            "url": "https://www.alpenverein.de/artikel/sicher-auf-die-zugspitze_d6656f66-4dc5-4e9c-bd6e-ca81704a79f5",
            "note": "Простіше, ніж іти з вершини пішки: з вершини Gletscherbahn до Sonnalpin, далі довгий Reintal назад.",
            "line": reintal_from_sonnalpin,
            "points": [
                {
                    "id": "RS01",
                    "name": "Sonnalpin / старт пішки вниз",
                    "lat": 47.413623,
                    "lon": 10.980062,
                    "kind": "decision_point",
                    "note": "Звідси Reintal назад технічно найпростіший, але дуже довгий.",
                }
            ],
            "recommendation": "caution",
        },
        {
            "id": "descent_reintal_full",
            "name": "Спуск: Reintal повністю пішки з вершини",
            "select_label": "Reintal повністю",
            "kind": "long_walking_return",
            "status": "пішки / обережно",
            "show_by_default": False,
            "source": "Поточний виправлений маршрут, розвернутий назад.",
            "url": "https://www.alpenverein.de/artikel/sicher-auf-die-zugspitze_d6656f66-4dc5-4e9c-bd6e-ca81704a79f5",
            "note": "Дуже довго; перша ділянка вершина → Sonnalpin має Schutt/Schrofen і місцями страхування, без досвіду краще Gletscherbahn.",
            "line": reintal_full_line,
            "points": [],
            "recommendation": "caution",
        },
        {
            "id": "descent_gatterl_ehrwald",
            "name": "Спуск: Gatterl → Ehrwald",
            "select_label": "Gatterl",
            "kind": "draft_walking_return",
            "status": "не простий / досвід",
            "show_by_default": False,
            "source": "Офіційний опис Gatterl Tour / OSM координати",
            "url": "https://www.zugspitze.at/en/peak/mountain-climbing/gatterl-tour/",
            "note": "Чернетка для порівняння: офіційно high mountain terrain; не простий спуск без досвіду.",
            "line": gatterl_line,
            "points": gatterl_points,
            "recommendation": "caution",
        },
        {
            "id": "descent_stopselzieher_blocked",
            "name": "НЕ планувати: Stopselzieher / Bayernsteig",
            "select_label": "Stopselzieher",
            "kind": "blocked_walking_return",
            "status": "НЕ планувати",
            "show_by_default": False,
            "source": "DAV: Bayernsteig 812 закритий з 2024",
            "url": "https://www.alpenverein.de/artikel/sicher-auf-die-zugspitze_d6656f66-4dc5-4e9c-bd6e-ca81704a79f5",
            "note": "Показано червоним тільки щоб не переплутати з нормальним спуском. Для цього походу не використовувати.",
            "line": stopselzieher_line,
            "points": stopselzieher_points,
            "recommendation": "blocked",
        },
        {
            "id": "descent_hoellental_blocked",
            "name": "НЕ планувати: Höllental",
            "select_label": "Höllental",
            "kind": "technical_walking_return",
            "status": "НЕ планувати без спорядження",
            "show_by_default": False,
            "source": "DAV / Höllentalangerhütte",
            "url": "https://www.alpenverein.de/artikel/sicher-auf-die-zugspitze_d6656f66-4dc5-4e9c-bd6e-ca81704a79f5",
            "note": "Потребує Klettersteig-set/каску/льодовикове спорядження за умовами; без карабінів не варіант.",
            "line": hoellental_line,
            "points": hoellental_points,
            "recommendation": "blocked",
        },
        {
            "id": "descent_jubilaeumsgrat_blocked",
            "name": "НЕ планувати: Jubiläumsgrat",
            "select_label": "Jubiläumsgrat",
            "kind": "alpine_climb",
            "status": "НЕ спуск / альпійська траверса",
            "show_by_default": False,
            "source": "DAV / альпійські описи маршруту",
            "url": "https://www.alpenverein.de/artikel/sicher-auf-die-zugspitze_d6656f66-4dc5-4e9c-bd6e-ca81704a79f5",
            "note": "Не спусковий маршрут для цього плану; серйозна гребенева траверса, показано тільки як заборонений напрям.",
            "line": jubilaeumsgrat_line,
            "points": jubilaeumsgrat_points,
            "recommendation": "blocked",
        },
    ]


def write_gpx(points):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="Codex corrected Zugspitze map" xmlns="http://www.topografix.com/GPX/1/1">',
        "  <metadata><name>Zugspitze Reintal corrected route via Partnachalm / Hoher Weg</name></metadata>",
    ]
    for point in export_map_points():
        lines.append(
            f'  <wpt lat="{point["lat"]:.6f}" lon="{point["lon"]:.6f}">'
            f"<name>{html.escape(point['id'] + ' ' + point['name'])}</name>"
            f"<desc>{html.escape(point_description(point))}</desc></wpt>"
        )
    lines.append("  <trk><name>Zugspitze Reintal corrected route</name><trkseg>")
    for lat, lon in points:
        lines.append(f'    <trkpt lat="{lat:.6f}" lon="{lon:.6f}"></trkpt>')
    lines.append("  </trkseg></trk>")
    lines.append("</gpx>")
    OUT_GPX.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_descent_gpx(descent_options):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="Codex Zugspitze descent options" xmlns="http://www.topografix.com/GPX/1/1">',
        "  <metadata><name>Zugspitze descent options / спуски</name></metadata>",
    ]
    for option in descent_options:
        for point in option.get("points", []):
            lines.append(
                f'  <wpt lat="{point["lat"]:.6f}" lon="{point["lon"]:.6f}">'
                f"<name>{html.escape(point['id'] + ' ' + point['name'])}</name>"
                f"<desc>{html.escape(point.get('note', ''))}</desc></wpt>"
            )
        if not option.get("line"):
            continue
        lines.append(f"  <trk><name>{html.escape(option['name'])}</name>")
        lines.append(f"    <desc>{html.escape((option.get('status') or '') + ' | ' + (option.get('note') or ''))}</desc>")
        lines.append("    <trkseg>")
        for lat, lon in option["line"]:
            lines.append(f'      <trkpt lat="{lat:.6f}" lon="{lon:.6f}"></trkpt>')
        lines.append("    </trkseg>")
        lines.append("  </trk>")
    lines.append("</gpx>")
    OUT_DESCENT_GPX.write_text("\n".join(lines) + "\n", encoding="utf-8")


def kml_coords(points):
    return " ".join(f"{lon:.6f},{lat:.6f},0" for lat, lon in points)


def descent_style_id(option):
    if option.get("recommendation") == "blocked":
        return "blocked"
    if option.get("recommendation") == "caution":
        return "caution"
    return "recommended"


def write_descent_kml(descent_options):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
        "  <name>Zugspitze descent options / спуски</name>",
        '  <Style id="recommended"><LineStyle><color>ff64748b</color><width>4</width></LineStyle></Style>',
        '  <Style id="caution"><LineStyle><color>ff0ea5f9</color><width>4</width></LineStyle></Style>',
        '  <Style id="blocked"><LineStyle><color>ff2626dc</color><width>4</width></LineStyle></Style>',
    ]
    for option in descent_options:
        if option.get("line"):
            lines.append(
                f"  <Placemark><name>{html.escape(option['name'])}</name><styleUrl>#{descent_style_id(option)}</styleUrl>"
                f"<description>{html.escape((option.get('status') or '') + ' | ' + (option.get('note') or ''))}</description>"
                f"<LineString><tessellate>1</tessellate><coordinates>{kml_coords(option['line'])}</coordinates></LineString></Placemark>"
            )
        for point in option.get("points", []):
            lines.append(
                f"  <Placemark><name>{html.escape(point['id'] + ' ' + point['name'])}</name>"
                f"<description>{html.escape(point.get('note', ''))}</description><Point>"
                f"<coordinates>{point['lon']:.6f},{point['lat']:.6f},0</coordinates></Point></Placemark>"
            )
    lines.append("</Document></kml>")
    OUT_DESCENT_KML.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_kml(segments, closed_points, detour_check_points):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
        "  <name>Zugspitze Reintal corrected map</name>",
        '  <Style id="main"><LineStyle><color>ff16a34a</color><width>5</width></LineStyle></Style>',
        '  <Style id="detour"><LineStyle><color>ff22c55e</color><width>6</width></LineStyle></Style>',
        '  <Style id="closed"><LineStyle><color>ff4444ef</color><width>6</width></LineStyle></Style>',
        '  <Style id="alpine"><LineStyle><color>ffea33a9</color><width>5</width></LineStyle></Style>',
        '  <Style id="point"><IconStyle><scale>1.1</scale></IconStyle></Style>',
    ]
    for name, points in segments.items():
        style = "#detour" if "Обхід" in name else "#alpine" if "Sonnalpin" in name else "#main"
        lines.append(
            f"  <Placemark><name>{html.escape(name)}</name><styleUrl>{style}</styleUrl>"
            f"<LineString><tessellate>1</tessellate><coordinates>{kml_coords(points)}</coordinates></LineString></Placemark>"
        )
    lines.append(
        "  <Placemark><name>Закрито / НЕ ЙТИ</name><styleUrl>#closed</styleUrl>"
        f"<LineString><tessellate>1</tessellate><coordinates>{kml_coords(closed_points)}</coordinates></LineString></Placemark>"
    )
    for point in detour_check_points:
        lines.append(
            f"  <Placemark><name>{html.escape(point['id'] + ' ' + point['name'])}</name>"
            f"<description>{html.escape(point['note'])}</description><Point>"
            f"<coordinates>{point['lon']:.7f},{point['lat']:.7f},0</coordinates></Point></Placemark>"
        )
    for point in export_map_points():
        lines.append(
            f"  <Placemark><name>{html.escape(point['id'] + ' ' + point['name'])}</name>"
            f"<description>{html.escape(point_description(point))}</description><Point>"
            f"<coordinates>{point['lon']:.6f},{point['lat']:.6f},0</coordinates></Point></Placemark>"
        )
    lines.append("</Document></kml>")
    OUT_KML.write_text("\n".join(lines) + "\n", encoding="utf-8")


def round_points(points, digits=6):
    return [[round(lat, digits), round(lon, digits)] for lat, lon in points]


def write_json(original_points, corrected_points, detour_points, detour_check_points, closed_points, used_way_summary, descent_options):
    payload = {
        "note": "Обхід побудований з OSM і примусово проведений через Partnachalm / Hoher Weg. Перед виходом перевірити на карті і вручну.",
        "last_checked": SOURCE_CHECK_DATE,
        "sources": [
            "OpenStreetMap highway ways через OSM API за конкретними way ID",
            "Офіційне повідомлення Partnachklamm: напрямок Bockhütte/Reintal закритий, обхід через Partnachalm",
            "Скріншот закриття/обходу від користувача",
        ],
        "source_checks": SOURCE_CHECKS,
        "detour_points": detour_check_points,
        "closed_points": [
            {
                "id": f"ЗАКРИТО-{index:02d}",
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "note": "Закритий червоний коридор з початкової KML/source-мапи",
            }
            for index, (lat, lon) in enumerate(closed_points, start=1)
        ],
        "poi": POI,
        "huts": HUTS,
        "overnight": OVERNIGHT,
        "water": WATER_SOURCES,
        "water_sources": WATER_SOURCES,
        "toilets": TOILETS,
        "emergency": EMERGENCY,
        "transport": TRANSPORT,
        "viewpoints": VIEWPOINTS,
        "risk_points": RISK_POINTS,
        "decision_points": DECISION_POINTS,
        "safety_links": SAFETY_LINKS,
        "pre_departure_checks": PRE_DEPARTURE_CHECKS,
        "iphone_offline_steps": IPHONE_OFFLINE_STEPS,
        "sonnalpin_decision": SONNALPIN_DECISION,
        "public_map_url": PUBLIC_MAP_URL,
        "descent_options": [
            {
                **option,
                "line": round_points(option["line"]),
            }
            for option in descent_options
        ],
        "osm_way_summary": used_way_summary,
        "stats": {
            "original_track_points": len(original_points),
            "corrected_track_points": len(corrected_points),
            "detour_polyline_points": len(detour_points),
            "detour_distance_km": round(polyline_distance(detour_points) / 1000, 2),
            "corrected_total_distance_km": round(polyline_distance(corrected_points) / 1000, 2),
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def polyline_distance(points):
    return sum(haversine(a, b) for a, b in zip(points, points[1:]))


def js_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def html_items(items):
    return "\n".join(f"        <li>{html.escape(str(item))}</li>" for item in items)


def html_checks(items):
    return "\n".join(
        f'        <label class="check-item"><input type="checkbox"><span>{html.escape(str(item))}</span></label>'
        for item in items
    )


def html_source_links(items):
    lines = []
    for item in items:
        lines.append(
            f'        <li><a href="{html.escape(item["url"])}" target="_blank" rel="noreferrer">'
            f'{html.escape(item["name"])}</a> - {html.escape(item["note"])}</li>'
        )
    return "\n".join(lines)


def cached_text_asset(path, url):
    if path.exists():
        return path.read_text(encoding="utf-8")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Codex local Zugspitze offline HTML builder"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        text = response.read().decode("utf-8")
    path.write_text(text, encoding="utf-8")
    return text


def leaflet_assets_for_html():
    css = cached_text_asset(LEAFLET_CSS_CACHE, LEAFLET_CSS_URL)
    js = cached_text_asset(LEAFLET_JS_CACHE, LEAFLET_JS_URL)
    return css, js.replace("</script", "<\\/script")


def simplified_by_step(points, min_step_meters):
    if len(points) <= 2:
        return points
    simplified = [points[0]]
    last_kept = points[0]
    for point in points[1:-1]:
        if haversine(last_kept, point) >= min_step_meters:
            simplified.append(point)
            last_kept = point
    if haversine(simplified[-1], points[-1]) > 0.1:
        simplified.append(points[-1])
    return simplified


def offline_way_kind(tags):
    highway = tags.get("highway")
    if tags.get("natural") == "water" or tags.get("waterway"):
        return "water"
    if tags.get("aerialway"):
        return "aerial"
    if tags.get("railway"):
        return "rail"
    if highway in {"path", "footway", "steps", "pedestrian"}:
        return "path"
    if highway == "track":
        return "track"
    if highway:
        return "road"
    return None


def offline_way_min_step(kind):
    if kind == "path":
        return 18
    if kind in {"track", "water", "aerial"}:
        return 24
    return 34


def build_offline_base_ways():
    payload = fetch_offline_osm_features()
    nodes = {item["id"]: item for item in payload["elements"] if item["type"] == "node"}
    base_ways = []
    for way in (item for item in payload["elements"] if item["type"] == "way"):
        tags = way.get("tags", {})
        kind = offline_way_kind(tags)
        if not kind:
            continue
        coords = [
            (nodes[node_id]["lat"], nodes[node_id]["lon"])
            for node_id in way.get("nodes", [])
            if node_id in nodes
        ]
        if len(coords) < 2:
            continue
        closed = len(coords) > 3 and way.get("nodes", [None])[0] == way.get("nodes", [None])[-1]
        simplified = simplified_by_step(coords, offline_way_min_step(kind))
        if closed and haversine(simplified[0], simplified[-1]) > 0.1:
            simplified.append(simplified[0])
        if len(simplified) < 2:
            continue
        name = tags.get("name") or tags.get("ref") or tags.get("destination") or tags.get("highway") or tags.get("railway") or tags.get("aerialway") or tags.get("waterway") or ""
        base_ways.append(
            {
                "id": way.get("id"),
                "name": name,
                "kind": kind,
                "closed": closed and kind == "water",
                "line": round_points(simplified),
            }
        )
    return base_ways


def write_html(original_points, corrected_points, segments, detour_points, detour_check_points, closed_points, used_way_summary, descent_options):
    leaflet_css, leaflet_js = leaflet_assets_for_html()
    offline_base_ways = build_offline_base_ways()
    html_text = f"""<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Zugspitze Reintal: карта маршруту</title>
  <style>
{leaflet_css}
  </style>
  <style>
    :root {{
      --safe-top: env(safe-area-inset-top, 0px);
      --safe-right: env(safe-area-inset-right, 0px);
      --safe-bottom: env(safe-area-inset-bottom, 0px);
      --safe-left: env(safe-area-inset-left, 0px);
    }}
    html, body {{ width: 100%; height: 100%; margin: 0; overflow: hidden; }}
    body {{ font-family: Arial, sans-serif; -webkit-text-size-adjust: 100%; overscroll-behavior: none; }}
    #map {{ position: fixed; inset: 0; width: 100%; height: 100vh; background: #edf2f7; }}
    @supports (height: 100dvh) {{
      #map {{ height: 100dvh; }}
    }}
    .panel {{
      position: fixed; z-index: 9999; background: rgba(255,255,255,.94);
      border: 2px solid #1f2937; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,.22);
      box-sizing: border-box; padding: 10px 12px; font-size: 12px; line-height: 1.35; max-width: 480px;
      overflow-wrap: anywhere;
    }}
    .panel-top {{
      top: 10px; left: 10px; right: auto; width: min(360px, calc(100vw - 20px)); transform: none;
      background: rgba(255,251,235,.96); border-color: #b45309;
    }}
    .panel-left {{
      left: 14px; bottom: 78px; display: none; width: min(470px, calc(100vw - 28px));
      max-height: calc(100vh - 112px); overflow: auto;
    }}
    .panel-right {{
      right: 14px; bottom: 78px; display: none; max-width: 380px;
    }}
    .sos-panel {{
      left: 14px; bottom: 78px; display: none; width: min(390px, calc(100vw - 28px));
      border-color: #dc2626; background: rgba(255,247,237,.97);
    }}
    .decision-panel {{
      right: 14px; bottom: 78px; display: none; width: min(430px, calc(100vw - 28px));
      border-color: #d97706; background: rgba(255,251,235,.98);
    }}
    body.show-info-panel .panel-left,
    body.show-edit-panel .panel-right,
    body.show-sos-panel .sos-panel,
    body.show-decision-panel .decision-panel {{ display: block; }}
    .panel-header {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; margin-bottom: 5px; }}
    .panel-top .panel-header {{ justify-content: flex-start; align-items: center; }}
    .panel-close {{
      flex: 0 0 auto; border: 1px solid #9ca3af; background: #fff; color: #111827;
      border-radius: 5px; cursor: pointer; font: 700 12px Arial, sans-serif; line-height: 1;
      min-width: 58px; height: 24px; padding: 0 7px;
    }}
    .copy-box {{ width: 100%; height: 94px; margin-top: 8px; font: 11px Consolas, monospace; }}
    .small-btn {{ margin-top: 6px; padding: 5px 8px; border: 1px solid #374151; background: #f8fafc; cursor: pointer; border-radius: 5px; }}
    .info-tabs {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 4px; margin: 8px 0 10px; }}
    .info-tab {{
      min-height: 32px; border: 1px solid #cbd5e1; border-radius: 6px; background: #f8fafc; color: #111827;
      font: 700 11px Arial, sans-serif; cursor: pointer; padding: 0 4px;
    }}
    .info-tab.active {{ background: #111827; border-color: #111827; color: #fff; }}
    .info-section {{ display: none; }}
    .info-section.active {{ display: block; }}
    .info-section p {{ margin: 6px 0; }}
    .source-list {{ margin-top: 6px; padding-left: 16px; }}
    .source-list li {{ margin: 3px 0; }}
    .descent-picker {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; margin: 8px 0; }}
    .descent-btn {{
      min-height: 38px; border: 1px solid #cbd5e1; border-radius: 6px; background: #fff;
      color: #111827; font: 700 11px Arial, sans-serif; padding: 4px 6px; cursor: pointer; text-align: left;
    }}
    .descent-btn.recommended {{ border-color: #0ea5e9; }}
    .descent-btn.caution {{ border-color: #f59e0b; }}
    .descent-btn.blocked {{ border-color: #dc2626; color: #991b1b; }}
    .descent-btn.active {{ background: #111827; color: #fff; border-color: #111827; }}
    .descent-note {{
      min-height: 42px; border-left: 4px solid #64748b; background: #f8fafc; padding: 7px 9px;
      border-radius: 4px; margin-top: 7px;
    }}
    .descent-note.recommended {{ border-left-color: #0ea5e9; }}
    .descent-note.caution {{ border-left-color: #f59e0b; }}
    .descent-note.blocked {{ border-left-color: #dc2626; background: #fff7ed; }}
    .check-grid {{ display: grid; grid-template-columns: 1fr; gap: 6px; margin: 8px 0; }}
    .check-item {{
      display: grid; grid-template-columns: 18px 1fr; gap: 7px; align-items: start;
      padding: 6px 7px; border: 1px solid #e2e8f0; border-radius: 6px; background: rgba(248,250,252,.82);
    }}
    .check-item input {{ margin-top: 2px; }}
    .action-row {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; margin: 8px 0; }}
    .action-btn {{
      min-height: 38px; border: 1px solid #334155; border-radius: 6px; background: #fff;
      color: #111827; font: 700 12px Arial, sans-serif; cursor: pointer; padding: 5px 7px;
    }}
    .action-btn.warn {{ border-color: #d97706; color: #92400e; background: #fffbeb; }}
    .action-btn.danger {{ border-color: #dc2626; color: #991b1b; background: #fff7ed; }}
    .decision-box {{ border-left: 4px solid #d97706; background: #fffbeb; border-radius: 6px; padding: 8px 10px; margin: 8px 0; }}
    .decision-box ul {{ margin: 5px 0 0; padding-left: 17px; }}
    .decision-box li {{ margin: 3px 0; }}
    .offline-status {{
      position: fixed; z-index: 900; top: 10px; left: 50%; right: auto; transform: translateX(-50%);
      max-width: min(430px, calc(100vw - 560px));
      box-sizing: border-box; padding: 7px 10px; border: 1px solid #334155; border-radius: 999px;
      background: rgba(255,255,255,.92); color: #111827; font: 700 12px Arial, sans-serif;
      box-shadow: 0 1px 7px rgba(0,0,0,.16);
    }}
    body.is-offline .offline-status {{ border-color: #b45309; background: rgba(255,251,235,.97); }}
    .download-row {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; margin-top: 8px; }}
    .download-btn {{
      display: grid; place-items: center; min-height: 34px; padding: 0 6px; border: 1px solid #334155;
      border-radius: 6px; background: #fff; color: #111827; font-weight: 700; text-decoration: none; text-align: center;
    }}
    .sos-number {{ font-size: 26px; font-weight: 800; color: #991b1b; line-height: 1.1; }}
    .sos-list {{ margin: 8px 0 0; padding-left: 17px; }}
    .sos-list li {{ margin: 5px 0; }}
    .map-toggle {{
      position: fixed; z-index: 10000; bottom: 36px; display: inline-flex;
      align-items: center; justify-content: center; box-sizing: border-box; width: 82px; height: 46px; padding: 0;
      border: 1px solid #111827; border-radius: 999px; background: rgba(255,255,255,.96);
      color: #111827; font: 700 15px Arial, sans-serif; box-shadow: 0 2px 10px rgba(0,0,0,.24);
      cursor: pointer;
    }}
    .map-toggle[aria-expanded="true"] {{ background: #111827; color: #fff; }}
    .map-toggle-info {{ left: 10px; }}
    .map-toggle-descent {{ left: 102px; width: 90px; }}
    .map-toggle-sos {{ left: 202px; width: 72px; color: #991b1b; border-color: #991b1b; }}
    .map-toggle-center {{ left: 284px; }}
    .locate-toggle {{
      position: fixed; z-index: 10000; right: 14px; bottom: 92px;
      min-width: 66px; height: 42px; padding: 0 10px; border: 1px solid #1d4ed8;
      border-radius: 999px; background: rgba(255,255,255,.96); color: #1d4ed8;
      font: 800 13px Arial, sans-serif; box-shadow: 0 2px 10px rgba(0,0,0,.22); cursor: pointer;
    }}
    .locate-toggle.active {{ background: #1d4ed8; color: #fff; }}
    .locate-toggle.error {{ border-color: #dc2626; color: #991b1b; background: #fff7ed; }}
    body.show-info-panel .locate-toggle,
    body.show-edit-panel .locate-toggle,
    body.show-sos-panel .locate-toggle,
    body.show-decision-panel .locate-toggle {{ display: none; }}
    .detour-label {{
      background: #111827; color: #fff; border: 2px solid #22c55e; border-radius: 999px;
      width: 28px; height: 28px; display: grid; place-items: center; font-size: 11px; font-weight: 700;
    }}
    .legend-line {{ display: inline-block; width: 20px; height: 5px; vertical-align: middle; border-radius: 99px; }}
    .legend-dot {{ display: inline-block; width: 11px; height: 11px; vertical-align: middle; border-radius: 50%; }}
    .leaflet-popup-content {{ font-size: 13px; line-height: 1.35; max-width: 270px; }}
    .leaflet-control-layers-toggle {{
      background-image: none !important; display: grid !important; place-items: center;
      font: 800 11px Arial, sans-serif; text-indent: 0;
    }}
    .leaflet-control-layers-toggle::after {{ content: "Шари"; }}
    .poi-popup {{ border-left: 5px solid #64748b; padding-left: 8px; max-width: 250px; }}
    .poi-popup b {{ font-size: 13px; }}
    .poi-hut {{ border-left-color: #15803d; }}
    .poi-water {{ border-left-color: #2563eb; }}
    .poi-overnight {{ border-left-color: #7c3aed; }}
    .poi-emergency {{ border-left-color: #dc2626; }}
    .poi-transport {{ border-left-color: #64748b; }}
    .poi-risk {{ border-left-color: #d97706; }}
    .poi-view {{ border-left-color: #0891b2; }}
    .popup-meta {{ margin-top: 4px; color: #334155; }}
    .popup-copy {{
      margin-top: 7px; min-height: 34px; border: 1px solid #334155; border-radius: 6px;
      background: #fff; color: #111827; font: 700 12px Arial, sans-serif; padding: 0 8px; cursor: pointer;
    }}
    @media (max-width: 760px) {{
      .panel {{ font-size: 12px; }}
      .panel-top {{
        top: 8px; left: 8px; right: auto;
        width: min(360px, calc(100vw - 16px)); transform: none;
        max-height: 22vh; overflow: auto; padding: 8px 10px;
      }}
      .panel-left,
      .panel-right,
      .sos-panel,
      .decision-panel {{
        display: none; left: 8px; right: 8px;
        bottom: 96px; max-width: none;
        max-height: 52vh; overflow: auto; padding: 12px;
      }}
      body.show-info-panel .panel-left {{ display: block; }}
      body.show-edit-panel .panel-right {{ display: block; }}
      body.show-sos-panel .sos-panel {{ display: block; }}
      body.show-decision-panel .decision-panel {{ display: block; }}
      .panel-close {{ min-width: 70px; height: 34px; font-size: 13px; }}
      .small-btn {{ width: 100%; min-height: 44px; font-size: 14px; }}
      .info-tabs {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
      .info-tab {{ min-height: 38px; font-size: 12px; }}
      .descent-picker {{ grid-template-columns: 1fr; }}
      .descent-btn {{ min-height: 42px; font-size: 13px; }}
      .copy-box {{ height: 145px; font-size: 16px; }}
      .leaflet-popup-content {{ width: 230px !important; max-width: 230px !important; margin: 10px 12px; font-size: 12px; }}
      .leaflet-popup-content-wrapper {{ max-width: calc(100vw - 34px); box-sizing: border-box; }}
      .poi-popup {{ width: 218px; max-width: 218px; }}
      .popup-copy {{ width: 100%; box-sizing: border-box; min-height: 38px; font-size: 12px; }}
      .leaflet-top.leaflet-left,
      .leaflet-top.leaflet-right {{
        top: 124px;
      }}
      body.notice-hidden .leaflet-top.leaflet-left,
      body.notice-hidden .leaflet-top.leaflet-right {{
        top: 8px;
      }}
      .leaflet-control-layers {{
        max-width: 72vw; max-height: 42vh; overflow: auto; font-size: 13px;
      }}
      .leaflet-touch .leaflet-bar a,
      .leaflet-control-layers-toggle {{
        width: 38px; height: 38px; line-height: 38px;
      }}
      .leaflet-control-zoom {{
        transform: none; transform-origin: top left;
      }}
      .leaflet-control-scale {{ display: none; }}
      .leaflet-control-attribution {{ font-size: 9px; max-width: calc(100vw - 12px); }}
      .coords-panel {{ display: none; }}
      .offline-status {{ display: none; top: auto; left: 8px; right: 8px; bottom: 150px; transform: none; max-width: none; border-radius: 8px; }}
      body.is-offline .offline-status {{ display: block; }}
      .download-row {{ grid-template-columns: 1fr; }}
      .action-row {{ grid-template-columns: 1fr; }}
      .locate-toggle {{ right: 10px; bottom: 92px; min-width: 64px; height: 40px; }}
    }}
    @supports (-webkit-touch-callout: none) {{
      .panel-top {{
        top: calc(env(safe-area-inset-top, 0px) + 10px);
        left: calc(env(safe-area-inset-left, 0px) + 10px);
        width: min(360px, calc(100vw - env(safe-area-inset-left, 0px) - env(safe-area-inset-right, 0px) - 20px));
      }}
      .panel-left {{
        left: calc(env(safe-area-inset-left, 0px) + 14px);
        bottom: calc(env(safe-area-inset-bottom, 0px) + 78px);
      }}
      .panel-right {{
        right: calc(env(safe-area-inset-right, 0px) + 14px);
        bottom: calc(env(safe-area-inset-bottom, 0px) + 78px);
      }}
      .sos-panel {{
        left: calc(env(safe-area-inset-left, 0px) + 14px);
        bottom: calc(env(safe-area-inset-bottom, 0px) + 78px);
      }}
      .decision-panel {{
        right: calc(env(safe-area-inset-right, 0px) + 14px);
        bottom: calc(env(safe-area-inset-bottom, 0px) + 78px);
      }}
      .map-toggle {{
        bottom: calc(env(safe-area-inset-bottom, 0px) + 28px);
      }}
      .map-toggle-info {{ left: calc(env(safe-area-inset-left, 0px) + 10px); }}
      .map-toggle-descent {{ left: calc(env(safe-area-inset-left, 0px) + 102px); }}
      .map-toggle-sos {{ left: calc(env(safe-area-inset-left, 0px) + 202px); }}
      .map-toggle-center {{ left: calc(env(safe-area-inset-left, 0px) + 284px); }}
      .locate-toggle {{
        right: calc(env(safe-area-inset-right, 0px) + 10px);
        bottom: calc(env(safe-area-inset-bottom, 0px) + 92px);
      }}
      @media (max-width: 760px) {{
        .panel-top {{
          top: calc(env(safe-area-inset-top, 0px) + 8px);
          left: calc(env(safe-area-inset-left, 0px) + 8px);
          width: min(360px, calc(100vw - env(safe-area-inset-left, 0px) - env(safe-area-inset-right, 0px) - 16px));
        }}
        .panel-left,
        .panel-right,
        .sos-panel,
        .decision-panel {{
          left: calc(env(safe-area-inset-left, 0px) + 8px);
          right: calc(env(safe-area-inset-right, 0px) + 8px);
          bottom: calc(env(safe-area-inset-bottom, 0px) + 96px);
        }}
        .leaflet-top.leaflet-left,
        .leaflet-top.leaflet-right {{
          top: calc(env(safe-area-inset-top, 0px) + 124px);
        }}
        body.notice-hidden .leaflet-top.leaflet-left,
        body.notice-hidden .leaflet-top.leaflet-right {{
          top: calc(env(safe-area-inset-top, 0px) + 8px);
        }}
      }}
    }}
  </style>
</head>
<body>
  <div id="map"></div>
  <div id="offlineStatus" class="offline-status">Офлайн готово · перевірено {SOURCE_CHECK_DATE}</div>
  <div id="routeNotice" class="panel panel-top">
    <div class="panel-header">
      <b>Маршрут 10.07</b>
      <button id="closeRouteNotice" class="panel-close" type="button" aria-label="Закрити верхнє повідомлення" title="Закрити">Закрити</button>
    </div>
    <b>Червоне</b> = закрито.<br>
    <b>Зелене</b> = обхід<br>
    Partnachalm / Hoher Weg.<br>
    Деталі: <b>Інфо</b>.
  </div>
  <div id="infoPanel" class="panel panel-left">
    <div class="panel-header">
      <b>Zugspitze / Reintal — карта</b>
      <button id="closeInfoPanel" class="panel-close" type="button" aria-label="Закрити інфо" title="Закрити">Закрити</button>
    </div>
    <div class="info-tabs" role="tablist" aria-label="Розділи інформації">
      <button class="info-tab active" type="button" data-info-tab="before">Перед</button>
      <button class="info-tab" type="button" data-info-tab="route">Маршрут</button>
      <button class="info-tab" type="button" data-info-tab="descent">Спуск</button>
      <button class="info-tab" type="button" data-info-tab="water">Вода</button>
      <button class="info-tab" type="button" data-info-tab="sleep">Ночівля</button>
      <button class="info-tab" type="button" data-info-tab="risk">Ризики</button>
      <button class="info-tab" type="button" data-info-tab="offline">Офлайн</button>
    </div>
    <div class="info-section active" data-info-section="before">
      <p><b>Перед виходом:</b> коротка перевірка того, що реально впливає на безпеку.</p>
      <div class="check-grid">
{html_checks(PRE_DEPARTURE_CHECKS)}
      </div>
      <div class="action-row">
        <button id="showSonnalpinDecision" class="action-btn warn" type="button">Рішення Sonnalpin</button>
        <button id="showMyLocationFromInfo" class="action-btn" type="button">Моя GPS-позиція</button>
        <a class="download-btn" href="print.html" target="_blank" rel="noreferrer">Аварійний лист</a>
        <a class="download-btn" href="zugspitze_reintal_corrected_route.gpx" download>Основний GPX</a>
      </div>
      <p><b>Офіційні лінки для перевірки:</b></p>
      <ul class="source-list">
{html_source_links(SAFETY_LINKS)}
      </ul>
    </div>
    <div class="info-section" data-info-section="route">
      <span class="legend-line" style="background:#16a34a"></span> Основний маршрут<br>
      <span class="legend-line" style="background:#22c55e"></span> Обхід Partnachalm / Hoher Weg<br>
      <span class="legend-line" style="background:#ef4444"></span> Закрито / НЕ ЙТИ<br>
      <span class="legend-line" style="background:#9333ea"></span> Фінальна альпійська ділянка<br>
      <p>Kainzenbad → Skistadion → Partnachklamm → Partnachalm → Hoher Weg → Bockhütte → Reintalangerhütte → Knorrhütte → Sonnalpin → Zugspitze.</p>
      <p><b>Перевірено:</b> {SOURCE_CHECK_DATE}</p>
      <ul class="source-list">
        <li>Partnachklamm: напрямок Bockhütte/Reintal закритий приблизно до 13.07.2026, обхід через Partnachalm.</li>
        <li>Геометрія обходу: OSM highway ways, не пряма лінія від Partnachalm до Bockhütte.</li>
        <li>Zugspitze facilities: перед виходом ще раз перевірити канатку, Zugspitzbahn і Gletscherbahn.</li>
      </ul>
    </div>
    <div class="info-section" data-info-section="water">
      <span class="legend-dot" style="background:#2563eb"></span> Вода / джерела<br>
      <p>На карті додані вода біля Skistadion/Hoher Weg, Bockhütte, Partnachursprung, Reintalangerhütte, Veitsbrünnl, Knorrhütte і Sonnalpin.</p>
      <p><b>Природну воду фільтрувати або очищати.</b> Сервіс у хатах залежить від сезону й роботи об'єкта.</p>
    </div>
    <div class="info-section" data-info-section="sleep">
      <span class="legend-dot" style="background:#7c3aed"></span> Офіційна ночівля<br>
      <p>Планові варіанти: Reintalangerhütte, Knorrhütte, Münchner Haus, офіційні кемпінги Grainau та Zugspitz Resort Ehrwald.</p>
      <p>Bockhütte додана як їжа/напої без ночівлі. Аварійний shelter біля Graseck показаний тільки для надзвичайної ситуації.</p>
    </div>
    <div class="info-section" data-info-section="descent">
      <span class="legend-line" style="background:#0ea5e9"></span> Reintal назад<br>
      <span class="legend-dot" style="background:#64748b"></span> Bahn / транспорт<br>
      <span class="legend-line" style="background:#f59e0b"></span> Gatterl → Ehrwald<br>
      <span class="legend-line" style="background:#dc2626"></span> НЕ планувати<br>
      <div id="descentPicker" class="descent-picker" aria-label="Вибір маршруту спуску"></div>
      <button id="clearDescent" class="small-btn" type="button">Прибрати спуск з карти</button>
      <button id="showSonnalpinDecisionFromDescent" class="small-btn" type="button">Рішення на Sonnalpin</button>
      <div id="descentNote" class="descent-note">Вибери варіант спуску вище. Найпростіші - Bahn/Eibsee, Bahn/Sonnalpin або Tiroler Zugspitzbahn.</div>
      <p>Пішохідні спуски тут для порівняння. Червоні варіанти показані тільки як “не йти”.</p>
      <p>Stopselzieher/Eibsee пішки не рекомендований через закриття Bayernsteig 812 за DAV.</p>
    </div>
    <div class="info-section" data-info-section="risk">
      <span class="legend-dot" style="background:#d97706"></span> Ризик / точка рішення<br>
      <p>DAV описує Reintal як довгий і віддалений маршрут. Фінал після Sonnalpin має осип, скелі, можливі снігові поля й туман на Zugspitzplatt.</p>
      <p>При втомі, нестачі часу або поганій погоді рішення біля Sonnalpin: спускатися Bahn, а не дотискати фінальний відрізок.</p>
      <button id="showSonnalpinDecisionFromRisk" class="small-btn" type="button">Відкрити рішення Sonnalpin</button>
    </div>
    <div class="info-section" data-info-section="offline">
      <p><b>HTML працює без інтернету:</b> маршрути, спуски, POI, шари, popup і офлайн OSM-вектор уже всередині файла.</p>
      <p><b>Супутник тільки онлайн.</b> Якщо немає мережі, просто лишай шар “Офлайн OSM-вектор”.</p>
      <p>Для реального походу також завантажити GPX у навігатор: Organic Maps, Mapy.cz, Garmin або інший застосунок. На iPhone не розраховувати, що Safari сам надійно збереже сайт офлайн.</p>
      <div class="download-row">
        <a class="download-btn" href="zugspitze_reintal_corrected_route.gpx" download>Основний GPX</a>
        <a class="download-btn" href="zugspitze_descent_options.gpx" download>Спуски GPX</a>
        <a class="download-btn" href="zugspitze_descent_options.kml" download>KML</a>
        <a class="download-btn" href="print.html" target="_blank" rel="noreferrer">Аварійний лист</a>
        <a class="download-btn" href="zugspitze_offline_pack.zip" download>ZIP офлайн</a>
      </div>
      <p><b>iPhone офлайн:</b></p>
      <ul class="source-list">
{html_items(IPHONE_OFFLINE_STEPS)}
      </ul>
      <details>
        <summary><b>Розширене</b></summary>
        <button id="openEditFromInfo" class="small-btn" type="button">Правка обходу</button>
      </details>
    </div>
  </div>
  <div id="sosPanel" class="panel sos-panel">
    <div class="panel-header">
      <b>SOS / аварійне</b>
      <button id="closeSosPanel" class="panel-close" type="button" aria-label="Закрити SOS" title="Закрити">Закрити</button>
    </div>
    <div class="sos-number">112</div>
    <div>Екстрений номер у Німеччині та Австрії. У popup аварійних точок також є координати.</div>
    <ul class="sos-list">
      <li>Bergwacht Garmisch-Partenkirchen: шар “Аварійне”.</li>
      <li>Klinikum Garmisch-Partenkirchen: шар “Аварійне”.</li>
      <li>Defib/phone біля Graseck/Partnachalm: шар “Аварійне”.</li>
    </ul>
    <button id="copyMapCenter" class="small-btn" type="button">Копіювати координати центру карти</button>
  </div>
  <div id="sonnalpinDecisionPanel" class="panel decision-panel">
    <div class="panel-header">
      <b>Sonnalpin: рішення</b>
      <button id="closeSonnalpinDecision" class="panel-close" type="button" aria-label="Закрити рішення Sonnalpin" title="Закрити">Закрити</button>
    </div>
    <div class="decision-box">
      <b>Йти фінал до вершини тільки якщо:</b>
      <ul>
{html_items(SONNALPIN_DECISION["go"])}
      </ul>
    </div>
    <div class="decision-box" style="border-left-color:#dc2626;background:#fff7ed">
      <b>Не йти далі, брати Bahn якщо:</b>
      <ul>
{html_items(SONNALPIN_DECISION["stop"])}
      </ul>
    </div>
    <button id="focusSonnalpin" class="small-btn" type="button">Показати Sonnalpin на карті</button>
    <button id="selectBahnSonnalpin" class="small-btn" type="button">Показати простий спуск Bahn/Sonnalpin</button>
  </div>
  <div id="editPanel" class="panel panel-right">
    <div class="panel-header">
      <b>Правка точок обходу</b>
      <button id="closeEditPanel" class="panel-close" type="button" aria-label="Закрити правки" title="Закрити">Закрити</button>
    </div>
    Це не потрібно для звичайного перегляду. Відкривай тільки якщо треба вручну пересунути контрольні точки обходу.<br>
    Чорні маркери `D01...` можна перетягувати. Нижче координати після перетягування.
    <textarea id="coordsBox" class="copy-box" readonly></textarea>
    <button id="copyCoords" class="small-btn" type="button">Скопіювати координати</button>
  </div>
  <button id="infoToggle" class="map-toggle map-toggle-info" type="button" aria-expanded="false" aria-label="Відкрити інформацію">Інфо</button>
  <button id="descentToggle" class="map-toggle map-toggle-descent" type="button" aria-expanded="false" aria-label="Відкрити спуски">Спуск</button>
  <button id="sosToggle" class="map-toggle map-toggle-sos" type="button" aria-expanded="false" aria-label="Відкрити SOS">SOS</button>
  <button id="centerToggle" class="map-toggle map-toggle-center" type="button" aria-label="Повернути карту до маршруту">Центр</button>
  <button id="locateToggle" class="locate-toggle" type="button" aria-label="Показати мою GPS-позицію" title="Моя GPS-позиція">GPS</button>

  <script>
{leaflet_js}
  </script>
  <script>
    const originalGpx = {js_json(round_points(original_points))};
    const correctedRoute = {js_json(round_points(corrected_points))};
    const segments = {js_json({name: round_points(points) for name, points in segments.items()})};
    const detourOsm = {js_json(round_points(detour_points))};
    const closedLine = {js_json(round_points(closed_points))};
    const detourControlPoints = {js_json(detour_check_points)};
    const poi = {js_json(POI)};
    const huts = {js_json(HUTS)};
    const overnight = {js_json(OVERNIGHT)};
    const waterSources = {js_json(WATER_SOURCES)};
    const toilets = {js_json(TOILETS)};
    const emergencyPoints = {js_json(EMERGENCY)};
    const transportPoints = {js_json(TRANSPORT)};
    const viewpoints = {js_json(VIEWPOINTS)};
    const riskPoints = {js_json(RISK_POINTS)};
    const decisionPoints = {js_json(DECISION_POINTS)};
    const preDepartureChecks = {js_json(PRE_DEPARTURE_CHECKS)};
    const iphoneOfflineSteps = {js_json(IPHONE_OFFLINE_STEPS)};
    const safetyLinks = {js_json(SAFETY_LINKS)};
    const sonnalpinDecision = {js_json(SONNALPIN_DECISION)};
    const publicMapUrl = {js_json(PUBLIC_MAP_URL)};
    const sourceChecks = {js_json(SOURCE_CHECKS)};
    const sourceCheckDate = {js_json(SOURCE_CHECK_DATE)};
    const descentOptions = {js_json([{**option, "line": round_points(option["line"])} for option in descent_options])};
    const offlineBaseWays = {js_json(offline_base_ways)};
    const osmWaySummary = {js_json(used_way_summary)};
    const isPhoneLayout = window.matchMedia("(max-width: 760px)").matches;

    const map = L.map("map", {{
      center: [47.445, 11.055],
      zoom: 12,
      preferCanvas: true
    }});

    const offlineBaseLayer = L.layerGroup().addTo(map);
    const esriOnline = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}", {{
      maxZoom: 18,
      attribution: "Супутник онлайн: Esri, Maxar, Earthstar Geographics, GIS User Community"
    }});

    function baseWayStyle(kind, closed) {{
      if (kind === "path") return {{ color: "#64748b", weight: 1.3, opacity: .72, dashArray: "3 5" }};
      if (kind === "track") return {{ color: "#475569", weight: 1.7, opacity: .65, dashArray: "8 5" }};
      if (kind === "road") return {{ color: "#334155", weight: 1.2, opacity: .46 }};
      if (kind === "rail") return {{ color: "#1f2937", weight: 1.7, opacity: .72, dashArray: "7 5" }};
      if (kind === "aerial") return {{ color: "#7c3aed", weight: 1.5, opacity: .72, dashArray: "2 7" }};
      if (kind === "water") return {{
        color: "#0284c7", weight: closed ? .8 : 1.4, opacity: .58,
        fillColor: "#7dd3fc", fillOpacity: closed ? .22 : 0
      }};
      return {{ color: "#94a3b8", weight: 1, opacity: .55 }};
    }}

    offlineBaseWays.forEach((way) => {{
      const style = baseWayStyle(way.kind, way.closed);
      const layer = way.closed ? L.polygon(way.line, style) : L.polyline(way.line, style);
      if (way.name) layer.bindTooltip(way.name, {{ sticky: true }});
      layer.addTo(offlineBaseLayer);
    }});

    const originalLayer = L.layerGroup();
    L.polyline(originalGpx, {{ color: "#38bdf8", weight: 3, opacity: .65 }}).bindTooltip("Оригінальний GPX").addTo(originalLayer);

    const correctedLayer = L.layerGroup();
    Object.entries(segments).forEach(([name, points]) => {{
      let style = {{ color: "#16a34a", weight: 5, opacity: .9 }};
      if (name.includes("Обхід")) style = {{ color: "#22c55e", weight: 7, opacity: .96 }};
      if (name.includes("Sonnalpin")) style = {{ color: "#9333ea", weight: 5, opacity: .9, dashArray: "8 8" }};
      L.polyline(points, style).bindTooltip(name).addTo(correctedLayer);
    }});
    L.polyline(detourOsm, {{ color: "#86efac", weight: 11, opacity: .34 }}).bindTooltip("Детальний коридор обходу з OSM").addTo(correctedLayer);
    correctedLayer.addTo(map);

    const closedLayer = L.layerGroup().addTo(map);
    L.polyline(closedLine, {{ color: "#ef4444", weight: 7, opacity: .82 }}).bindTooltip("Закрито / НЕ ЙТИ").addTo(closedLayer);

    const hutLayer = L.layerGroup().addTo(map);
    const waterLayer = L.layerGroup().addTo(map);
    const riskLayer = L.layerGroup().addTo(map);
    const overnightLayer = L.layerGroup();
    const toiletLayer = L.layerGroup();
    const emergencyLayer = L.layerGroup();
    const transportLayer = L.layerGroup();
    const viewpointLayer = L.layerGroup();
    const decisionLayer = L.layerGroup().addTo(map);
    const locationLayer = L.layerGroup().addTo(map);
    const descentLayers = {{}};
    const descentOverlayLayers = {{}};
    const detourEditLayer = L.layerGroup();

    function escapeHtml(value) {{
      const text = String(value ?? "");
      return text.replace(/[&<>"']/g, (char) => {{
        if (char === "&") return "&amp;";
        if (char === "<") return "&lt;";
        if (char === ">") return "&gt;";
        if (char === '"') return "&quot;";
        return "&#39;";
      }});
    }}

    function markerHtml(color, label, borderColor = "#fff") {{
      return `<div style="background:${{color}}; color:#fff; width:24px; height:24px; border-radius:50%; border:2px solid ${{borderColor}}; display:grid; place-items:center; font-size:10px; font-weight:700; box-shadow:0 1px 4px rgba(0,0,0,.35);">${{escapeHtml(label)}}</div>`;
    }}

    function divIcon(color, label, borderColor) {{
      return L.divIcon({{ html: markerHtml(color, label, borderColor), className: "", iconSize: [28, 28], iconAnchor: [14, 14] }});
    }}

    function planningLabel(point) {{
      const kind = String(point.kind || "");
      if (kind.includes("emergency") || kind.includes("shelter")) return "не планова";
      if (kind.includes("hut_food_no_sleep")) return "без ночівлі";
      if (kind.includes("camp") || kind.includes("dav_hut") || kind.includes("summit_hut")) return "планова";
      return "";
    }}

    function pointPopup(point, tone) {{
      const lat = Number(point.lat);
      const lon = Number(point.lon);
      const coords = `${{lat.toFixed(6)}}, ${{lon.toFixed(6)}}`;
      const planned = planningLabel(point);
      const typeText = escapeHtml(point.kind || "точка");
      const parts = [
        `<b>${{escapeHtml(point.name)}}</b>`,
        `<div class="popup-meta">${{typeText}}${{planned ? " / " + escapeHtml(planned) : ""}}</div>`
      ];
      if (point.open_hint) parts.push(`<div><b>Статус:</b> ${{escapeHtml(point.open_hint)}}</div>`);
      if (point.note) parts.push(`<div>${{escapeHtml(point.note)}}</div>`);
      if (tone === "emergency") parts.push(`<div><b>112</b> - екстрений номер у Німеччині/Австрії.</div>`);
      if (point.source) parts.push(`<div class="popup-meta"><b>Джерело:</b> ${{escapeHtml(point.source)}}</div>`);
      if (point.url) parts.push(`<div><a href="${{escapeHtml(point.url)}}" target="_blank" rel="noreferrer">Відкрити джерело</a></div>`);
      parts.push(`<code>${{coords}}</code>`);
      parts.push(`<br><button class="popup-copy" type="button" data-coords="${{coords}}">Копіювати координати</button>`);
      return `<div class="poi-popup poi-${{tone}}">${{parts.join("")}}</div>`;
    }}

    function addPointMarkers(points, layer, color, label, tone, borderColor = "#fff") {{
      points.forEach((point) => {{
        const marker = L.marker([point.lat, point.lon], {{ icon: divIcon(color, label, borderColor) }})
          .bindPopup(pointPopup(point, tone), markerPopupOptions)
          .bindTooltip(point.name);
        marker.addTo(layer);
      }});
    }}

    function addDescentOption(option, layer, color, label, tone, dashArray) {{
      if (!option) return;
      if (option.line && option.line.length > 1) {{
        L.polyline(option.line, {{ color, weight: 4, opacity: .78, dashArray }})
          .bindTooltip(option.name)
          .addTo(layer);
      }}
      addPointMarkers(option.points || [], layer, color, label, tone);
    }}

    function descentVisual(option) {{
      if (option.recommendation === "blocked") return {{ color: "#dc2626", label: "!", tone: "risk", dash: "2 7" }};
      if (option.id.includes("gatterl")) return {{ color: "#f59e0b", label: "G", tone: "risk", dash: "7 7" }};
      if (option.id.includes("reintal")) return {{ color: "#0ea5e9", label: "R", tone: "view", dash: option.id.includes("full") ? "5 8" : "3 9" }};
      if (option.id.includes("tiroler")) return {{ color: "#64748b", label: "T", tone: "transport", dash: "2 8" }};
      return {{ color: "#64748b", label: "B", tone: "transport", dash: "2 8" }};
    }}

    const markerPopupOptions = isPhoneLayout
      ? {{
          maxWidth: 260,
          autoPan: true,
          keepInView: true,
          autoPanPaddingTopLeft: [18, 132],
          autoPanPaddingBottomRight: [18, 126]
        }}
      : {{ maxWidth: 320, autoPan: true, keepInView: true }};

    const routeCheckPoints = poi.filter((point) => !["hut", "risk", "summit"].includes(point.kind));
    addPointMarkers(huts, hutLayer, "#15803d", "H", "hut");
    addPointMarkers(waterSources, waterLayer, "#2563eb", "W", "water");
    addPointMarkers(riskPoints, riskLayer, "#d97706", "!", "risk", "#7c2d12");
    addPointMarkers(decisionPoints, decisionLayer, "#f59e0b", "D", "risk", "#7c2d12");
    addPointMarkers(overnight, overnightLayer, "#7c3aed", "N", "overnight");
    addPointMarkers(toilets, toiletLayer, "#0f766e", "WC", "view");
    addPointMarkers(emergencyPoints, emergencyLayer, "#dc2626", "SOS", "emergency", "#7f1d1d");
    addPointMarkers(transportPoints, transportLayer, "#64748b", "B", "transport");
    addPointMarkers(routeCheckPoints, viewpointLayer, "#0891b2", "C", "view");
    addPointMarkers(viewpoints, viewpointLayer, "#0891b2", "V", "view");

    descentOptions.forEach((option) => {{
      const layer = L.layerGroup();
      const visual = descentVisual(option);
      addDescentOption(option, layer, visual.color, visual.label, visual.tone, visual.dash);
      descentLayers[option.id] = layer;
      descentOverlayLayers[option.name] = layer;
    }});

    map.on("popupopen", (event) => {{
      const button = event.popup.getElement().querySelector(".popup-copy");
      if (!button) return;
      button.addEventListener("click", async () => {{
        const coords = button.getAttribute("data-coords");
        try {{
          await navigator.clipboard.writeText(coords);
          button.textContent = "Скопійовано";
          window.setTimeout(() => {{ button.textContent = "Копіювати координати"; }}, 1200);
        }} catch {{
          button.textContent = coords;
        }}
      }}, {{ once: true }});
    }});

    const detourMarkers = [];
    const detourCheckLine = L.polyline([], {{ color: "#111827", weight: 3, opacity: .9, dashArray: "4 8" }}).addTo(detourEditLayer);

    function updateEditedCoords() {{
      const edited = detourMarkers.map((marker, index) => {{
        const pos = marker.getLatLng();
        return {{
          id: detourControlPoints[index].id,
          name: detourControlPoints[index].name,
          lat: Number(pos.lat.toFixed(7)),
          lon: Number(pos.lng.toFixed(7)),
          note: detourControlPoints[index].note
        }};
      }});
      detourCheckLine.setLatLngs(edited.map((item) => [item.lat, item.lon]));
      document.getElementById("coordsBox").value = JSON.stringify({{ detour_points: edited }}, null, 2);
    }}

    detourControlPoints.forEach((point, index) => {{
      const marker = L.marker([point.lat, point.lon], {{
        draggable: true,
        icon: L.divIcon({{
          html: `<div class="detour-label">D${{String(index + 1).padStart(2, "0")}}</div>`,
          className: "",
          iconSize: [32, 32],
          iconAnchor: [16, 16]
        }})
      }})
        .bindPopup(`<b>${{point.id}}</b><br>${{point.name}}<br>${{point.note}}<br><code>${{point.lat}}, ${{point.lon}}</code>`, markerPopupOptions)
        .bindTooltip(point.id);
      marker.on("dragend", () => {{
        const pos = marker.getLatLng();
        marker.setPopupContent(`<b>${{point.id}}</b><br>${{point.name}}<br>${{point.note}}<br><code>${{pos.lat.toFixed(7)}}, ${{pos.lng.toFixed(7)}}</code>`);
        updateEditedCoords();
      }});
      marker.addTo(detourEditLayer);
      detourMarkers.push(marker);
    }});
    updateEditedCoords();

    document.getElementById("copyCoords").addEventListener("click", async () => {{
      const text = document.getElementById("coordsBox").value;
      const button = document.getElementById("copyCoords");
      try {{
        await navigator.clipboard.writeText(text);
        button.textContent = "Скопійовано";
        window.setTimeout(() => {{ button.textContent = "Скопіювати координати"; }}, 1200);
      }} catch {{
        document.getElementById("coordsBox").select();
      }}
    }});

    const infoToggle = document.getElementById("infoToggle");
    const descentToggle = document.getElementById("descentToggle");
    const sosToggle = document.getElementById("sosToggle");
    const centerToggle = document.getElementById("centerToggle");
    const locateToggle = document.getElementById("locateToggle");
    const routeNotice = document.getElementById("routeNotice");
    const offlineStatus = document.getElementById("offlineStatus");
    let locationWatchId = null;
    let locationMarker = null;
    let locationAccuracyCircle = null;

    function hideRouteNotice() {{
      routeNotice.style.display = "none";
      document.body.classList.add("notice-hidden");
    }}

    function activeInfoTabKey() {{
      return document.querySelector(".info-tab.active")?.getAttribute("data-info-tab") || "before";
    }}

    function syncPanelButtons() {{
      const infoOpen = document.body.classList.contains("show-info-panel");
      infoToggle.setAttribute("aria-expanded", infoOpen ? "true" : "false");
      descentToggle.setAttribute("aria-expanded", infoOpen && activeInfoTabKey() === "descent" ? "true" : "false");
      sosToggle.setAttribute("aria-expanded", document.body.classList.contains("show-sos-panel") ? "true" : "false");
    }}

    function activateInfoTab(key) {{
      document.querySelectorAll(".info-tab").forEach((button) => {{
        button.classList.toggle("active", button.getAttribute("data-info-tab") === key);
      }});
      document.querySelectorAll(".info-section").forEach((section) => {{
        section.classList.toggle("active", section.getAttribute("data-info-section") === key);
      }});
      syncPanelButtons();
    }}

    function setInfoPanel(open) {{
      document.body.classList.toggle("show-info-panel", open);
      if (open) {{
        hideRouteNotice();
        document.body.classList.remove("show-sos-panel");
        document.body.classList.remove("show-decision-panel");
        setEditPanel(false);
      }}
      syncPanelButtons();
    }}

    function setEditPanel(open) {{
      document.body.classList.toggle("show-edit-panel", open);
      if (open) {{
        hideRouteNotice();
        document.body.classList.remove("show-info-panel");
        document.body.classList.remove("show-sos-panel");
        document.body.classList.remove("show-decision-panel");
        if (!map.hasLayer(detourEditLayer)) detourEditLayer.addTo(map);
      }} else if (map.hasLayer(detourEditLayer)) {{
        map.removeLayer(detourEditLayer);
      }}
      syncPanelButtons();
    }}

    function setSosPanel(open) {{
      document.body.classList.toggle("show-sos-panel", open);
      if (open) {{
        hideRouteNotice();
        document.body.classList.remove("show-info-panel");
        document.body.classList.remove("show-decision-panel");
        setEditPanel(false);
        if (!map.hasLayer(emergencyLayer)) emergencyLayer.addTo(map);
      }}
      syncPanelButtons();
    }}

    function setDecisionPanel(open) {{
      document.body.classList.toggle("show-decision-panel", open);
      if (open) {{
        hideRouteNotice();
        document.body.classList.remove("show-info-panel");
        document.body.classList.remove("show-sos-panel");
        setEditPanel(false);
        if (!map.hasLayer(decisionLayer)) decisionLayer.addTo(map);
      }}
      syncPanelButtons();
    }}

    function focusSonnalpin() {{
      const point = sonnalpinDecision;
      map.setView([point.lat, point.lon], Math.max(map.getZoom(), 15), {{ animate: true }});
      L.popup(markerPopupOptions)
        .setLatLng([point.lat, point.lon])
        .setContent(`<div class="poi-popup poi-risk"><b>${{escapeHtml(point.name)}}</b><div>Точка рішення: фінал до вершини або Bahn вниз.</div><code>${{point.lat.toFixed(6)}}, ${{point.lon.toFixed(6)}}</code></div>`)
        .openOn(map);
    }}

    infoToggle.addEventListener("click", () => {{
      setInfoPanel(!document.body.classList.contains("show-info-panel"));
    }});
    descentToggle.addEventListener("click", () => {{
      const wasOpen = document.body.classList.contains("show-info-panel");
      const wasDescent = activeInfoTabKey() === "descent";
      activateInfoTab("descent");
      setInfoPanel(!(wasOpen && wasDescent));
    }});
    sosToggle.addEventListener("click", () => {{
      setSosPanel(!document.body.classList.contains("show-sos-panel"));
    }});
    centerToggle.addEventListener("click", () => fitRoute());
    document.getElementById("closeInfoPanel").addEventListener("click", () => setInfoPanel(false));
    document.getElementById("closeEditPanel").addEventListener("click", () => setEditPanel(false));
    document.getElementById("closeSosPanel").addEventListener("click", () => setSosPanel(false));
    document.getElementById("closeSonnalpinDecision").addEventListener("click", () => setDecisionPanel(false));
    document.getElementById("closeRouteNotice").addEventListener("click", hideRouteNotice);
    document.getElementById("openEditFromInfo").addEventListener("click", () => setEditPanel(true));
    document.getElementById("showSonnalpinDecision").addEventListener("click", () => setDecisionPanel(true));
    document.getElementById("showSonnalpinDecisionFromDescent").addEventListener("click", () => setDecisionPanel(true));
    document.getElementById("showSonnalpinDecisionFromRisk").addEventListener("click", () => setDecisionPanel(true));
    document.getElementById("focusSonnalpin").addEventListener("click", () => focusSonnalpin());
    document.getElementById("selectBahnSonnalpin").addEventListener("click", () => {{
      setDecisionPanel(false);
      activateInfoTab("descent");
      setInfoPanel(true);
      setSelectedDescent("descent_bahn_sonnalpin");
    }});
    document.getElementById("showMyLocationFromInfo").addEventListener("click", () => startLocationWatch());
    document.getElementById("copyMapCenter").addEventListener("click", async () => {{
      const center = map.getCenter();
      const coords = `${{center.lat.toFixed(6)}}, ${{center.lng.toFixed(6)}}`;
      const button = document.getElementById("copyMapCenter");
      try {{
        await navigator.clipboard.writeText(coords);
        button.textContent = "Скопійовано: " + coords;
        window.setTimeout(() => {{ button.textContent = "Копіювати координати центру карти"; }}, 1500);
      }} catch {{
        button.textContent = coords;
      }}
    }});

    function setLocateState(state, label) {{
      locateToggle.classList.toggle("active", state === "active");
      locateToggle.classList.toggle("error", state === "error");
      locateToggle.textContent = label;
    }}

    function updateLocationMarker(position) {{
      const lat = position.coords.latitude;
      const lon = position.coords.longitude;
      const accuracy = Math.round(position.coords.accuracy || 0);
      const coords = `${{lat.toFixed(6)}}, ${{lon.toFixed(6)}}`;
      const popup = `<div class="poi-popup poi-view"><b>Моя позиція</b><div>Точність GPS: ~${{accuracy}} м</div><code>${{coords}}</code><br><button class="popup-copy" type="button" data-coords="${{coords}}">Копіювати координати</button></div>`;
      if (!locationMarker) {{
        locationMarker = L.marker([lat, lon], {{ icon: divIcon("#1d4ed8", "GPS") }}).addTo(locationLayer);
        locationAccuracyCircle = L.circle([lat, lon], {{ radius: accuracy || 30, color: "#1d4ed8", weight: 1, opacity: .7, fillColor: "#60a5fa", fillOpacity: .18 }}).addTo(locationLayer);
      }} else {{
        locationMarker.setLatLng([lat, lon]);
        locationAccuracyCircle.setLatLng([lat, lon]);
        locationAccuracyCircle.setRadius(accuracy || 30);
      }}
      locationMarker.bindPopup(popup, markerPopupOptions);
      map.setView([lat, lon], Math.max(map.getZoom(), 15), {{ animate: true }});
      setLocateState("active", "GPS");
    }}

    function startLocationWatch() {{
      hideRouteNotice();
      if (!navigator.geolocation) {{
        setLocateState("error", "GPS!");
        alert("GPS недоступний у цьому браузері.");
        return;
      }}
      if (locationWatchId !== null) {{
        navigator.geolocation.clearWatch(locationWatchId);
        locationWatchId = null;
        setLocateState("", "GPS");
        return;
      }}
      setLocateState("active", "...");
      locationWatchId = navigator.geolocation.watchPosition(
        updateLocationMarker,
        (error) => {{
          setLocateState("error", "GPS!");
          alert("Не вдалося отримати GPS: " + error.message);
        }},
        {{ enableHighAccuracy: true, maximumAge: 10000, timeout: 15000 }}
      );
    }}

    locateToggle.addEventListener("click", () => startLocationWatch());

    function updateOnlineStatus() {{
      const offline = navigator.onLine === false;
      document.body.classList.toggle("is-offline", offline);
      offlineStatus.textContent = offline
        ? "Офлайн режим: маршрути і POI працюють; супутник недоступний"
        : `Офлайн готово · перевірено ${{sourceCheckDate}} · супутник онлайн за потреби`;
    }}

    window.addEventListener("online", updateOnlineStatus);
    window.addEventListener("offline", updateOnlineStatus);
    updateOnlineStatus();
    syncPanelButtons();

    document.querySelectorAll(".info-tab").forEach((button) => {{
      button.addEventListener("click", () => {{
        activateInfoTab(button.getAttribute("data-info-tab"));
      }});
    }});

    function layerBounds(layer) {{
      const bounds = L.latLngBounds([]);
      layer.eachLayer((item) => {{
        if (item.getBounds) {{
          bounds.extend(item.getBounds());
        }} else if (item.getLatLng) {{
          bounds.extend(item.getLatLng());
        }}
      }});
      return bounds;
    }}

    function setSelectedDescent(optionId) {{
      Object.values(descentLayers).forEach((layer) => {{
        if (map.hasLayer(layer)) map.removeLayer(layer);
      }});
      const note = document.getElementById("descentNote");
      document.querySelectorAll(".descent-btn").forEach((button) => {{
        button.classList.toggle("active", button.getAttribute("data-descent-id") === optionId);
      }});
      if (!optionId) {{
        note.className = "descent-note";
        note.textContent = "Вибери варіант спуску вище. Найпростіші - Bahn/Eibsee, Bahn/Sonnalpin або Tiroler Zugspitzbahn.";
        return;
      }}
      const option = descentOptions.find((item) => item.id === optionId);
      const layer = descentLayers[optionId];
      if (!option || !layer) return;
      layer.addTo(map);
      note.className = `descent-note ${{option.recommendation || ""}}`;
      note.innerHTML = `<b>${{escapeHtml(option.name)}}</b><br>${{escapeHtml(option.status || "")}}<br>${{escapeHtml(option.note || "")}}`;
      const bounds = layerBounds(layer);
      if (bounds.isValid()) {{
        map.fitBounds(bounds, isPhoneLayout
          ? {{ paddingTopLeft: [18, 96], paddingBottomRight: [18, 128] }}
          : {{ padding: [30, 30] }}
        );
      }}
      if (isPhoneLayout) setInfoPanel(false);
    }}

    function buildDescentPicker() {{
      const picker = document.getElementById("descentPicker");
      descentOptions.forEach((option) => {{
        const button = document.createElement("button");
        button.type = "button";
        button.className = `descent-btn ${{option.recommendation || ""}}`;
        button.setAttribute("data-descent-id", option.id);
        button.innerHTML = `${{escapeHtml(option.select_label || option.name)}}<br><small>${{escapeHtml(option.status || "")}}</small>`;
        button.addEventListener("click", () => setSelectedDescent(option.id));
        picker.appendChild(button);
      }});
      document.getElementById("clearDescent").addEventListener("click", () => setSelectedDescent(null));
    }}

    buildDescentPicker();

    const baseLayers = {{
        "Офлайн OSM-вектор": offlineBaseLayer,
        "Супутник онлайн": esriOnline
      }};
    const overlayLayers = {{
        "Виправлений маршрут / зелений": correctedLayer,
        "Закрито / НЕ ЙТИ": closedLayer,
        "Оригінальний GPX": originalLayer,
        "Хати / їжа": hutLayer,
        "Вода": waterLayer,
        "Ризики": riskLayer,
        "Точки рішення": decisionLayer,
        "Ночівля": overnightLayer,
        "Туалети": toiletLayer,
        "Аварійне": emergencyLayer,
        "Транспорт": transportLayer,
        "Оглядові / контрольні": viewpointLayer,
      }};
    Object.entries(descentOverlayLayers).forEach(([name, layer]) => {{
      overlayLayers[name] = layer;
    }});
    overlayLayers["Точки правки обходу"] = detourEditLayer;

    L.control.layers(
      baseLayers,
      overlayLayers,
      {{ collapsed: true }}
    ).addTo(map);

    map.attributionControl.addAttribution("Офлайн OSM: &copy; OpenStreetMap contributors");
    L.control.scale({{ imperial: false }}).addTo(map);
    const mouse = L.control({{ position: "bottomright" }});
    mouse.onAdd = function() {{
      const div = L.DomUtil.create("div", "panel coords-panel");
      div.style.position = "static";
      div.style.borderWidth = "1px";
      div.style.maxWidth = "220px";
      div.innerHTML = "Координати";
      map.on("mousemove", (event) => {{
        div.innerHTML = `Координати: ${{event.latlng.lat.toFixed(5)}} | ${{event.latlng.lng.toFixed(5)}}`;
      }});
      return div;
    }};
    mouse.addTo(map);

    function fitRoute() {{
      const bounds = L.polyline(correctedRoute).getBounds();
      if (isPhoneLayout) {{
        const noticeOpen = routeNotice.style.display !== "none";
        map.fitBounds(bounds, {{
          paddingTopLeft: [18, noticeOpen ? 146 : 64],
          paddingBottomRight: [18, 118]
        }});
      }} else {{
        map.fitBounds(bounds, {{ padding: [26, 26] }});
      }}
    }}

    fitRoute();
  </script>
</body>
</html>
"""
    OUT_HTML.write_text(html_text, encoding="utf-8")
    OUT_INDEX.write_text(html_text, encoding="utf-8")


def qr_data_url(text):
    try:
        import qrcode
    except Exception:
        return ""
    image = qrcode.make(text)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def point_rows(points):
    rows = []
    for point in points:
        rows.append(
            "<tr>"
            f"<td>{html.escape(point['id'])}</td>"
            f"<td>{html.escape(point['name'])}</td>"
            f"<td>{point['lat']:.6f}, {point['lon']:.6f}</td>"
            f"<td>{html.escape(point.get('note', ''))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def descent_rows(descent_options):
    rows = []
    for option in descent_options:
        rows.append(
            "<tr>"
            f"<td>{html.escape(option.get('select_label') or option['name'])}</td>"
            f"<td>{html.escape(option.get('status', ''))}</td>"
            f"<td>{html.escape(option.get('note', ''))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def write_print_html(descent_options):
    qr = qr_data_url(PUBLIC_MAP_URL)
    qr_html = f'<img class="qr" src="{qr}" alt="QR карта">' if qr else '<div class="qr-fallback">QR недоступний<br>див. URL нижче</div>'
    html_text = f"""<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Zugspitze Reintal: аварійний лист</title>
  <style>
    html, body {{ margin: 0; padding: 0; background: #f8fafc; color: #111827; font-family: Arial, sans-serif; }}
    body {{ padding: 18px; }}
    .sheet {{ max-width: 980px; margin: 0 auto; background: #fff; border: 1px solid #cbd5e1; padding: 18px; box-sizing: border-box; }}
    h1 {{ margin: 0 0 4px; font-size: 22px; }}
    h2 {{ margin: 16px 0 6px; font-size: 15px; border-bottom: 1px solid #cbd5e1; padding-bottom: 3px; }}
    p {{ margin: 5px 0; }}
    .top {{ display: grid; grid-template-columns: 1fr 150px; gap: 16px; align-items: start; }}
    .qr {{ width: 150px; height: 150px; image-rendering: pixelated; }}
    .qr-fallback {{ width: 150px; height: 150px; display: grid; place-items: center; text-align: center; border: 1px solid #cbd5e1; }}
    .emergency {{ display: grid; grid-template-columns: 120px 1fr; gap: 10px; align-items: center; margin-top: 8px; }}
    .number {{ font-size: 42px; font-weight: 900; color: #991b1b; border: 2px solid #991b1b; border-radius: 8px; text-align: center; padding: 8px 0; }}
    ul {{ margin: 5px 0 0; padding-left: 18px; }}
    li {{ margin: 3px 0; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 6px; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 5px 6px; vertical-align: top; }}
    th {{ background: #f1f5f9; text-align: left; }}
    .cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
    .warn {{ border-left: 5px solid #d97706; background: #fffbeb; padding: 8px 10px; }}
    .danger {{ border-left: 5px solid #dc2626; background: #fff7ed; padding: 8px 10px; }}
    .small {{ font-size: 11px; color: #334155; overflow-wrap: anywhere; }}
    @page {{ size: A4; margin: 10mm; }}
    @media print {{
      body {{ background: #fff; padding: 0; }}
      .sheet {{ border: 0; padding: 0; max-width: none; }}
      h2 {{ break-after: avoid; }}
      table {{ break-inside: avoid; }}
      .no-print {{ display: none; }}
    }}
  </style>
</head>
<body>
  <main class="sheet">
    <section class="top">
      <div>
        <h1>Zugspitze Reintal: аварійний лист</h1>
        <p><b>Перевірено:</b> {SOURCE_CHECK_DATE}</p>
        <p><b>Карта:</b> <span class="small">{html.escape(PUBLIC_MAP_URL)}</span></p>
        <p><b>Основний маршрут:</b> Kainzenbad → Skistadion → Partnachklamm → Partnachalm / Hoher Weg → Bockhütte → Reintalangerhütte → Knorrhütte → Sonnalpin → Zugspitze.</p>
      </div>
      <div>{qr_html}</div>
    </section>

    <section class="emergency">
      <div class="number">112</div>
      <div>
        <b>Екстрений номер у Німеччині та Австрії.</b><br>
        Сказати: маршрут Zugspitze/Reintal, найближча точка, координати з GPS/popup, стан людини, погода, кількість людей.
      </div>
    </section>

    <div class="cols">
      <section>
        <h2>Перед виходом</h2>
        <ul>
{html_items(PRE_DEPARTURE_CHECKS)}
        </ul>
      </section>
      <section>
        <h2>iPhone / офлайн</h2>
        <ul>
{html_items(IPHONE_OFFLINE_STEPS)}
        </ul>
      </section>
    </div>

    <section>
      <h2>Sonnalpin: рішення</h2>
      <div class="cols">
        <div class="warn">
          <b>Йти фінал тільки якщо:</b>
          <ul>
{html_items(SONNALPIN_DECISION["go"])}
          </ul>
        </div>
        <div class="danger">
          <b>Брати Bahn, не йти далі якщо:</b>
          <ul>
{html_items(SONNALPIN_DECISION["stop"])}
          </ul>
        </div>
      </div>
    </section>

    <section>
      <h2>Точки рішення</h2>
      <table>
        <thead><tr><th>ID</th><th>Точка</th><th>Координати</th><th>Що вирішити</th></tr></thead>
        <tbody>
{point_rows(DECISION_POINTS)}
        </tbody>
      </table>
    </section>

    <section>
      <h2>Аварійне / транспорт / вода</h2>
      <table>
        <thead><tr><th>ID</th><th>Точка</th><th>Координати</th><th>Примітка</th></tr></thead>
        <tbody>
{point_rows(EMERGENCY + WATER_SOURCES[:6] + TRANSPORT[:5])}
        </tbody>
      </table>
    </section>

    <section>
      <h2>Спуски</h2>
      <table>
        <thead><tr><th>Варіант</th><th>Статус</th><th>Примітка</th></tr></thead>
        <tbody>
{descent_rows(descent_options)}
        </tbody>
      </table>
    </section>

    <section>
      <h2>Офіційні джерела для перевірки</h2>
      <ul>
{html_source_links(SAFETY_LINKS)}
      </ul>
      <p class="small">Файли резерву: zugspitze_reintal_corrected_route.gpx, zugspitze_descent_options.gpx, zugspitze_descent_options.kml.</p>
    </section>
  </main>
</body>
</html>
"""
    OUT_PRINT.write_text(html_text, encoding="utf-8")


def write_offline_readme():
    text = f"""Zugspitze Reintal offline pack
Перевірено: {SOURCE_CHECK_DATE}

Як відкрити як файл:
1. Розпакуй ZIP у звичайну папку.
2. Відкрий index.html у браузері.
3. Карта, маршрути, POI, шари, GPS-кнопка і popup працюють без CDN.
4. Супутник онлайн працює тільки з інтернетом.
5. Для походу імпортуй GPX у навігатор, не покладайся тільки на HTML.

Основні файли:
- index.html - основна карта.
- print.html - аварійний лист A4 з QR, SOS, координатами і рішенням Sonnalpin.
- zugspitze_reintal_corrected_route.gpx - основний маршрут.
- zugspitze_descent_options.gpx - варіанти спусків.
- zugspitze_descent_options.kml - спуски для KML.
- zugspitze_reintal_corrected_map.kml - основний маршрут для KML.

iPhone:
- Завантажити ZIP через GitHub Pages або GitHub.
- Розпакувати у Files.
- Відкрити index.html.
- GPX окремо імпортувати в Organic Maps / Mapy.cz / Garmin.

Публічна карта:
{PUBLIC_MAP_URL}
"""
    OUT_OFFLINE_README.write_text(text, encoding="utf-8")


def write_offline_zip():
    files = [
        OUT_INDEX,
        OUT_HTML,
        OUT_PRINT,
        OUT_GPX,
        OUT_KML,
        OUT_DESCENT_GPX,
        OUT_DESCENT_KML,
        OUT_JSON,
        OUT_OFFLINE_README,
    ]
    with zipfile.ZipFile(OUT_OFFLINE_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file_path in files:
            if file_path.exists():
                archive.write(file_path, arcname=file_path.name)


def main():
    original_points = load_source_gpx_points()
    closed_points = parse_kml_linestring_by_name("Closed original segment")
    if not closed_points:
        raise RuntimeError("Closed original segment not found in source KML")

    detour_points, detour_check_points, used_way_summary = build_osm_detour()
    corrected_points = replace_detour_in_track(original_points, detour_points)
    corrected_points = replace_start_connector(corrected_points)
    segments = split_route_segments(corrected_points)
    descent_options = build_descent_options(corrected_points)

    write_json(original_points, corrected_points, detour_points, detour_check_points, closed_points, used_way_summary, descent_options)
    write_gpx(corrected_points)
    write_kml(segments, closed_points, detour_check_points)
    write_descent_gpx(descent_options)
    write_descent_kml(descent_options)
    write_html(original_points, corrected_points, segments, detour_points, detour_check_points, closed_points, used_way_summary, descent_options)
    write_print_html(descent_options)
    write_offline_readme()
    write_offline_zip()

    print(f"Wrote {OUT_HTML.name}")
    print(f"Wrote {OUT_INDEX.name}")
    print(f"Wrote {OUT_PRINT.name}")
    print(f"Wrote {OUT_OFFLINE_ZIP.name}")
    print(f"Wrote {OUT_JSON.name}")
    print(f"Wrote {OUT_GPX.name}")
    print(f"Wrote {OUT_KML.name}")
    print(f"Wrote {OUT_DESCENT_GPX.name}")
    print(f"Wrote {OUT_DESCENT_KML.name}")
    print(f"Detour: {len(detour_points)} points, {polyline_distance(detour_points) / 1000:.2f} km")
    print(f"Corrected route: {len(corrected_points)} points, {polyline_distance(corrected_points) / 1000:.2f} km")


if __name__ == "__main__":
    main()
