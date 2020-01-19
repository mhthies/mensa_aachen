#!/usr/bin/env python3

"""
Library to fetch and parse the menu of Studierendenwerk Aachen's canteens.
"""
import datetime
import enum
import re
from typing import Dict, List, Optional, NamedTuple
from decimal import Decimal
import logging

import requests
from bs4 import BeautifulSoup  # type: ignore
import bs4  # type: ignore

logger = logging.getLogger(__name__)


class Canteens(enum.Enum):
    MENSA_ACADEMICA = "academica"
    MENSA_AHORNSTRASSE = "ahornstrasse"
    BISTRO_TEMPLERGRABEN = "templergraben"
    MENSA_BAYERNALLEE = "bayernallee"
    MENSA_EUPENER_STRASSE = "eupenerstrasse"
    MENSA_GOETHESTRASSE = "goethestrasse"
    MENSA_SUEDPARK = "suedpark"
    MENSA_VITA = "vita"
    MENSA_JUELICH = "juelich"


class MeatType(enum.Enum):
    """
    Enum of types of meals with respect to contained meats
    """
    RIND = 0
    SCHWEIN = 1
    GEFLUEGEL = 2
    VEGETARIAN = 3
    VEGAN = 4

    @classmethod
    def from_class_list(cls, class_list: List[str]):
        for key, value in MEAT_TYPE_CSS_CLASSES.items():
            if key in class_list:
                return value


# Meat type can most easily be parsed by checking for the CSS classes
MEAT_TYPE_CSS_CLASSES = {
    'vegan': MeatType.VEGAN,
    'OLV': MeatType.VEGETARIAN,
    'Rind': MeatType.RIND,
    'Schwein': MeatType.SCHWEIN,
    'Geflügel': MeatType.GEFLUEGEL,
}


class Flags(enum.Enum):
    """
    Enum of available (ingredient) flags of Studierendenwerk Aachen
    """
    FARBSTOFF = "1"
    KONSERVIERUNGSSTOFF = "2"
    ANTIOXIDATIONSMITTEL = "3"
    GESCHMACKSVERSTAERKER = "4"
    GESCHWEFELT = "5"
    GESCHWAERZT = "6"
    GEWACHST = "7"
    PHOSPHAT = "8"
    SUESSUNGSMITTEL = "9"
    PHENYLALANINQUELLE = "10"
    GLUTEN = "A"
    WEIZEN = "A1"
    ROGGEN = "A2"
    GERSTE = "A3"
    HAFER = "A4"
    DINKEL = "A5"
    SELLERIE = "B"
    KREBSTIERE = "C"
    EIER = "D"
    FISCHE = "E"
    ERDNUESSE = "F"
    SOJABOHNEN = "G"
    MILCH = "H"
    SCHALENFRUECHTE = "I"
    MANDELN = "I1"
    HASELNUESSE = "I2"
    WALNUESSE = "I3"
    KASCHUNUESSE = "I4"
    PECANNUESSE = "I5"
    PARANUESSE = "I6"
    PISTAZIEN = "I7"
    MACADAMIANUESSE = "I8"
    SENF = "J"
    SESAMSAMEN = "K"
    SCHWEFELDIOXID_ODER_SULFITE = "L"
    LUPINEN = "M"
    WEICHTIERE = "N"


class MealComponent(NamedTuple):
    title: str
    flags: List[Flags]


class NutritionalValues(NamedTuple):
    caloric_val: Optional[float]  # in kilojoules
    fat: Optional[float]  # in g
    carbs: Optional[float]  # in g
    protein: Optional[float]  # in g


class Meal(NamedTuple):
    """
    A single meal in a canteen's menue.

    The meal comprises a category (such as 'Tellergericht'), a main component (the first named component of the meal, a
    list of auxiliary components, the meat/vegetarian flag, the price (without student discount) and the nutritional
    values of the total meal (as far as provided)
    """
    menu_category: str
    main_component: MealComponent
    aux_components: List[MealComponent]
    meat: MeatType
    price: Optional[Decimal]
    nutritional_values: NutritionalValues


def get_meals(canteen: Canteens) -> Dict[datetime.date, List[Meal]]:
    """
    Fetch and parse the meals of every day of the current week in the specified canteen

    This function simply plugs the pieces together: `fetch_menue()` to get the menue HTML document, *BeautifulSoup* to
    parse the HTML, and `parse_meals()` to get the list of meals from the parse HTML tree.

    :return: A dict, mapping dates to lists of meals
    """
    menue = fetch_menue(canteen)
    soup = BeautifulSoup(menue, features="lxml")
    return parse_meals(soup)


