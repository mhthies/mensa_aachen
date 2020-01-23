
# mensa_aachen.py

Fetch and parse Studierendenwerk Aachen's canteen menu

This Python module allows to fetch and parse the current week's menu of the university canteens in Aachen from the Studierendenwerk Aachen's website.
The module is build on top of the popular libraries *Requests* and *Beautifulsoup4*.

Typical usage:

```python
import mensa_aachen
dishes = mensa_aachen.get_dishes(mensa_aachen.Canteens.MENSA_ACADEMICA)
```
Which will yield a result in a form like
```python
{
    datetime.date(2020, 1, 20):
        Menu(
            main_dishes=[
                Dish(
                    menu_category='Tellergericht',
                    main_component=DishComponent(
                        title='Bulgureintopf',
                        flags=[]),
                    aux_components=[
                        DishComponent(
                            title='Kichererbsen, Gemüse',
                            flags=[<Flags.ANTIOXIDATIONSMITTEL: '3'>, <Flags.GLUTEN: 'A'>, <Flags.WEIZEN: 'A1'>])
                        ],
                    meat=[<MeatType.VEGAN: 4>, <MeatType.VEGETARIAN: 3>],
                    price=Decimal('1.80'),
                    nutritional_values=NutritionalValues(caloric_val=None, fat=None, carbs=None, protein=None)),
                Dish(
                    menu_category='Vegetarisch',
                    main_component=DishComponent(
                        title='Spätzlepfanne',
                        flags=[]),
                    aux_components=[
                        DishComponent(
                            title='Röstzwiebeln',
                            flags=[<Flags.GLUTEN: 'A'>, <Flags.SELLERIE: 'B'>, <Flags.EIER: 'D'>, <Flags.MILCH: 'H'>, <Flags.WEIZEN: 'A1'>, <Flags.DINKEL: 'A5'>]),
                        DishComponent(
                            title='Käsesauce',
                            flags=[<Flags.FARBSTOFF: '1'>, <Flags.MILCH: 'H'>])], meat=[<MeatType.VEGETARIAN: 3>],
                    price=Decimal('2.10'),
                    nutritional_values=NutritionalValues(caloric_val=3857.0, fat=44.6, carbs=97.1, protein=32.0)),
                ...],
            side_dishes=[
                Dish(
                    menu_category='Hauptbeilagen',
                    main_component=DishComponent(
                        title='Nudelreis',
                        flags=[<Flags.GLUTEN: 'A'>, <Flags.WEIZEN: 'A1'>]),
                    aux_components=[],
                    meat=[],
                    price=None,
                    nutritional_values=NutritionalValues(caloric_val=1859.0, fat=11.0, carbs=72.0, protein=12.0)),
                Dish(
                    menu_category='Nebenbeilage',
                    main_component=DishComponent(
                        title='Rosenkohl',
                        flags=[]),
                    aux_components=[],
                    meat=[],
                    price=None,
                    nutritional_values=NutritionalValues(caloric_val=502.0, fat=8.0, carbs=6.6, protein=5.5)),
                ...]
            ),
    datetime.date(2020, 1, 21):
        Menu(...),
    ...
}
```

The types `Menu`, `Dish`, `DishComponent`, and `NutritionalValues`, used in the result, are NamedTuples.
`Flags` and `MeatType` are Enums.
The `value` of each member of `Flags` corresponds to the abbreviation used in the menu. 
For more information about the fields and available enum options, please take a look at the module's source code.
