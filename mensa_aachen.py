#!/usr/bin/env python3

# Copyright 2020 by Michael Thies <mail@mhthies.de>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Library to fetch and parse the menu of Studierendenwerk Aachen's canteens.

This module contains functions to fetch and parse the menue from the Studierendenwerk Aachen's website and some
NamedTuple and Enum definitions to represent the parsed structured menue data. Typically, the main entry point to this
module is `get_meals()` which fetches and parses the menue data of the current week for one (specified) canteen. It
returns a dict with a list of `Meal` objects for every day.
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
    def from_class_list(cls, class_list: List[str]) -> List["MeatType"]:
        return [meat_type
                for css_class, meat_type in MEAT_TYPE_CSS_CLASSES.items()
                if css_class in class_list]


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
    SCHARF = "scharf"


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
    list of auxiliary components, the meat/vegetarian indication, the price (including student discount) and the
    nutritional values of the total meal (as far as provided).

    Side dishes are also Meals, but without a price and without meat indication.
    """
    menu_category: str
    main_component: MealComponent
    aux_components: List[MealComponent]
    meat: List[MeatType]
    price: Optional[Decimal]  # includes student discount (e.g. 1.80€ instead of 3.30€ for the "Tellergericht")
    nutritional_values: NutritionalValues


class Menue(NamedTuple):
    """
    A full menu: All meals at one day in one canteen, consisting of main meals and side dishes
    """
    main_meals: List[Meal]
    side_dishes: List[Meal]


def get_meals(canteen: Canteens) -> Dict[datetime.date, Menue]:
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
    r.encoding = 'utf-8'
    return r.text


RE_PRICE = re.compile(r'([\d,]+)\s*€')


def parse_meals(soup: BeautifulSoup) -> Dict[datetime.date, Menue]:
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
            meals.extend(parse_menue_row(meal_row))
        side_dishes: List[Meal] = []
        for meal_row in date_div.find('table', class_='extras').find_all('td', class_='menue-wrapper'):
            side_dishes.extend(parse_menue_row(meal_row))

        days[monday + datetime.timedelta(days=weekday_offset)] = Menue(meals, side_dishes)

    return days


def parse_menue_row(meal_row: bs4.Tag) -> List[Meal]:
    """
    Parse all meals in a single menue row.

    Typically a menue row only contains only one meal with all its attributes (menue category, meal description (with
    multiple components, price, nutritional values). However, this does not hold for the side dishes: They are listed
    as multiple meals within one row, with entangled attributes. This function finds all meals in both cases and
    composes the correct attributes.
    """
    meal_category = meal_row.find(class_='menue-category').string
    meal_meat = MeatType.from_class_list(meal_row.parent.attrs.get('class', []))

    # Parse meal descriptions (all meals with all components)
    # Sometimes, the meal descriptions are directly in the span.menu-desc, sometimes, they are encapsulated in a
    # span.expand-nutr
    meal_text = meal_row.find(class_='expand-nutr')
    if not meal_text:
        meal_text = meal_row.find(class_='menue-desc')
    if not meal_text:
        return []
    assert(isinstance(meal_text, bs4.Tag))
    # Each meal_row might contain multiple meal descriptions with multiple components each.
    meal_descriptions: List[List[MealComponent]] = parse_meal_components(meal_text)
    if not meal_descriptions:
        logger.info("A row does not contain any meals.")
        return []

    # Parse price (if existing)
    meal_price = None
    price_tag = meal_row.find(class_='menue-price')
    if price_tag:
        assert(isinstance(price_tag, bs4.Tag))
        price_match = RE_PRICE.search(price_tag.string)
        if price_match:
            meal_price = Decimal(price_match[1].replace(',', '.'))

    # Parse all nutritional value information (might be multiple for, e.g. side dishes)
    nutritional_values = [parse_nutritional_values(nutr_info_tag)
                          for nutr_info_tag in meal_row.find_all(class_='nutr-info')]
    # Fill up nutritional values to get one for every meal
    nutritional_values += ([NutritionalValues(None, None, None, None)]
                           * max(0, len(meal_descriptions) - len(nutritional_values)))

    # Construct Meal objects
    return [Meal(meal_category, meal_components[0], meal_components[1:], meal_meat, meal_price, meal_nutr)
            for meal_components, meal_nutr in zip(meal_descriptions, nutritional_values)]


def parse_meal_components(meal_content: bs4.Tag) -> List[List[MealComponent]]:
    """
    Split the contents of span.expand-nutr into separate meals with separate meal components and their (ingredient)
    flags

    A single row in the menue may contain multiple meals (divided with span.divider tags – mainly used for the side
    dishes) and each of them may have multiple components (divided by "|").

    :param meal_content: The span.expand-nutr PageElement of a single meal
    :return: A list of meals, each being a list of meal components
    """
    meals = []
    current_meal = []
    current_meal_cmp: Optional[MealComponent] = None
    for element in meal_content.children:
        if isinstance(element, bs4.NavigableString):
            for meal_item_name in element.split('|'):
                if not meal_item_name.strip():
                    continue
                if current_meal_cmp is not None:
                    current_meal.append(current_meal_cmp)
                current_meal_cmp = MealComponent(meal_item_name.strip(), [])

        elif 'class' in element.attrs and {'menue-nutr', 'nutr-info'} & set(element.attrs['class']):
            # Skip expand/"+" button
            continue

        elif 'class' in element.attrs and 'seperator' in element.attrs['class']:
            if current_meal_cmp is not None:
                current_meal.append(current_meal_cmp)
                current_meal_cmp = None
            if current_meal:
                meals.append(current_meal)
                current_meal = []

        elif element.name == "sup":
            # Skip the "Preis ohne Pfand" annotation
            if element.string.strip() == "Preis ohne Pfand":
                continue
            if current_meal_cmp is not None:
                for flag_id in element.string.strip().split(','):
                    try:
                        flag = Flags(flag_id)
                    except ValueError as e:
                        logger.warning(e)
                        continue
                    current_meal_cmp[1].append(flag)

    if current_meal_cmp is not None:
        current_meal.append(current_meal_cmp)
    if current_meal:
        meals.append(current_meal)
    return meals


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
    text = nutr_content.get_text()
    matches = (
        RE_CALORIC_VAL.search(text),
        RE_FAT.search(text),
        RE_CARBS.search(text),
        RE_PROTEIN.search(text),
    )
    return NutritionalValues(*(float(match[1].replace(',', '.')) if match else None
                               for match in matches))