def fetch_menue(canteen: Canteens) -> str:
    """
    Get the current week's menue of the specified canteen as HTML document
    :raises requests.exceptions.HTTPError: If one occured
    """
    url = "https://www.studierendenwerk-aachen.de/speiseplaene/{}-w.html".format(canteen.value)

    r = requests.get(url)
    r.raise_for_status()
    return r.text


RE_PRICE = re.compile(r'([\d,]+)\s*€')


def parse_meals(soup: BeautifulSoup) -> Dict[datetime.date, List[Meal]]:
    """
    Parse all meals of the current week from a menu HTML document of one canteen, parsed with BeautifulSoup4.

    :return: A dict, mapping dates to lists of meals
    """
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())

    days: Dict[datetime.date, List[Meal]] = {}
    for weekday, weekday_offset in (('Montag', 0), ('Dienstag', 1), ('Mittwoch', 2), ('Donnerstag', 3), ('Freitag', 4)):
        date_div = soup.find(id=weekday)
        assert(isinstance(date_div, bs4.Tag))

        meals: List[Meal] = []
        for meal_row in date_div.find('table', class_='menues').find_all('td', class_='menue-wrapper'):
            meal_category = meal_row.find(class_='menue-category').string
            meal_meat = MeatType.from_class_list(meal_row.parent['class'])

            # Parse meal description
            meal_text = meal_row.find(class_='expand-nutr')
            assert(isinstance(meal_text, bs4.Tag))
            meal_components = parse_meal_components(meal_text)
            if not meal_components:
                logger.info("A meal does not contain any components.")
                continue

            # Parse price
            price_match = RE_PRICE.search(meal_row.find(class_='menue-price').string)
            meal_price = Decimal(price_match[1].replace(',', '.')) if price_match else None

            # Parse nutritional values
            nutritional_info = meal_row.find(class_='nutr-info')
            nutritional_values = parse_nutritional_values(nutritional_info)

            # Construct Meal object
            meals.append(Meal(meal_category, meal_components[0], meal_components[1:], meal_meat, meal_price,
                              nutritional_values))

        days[monday + datetime.timedelta(days=weekday_offset)] = meals

    return days


def parse_meal_components(meal_content: bs4.Tag) -> List[MealComponent]:
    """
    Split the contents of span.expand-nutr into separate menu components and their (ingredient) flags

    :param meal_content: The span.expand-nutr PageElement of a single meal
    :return: A list of meal components, each with name and list of ingredient flags
    """
    meal_components = []
    current_meal_item: Optional[MealComponent] = None
    for element in meal_content.children:
        if isinstance(element, bs4.NavigableString):
            for meal_item_name in element.split('|'):
                if not meal_item_name.strip():
                    continue
                if current_meal_item is not None:
                    meal_components.append(current_meal_item)
                current_meal_item = MealComponent(meal_item_name.strip(), [])

        elif 'class' in element.attrs and {'menue-nutr'} & set(element.attrs['class']):
            # Skip expand/"+" button
            continue

        elif element.name == "sup":
            # Skip the "Preis ohne Pfand" annotation
            if element.string.strip() == "Preis ohne Pfand":
                continue
            if current_meal_item is not None:
                for flag_id in element.string.strip().split(','):
                    try:
                        flag = Flags(flag_id)
                    except ValueError as e:
                        logger.warning(e)
                        continue
                    current_meal_item[1].append(flag)

    if current_meal_item is not None:
        meal_components.append(current_meal_item)
    return meal_components


RE_CALORIC_VAL = re.compile(r'Brennwert\s*=\s*([\d,]+)\s*kJ')
RE_FAT = re.compile(r'Fett\s*=\s*([\d,]+)\s*g')
RE_CARBS = re.compile(r'Kohlenhydrate\s*=\s*([\d,]+)\s*g')
RE_PROTEIN = re.compile(r'Eiwei.*?\s*=\s*([\d,]+)\s*g')


def parse_nutritional_values(nutr_content: Optional[bs4.Tag]) -> NutritionalValues:
    """
    Parse the contents of span.nutr-info to get the nutritional values

    :param nutr_content: The span.nutr-info PageElement of a single meal or None, if nutritional values were not found
        or could not be parsed
    """
    if nutr_content is None:
        return NutritionalValues(None, None, None, None)
    text = nutr_content.get_text()
    matches = (
        RE_CALORIC_VAL.search(text),
        RE_FAT.search(text),
        RE_CARBS.search(text),
        RE_PROTEIN.search(text),
    )
    return NutritionalValues(*(float(match[1].replace(',', '.')) if match else None
                               for match in matches))
