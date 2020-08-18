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

This module contains functions to fetch and parse the menu from the Studierendenwerk Aachen's website and some
NamedTuple and Enum definitions to represent the parsed structured menu data. Typically, the main entry point to this
module is `get_dishes()` which fetches and parses the menu data of the current week for one (specified) canteen. It
returns a dict with a list of `Dish` objects for every day.
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
    Enum of types of dishes with respect to contained meats
    """
    RIND = 0
    SCHWEIN = 1
    GEFLUEGEL = 2
    VEGETARIAN = 3
    VEGAN = 4
    FISCH = 5

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
    'Fisch': MeatType.FISCH,
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


class DishComponent(NamedTuple):
    title: str
    flags: List[Flags]


class NutritionalValues(NamedTuple):
    caloric_val: Optional[float]  # in kilojoules
    fat: Optional[float]  # in g
    carbs: Optional[float]  # in g
    protein: Optional[float]  # in g


class Dish(NamedTuple):
    """
    A single dish in a canteen's menu.

    The dish comprises a menu category (such as 'Tellergericht'), a main component (the first named component of the
    dish, a list of auxiliary components, the meat/vegetarian indication, the price (including student discount) and the
    nutritional values of the total dish (as far as provided).

    Side dishes are also Dishes, but without a price and without meat indication.
    """
    menu_category: str
    main_component: DishComponent
    aux_components: List[DishComponent]
    meat: List[MeatType]
    price: Optional[Decimal]  # includes student discount (e.g. 1.80€ instead of 3.30€ for the "Tellergericht")
    nutritional_values: NutritionalValues


class Menu(NamedTuple):
    """
    A full menu: All dishes at one day in one canteen, consisting of main dishes and side dishes
    """
    main_dishes: List[Dish]
    side_dishes: List[Dish]


def get_dishes(canteen: Canteens) -> Dict[datetime.date, Menu]:
    """
    Fetch and parse the dishes of every day of the current week in the specified canteen

    This function simply plugs the pieces together: `fetch_menu()` to get the menu HTML document, *BeautifulSoup* to
    parse the HTML, and `parse_dishes()` to get the list of dishes from the parse HTML tree.

    :return: A dict, mapping dates to lists of dishes
    """
    menu = fetch_menu(canteen)
    soup = BeautifulSoup(menu, features="lxml")
    return parse_dishes(soup)


def fetch_menu(canteen: Canteens) -> str:
    """
    Get the current week's menu of the specified canteen as HTML document
    :raises requests.exceptions.HTTPError: If one occured
    """
    url = "https://www.studierendenwerk-aachen.de/speiseplaene/{}-w.html".format(canteen.value)

    r = requests.get(url)
    r.raise_for_status()
    r.encoding = 'utf-8'
    return r.text


RE_PRICE = re.compile(r'([\d,]+)\s*€')
RE_DATE = re.compile(r'(\d\d)\.(\d\d)\.(\d\d\d\d)')


def parse_dishes(soup: BeautifulSoup) -> Dict[datetime.date, Menu]:
    """
    Parse all dishes from a menu HTML document of one canteen, parsed with BeautifulSoup4.

    :return: A dict, mapping dates to lists of dishes
    """
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())

    days: Dict[datetime.date, Menu] = {}
    for date_div in soup.find_all(class_='preventBreak'):
        assert(isinstance(date_div, bs4.Tag))
        heading = date_div.find('h3')
        if not heading:
            continue
        date_match = RE_DATE.search(heading.a.string)
        date = datetime.date(int(date_match[3]), int(date_match[2]), int(date_match[1]))

        dishes: List[Dish] = []
        for dish_row in date_div.find('table', class_='menues').find_all('td', class_='menue-wrapper'):
            dishes.extend(parse_menu_row(dish_row))
        side_dishes: List[Dish] = []
        for dish_row in date_div.find('table', class_='extras').find_all('td', class_='menue-wrapper'):
            side_dishes.extend(parse_menu_row(dish_row))

        days[date] = Menu(dishes, side_dishes)

    return days


def parse_menu_row(dish_row: bs4.Tag) -> List[Dish]:
    """
    Parse all dishes in a single menu row.

    Typically a menu row only contains only one dish with all its attributes (menu category, dish description (with
    multiple components, price, nutritional values). However, this does not hold for the side dishes: They are listed
    as multiple dishes within one row, with entangled attributes. This function finds all dishes in both cases and
    composes the correct attributes.
    """
    dish_category = dish_row.find(class_='menue-category').string
    dish_meat = MeatType.from_class_list(dish_row.parent.attrs.get('class', []))

    # Parse dish descriptions (all dishes with all components)
    # Sometimes, the dish descriptions are directly in the span.menue-desc, sometimes, they are encapsulated in a
    # span.expand-nutr
    dish_text = dish_row.find(class_='expand-nutr')
    if not dish_text:
        dish_text = dish_row.find(class_='menue-desc')
    if not dish_text:
        return []
    assert(isinstance(dish_text, bs4.Tag))
    # Each dish_row might contain multiple dish descriptions with multiple components each.
    dish_descriptions: List[List[DishComponent]] = parse_dish_components(dish_text)
    if not dish_descriptions:
        logger.info("A row does not contain any dishes.")
        return []

    # Parse price (if existing)
    dish_price = None
    price_tag = dish_row.find(class_='menue-price')
    if price_tag:
        assert(isinstance(price_tag, bs4.Tag))
        price_match = RE_PRICE.search(price_tag.string)
        if price_match:
            dish_price = Decimal(price_match[1].replace(',', '.'))

    # Parse all nutritional value information (might be multiple for, e.g. side dishes)
    nutritional_values = [parse_nutritional_values(nutr_info_tag)
                          for nutr_info_tag in dish_row.find_all(class_='nutr-info')]
    # Fill up nutritional values to get one for every dish
    nutritional_values += ([NutritionalValues(None, None, None, None)]
                           * max(0, len(dish_descriptions) - len(nutritional_values)))

    # Construct Dish objects
    return [Dish(dish_category, dish_components[0], dish_components[1:], dish_meat, dish_price, dish_nutr)
            for dish_components, dish_nutr in zip(dish_descriptions, nutritional_values)]


def parse_dish_components(dish_content: bs4.Tag) -> List[List[DishComponent]]:
    """
    Split the contents of span.expand-nutr into separate dishes with separate dish components and their (ingredient)
    flags

    A single row in the menu may contain multiple dishes (divided with span.divider tags – mainly used for the side
    dishes) and each of them may have multiple components (divided by "|").

    :param dish_content: The span.expand-nutr PageElement of a single dish
    :return: A list of dishes, each being a list of dish components
    """
    dishes = []
    current_dish = []
    current_dish_cmp: Optional[DishComponent] = None
    for element in dish_content.children:
        if isinstance(element, bs4.NavigableString):
            for dish_item_name in element.split('|'):
                if not dish_item_name.strip():
                    continue
                if current_dish_cmp is not None:
                    current_dish.append(current_dish_cmp)
                current_dish_cmp = DishComponent(dish_item_name.strip(), [])

        elif 'class' in element.attrs and {'menue-nutr', 'nutr-info'} & set(element.attrs['class']):
            # Skip expand/"+" button
            continue

        elif 'class' in element.attrs and 'seperator' in element.attrs['class']:
            if current_dish_cmp is not None:
                current_dish.append(current_dish_cmp)
                current_dish_cmp = None
            if current_dish:
                dishes.append(current_dish)
                current_dish = []

        elif element.name == "sup":
            # Skip the "Preis ohne Pfand" annotation
            if element.string.strip() == "Preis ohne Pfand":
                continue
            if current_dish_cmp is not None:
                for flag_id in element.string.strip().split(','):
                    try:
                        flag = Flags(flag_id)
                    except ValueError as e:
                        logger.warning(e)
                        continue
                    current_dish_cmp[1].append(flag)

    if current_dish_cmp is not None:
        current_dish.append(current_dish_cmp)
    if current_dish:
        dishes.append(current_dish)
    return dishes


RE_CALORIC_VAL = re.compile(r'Brennwert\s*=\s*([\d,]+)\s*kJ')
RE_FAT = re.compile(r'Fett\s*=\s*([\d,]+)\s*g')
RE_CARBS = re.compile(r'Kohlenhydrate\s*=\s*([\d,]+)\s*g')
RE_PROTEIN = re.compile(r'Eiwei.*?\s*=\s*([\d,]+)\s*g')


def parse_nutritional_values(nutr_content: Optional[bs4.Tag]) -> NutritionalValues:
    """
    Parse the contents of span.nutr-info to get the nutritional values

    :param nutr_content: The span.nutr-info PageElement of a single dish or None, if nutritional values could not be
        parsed
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
