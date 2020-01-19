
# mensa_aachen.py

Fetch and parse Studierendenwerk Aachen's canteen menue

This Python module allows to fetch and parse the current week's menue of the university canteens in Aachen from the Studierendenwerk Aachen's website.
The module is build on top of the popular libraries *Requests* and *Beautifulsoup4*.

Typical usage:

```python
import mensa_aachen
meals = mensa_aachen.get_meals(mensa_aachen.Canteens.MENSA_ACADEMICA)
```
Which will yield a result in a form like
```python
{
    datetime.date(2020, 1, 13): [
        Meal(menu_category='Tellergericht',
             main_component=MealComponent(title='Tom Kha Gai', flags=[]),
             aux_components=[
                MealComponent(title='Kokosmilch, Hähnchen',
                             flags=[<Flags.GLUTEN: 'A'>,
                                    <Flags.SOJABOHNEN: 'G'>,
                                    <Flags.WEIZEN: 'A1'>]),
                MealComponent(title='Fladenbrot',
                              flags=[<Flags.GLUTEN: 'A'>,
                                     <Flags.SESAMSAMEN: 'K'>,
                                     <Flags.WEIZEN: 'A1'>])],
             meat=<MeatType.GEFLUEGEL: 2>,
             price=Decimal('1.80'),
             nutritional_values=NutritionalValues(caloric_val=2050.0, fat=20.2, carbs=44.0, protein=29.3)),
        Meal(…),
        …],
    datetime.date(2020, 1, 13): […],
    …
}
```

The types `Meal`, `MealComponent`, and `NutritionalValues`, used in the result, are NamedTuples.
`Flags` and `MeatType` are Enums.
The `value` of each member of `Flags` corresponds to the abbreviation used in the menue. 
For more information about the fields and available enum options, please take a look at the module's source code.
