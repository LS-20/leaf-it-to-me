"""Hand-built ingredient facts: diet status, culinary role, footprint commodity.

Diet compliance comes ONLY from this file, never from embeddings.
Anything we cannot classify is "check" (fail closed: the UI says "check label").
"""
import re

VEGAN, VEGETARIAN, ANIMAL, CHECK = "vegan", "vegetarian", "animal", "check"

# --- Explicit diet status -------------------------------------------------
# ANIMAL = not vegetarian. VEGETARIAN = vegetarian but not vegan.
ANIMAL_ITEMS = {
    "beef", "lamb", "mutton", "goat", "veal", "venison", "pork", "bacon", "ham",
    "sausage", "chorizo", "pepperoni", "salami", "prosciutto", "pancetta",
    "chicken", "turkey", "duck", "goose", "quail",
    "fish", "salmon", "tuna", "cod", "tilapia", "trout", "sardine", "anchovy",
    "mackerel", "halibut", "shrimp", "prawn", "crab", "lobster", "scallop",
    "clam", "mussel", "oyster", "squid", "octopus", "abalone",
    "chicken_broth", "chicken_stock", "beef_broth", "beef_stock", "fish_stock",
    "cream_of_chicken_soup", "bouillon",
    "gelatin", "lard", "suet", "tallow", "fish_sauce", "oyster_sauce",
    "shrimp_paste", "worcestershire_sauce",  # contains anchovy
    "parmesan_cheese", "romano_cheese", "pecorino_cheese",  # traditional animal rennet
}
VEGETARIAN_ITEMS = {
    "milk", "cream", "heavy_cream", "sour_cream", "yogurt", "curd", "buttermilk",
    "butter", "ghee", "egg", "egg_yolk", "egg_white", "honey", "paneer",
    "condensed_milk", "evaporated_milk", "whey", "ricotta_cheese",
    "cream_cheese", "cottage_cheese", "mayonnaise",
}
# Cheeses other than the ones above: rennet may be animal -> check label.
CHECK_PATTERNS = [r"cheese$", r"_cheese", r"sauce$", r"seasoning$", r"paste$",
                  r"_mix$", r"soup", r"bread", r"cake", r"cookie", r"candy",
                  r"marshmallow", r"chocolate", r"pastry", r"sugar$", r"wine$",
                  r"beer$", r"noodle", r"pasta"]  # fresh pasta and noodles can contain egg
# Composite/processed items we have checked are normally vegan.
KNOWN_VEGAN_COMPOSITES = {
    "soy_sauce", "tomato_paste", "doubanjiang", "hoisin_sauce", "tahini",
    "garam_masala", "curry_paste", "chili_paste", "ginger_paste",
    "garlic_paste", "sriracha", "hot_sauce",
    "chaat_masala", "nutritional_yeast", "vegetable_stock",
}
ANIMAL_WORDS = re.compile(
    r"(beef|pork|chicken|turkey|lamb|bacon|ham\b|sausage|fish|shrimp|prawn|crab|"
    r"anchov|gelatin|lard|milk|cream|butter|cheese|egg|honey|whey|casein)"
)
PLANT_EXCEPTIONS = {"coconut_milk", "coconut_cream", "soy_milk", "oat_milk",
                    "almond_milk", "rice_milk", "peanut_butter", "almond_butter",
                    "cocoa_butter", "butternut_squash", "butter_bean",
                    "eggplant", "cream_of_tartar"}


# Processed items whose usual hidden ingredients are egg or dairy (fine for vegetarians).
EGG_DAIRY_ONLY = re.compile(r"(pasta|noodle|bread|cake|cookie|pastry|chocolate)")


def check_concerns(name: str, mode: str) -> bool:
    """For a CHECK item: could it break this diet? (Used only for warnings.)"""
    if mode == "flexitarian":
        return False
    if mode == "vegetarian" and EGG_DAIRY_ONLY.search(name) and not ANIMAL_WORDS.search(name):
        return False
    return True


def diet_status(name: str) -> str:
    if name in ANIMAL_ITEMS:
        return ANIMAL
    if name in VEGETARIAN_ITEMS:
        return VEGETARIAN
    if name in PLANT_EXCEPTIONS or name in KNOWN_VEGAN_COMPOSITES:
        return VEGAN
    if ANIMAL_WORDS.search(name):
        return CHECK  # mentions an animal product but not in our table
    if any(re.search(p, name) for p in CHECK_PATTERNS):
        return CHECK  # processed item: may hide animal ingredients
    return VEGAN  # single plant ingredient


ALLOWED = {
    "vegan": {VEGAN},
    "vegetarian": {VEGAN, VEGETARIAN},
    "flexitarian": {VEGAN, VEGETARIAN, ANIMAL},
}
RUMINANT = {"beef", "lamb", "mutton", "goat", "veal", "venison",
            "beef_broth", "beef_stock"}

# --- Culinary role (decides which replacements are allowed) ---------------
ROLE = {}
for n in ["beef", "lamb", "mutton", "goat", "veal", "venison", "pork", "bacon",
          "ham", "sausage", "chorizo", "chicken", "turkey", "duck"]:
    ROLE[n] = "meat"
for n in ["fish", "salmon", "tuna", "cod", "tilapia", "trout", "shrimp", "prawn",
          "crab", "scallop", "squid"]:
    ROLE[n] = "seafood"
for n in ["chicken_broth", "chicken_stock", "beef_broth", "beef_stock",
          "fish_stock", "bouillon"]:
    ROLE[n] = "broth"
ROLE.update({
    "butter": "fat", "ghee": "fat", "lard": "fat",
    "cream": "cream", "heavy_cream": "cream", "sour_cream": "cream",
    "yogurt": "yogurt", "curd": "yogurt",
    "milk": "milk", "buttermilk": "milk",
    "egg": "egg",
    "honey": "sweetener",
    "gelatin": "gelling",
    "fish_sauce": "umami_sauce", "oyster_sauce": "umami_sauce",
    "worcestershire_sauce": "umami_sauce", "anchovy": "umami_sauce",
    "paneer": "cheese",
})


def role_of(name: str):
    if name in ROLE:
        return ROLE[name]
    if name.endswith("cheese"):
        return "cheese"
    return None


PROTEINS = ["tofu", "tempeh", "chickpea", "lentil", "black_bean", "kidney_bean",
            "pinto_bean", "edamame", "mushroom", "jackfruit", "eggplant",
            "cauliflower", "chana_dal"]
CANDIDATES = {
    "meat": PROTEINS,
    "seafood": PROTEINS,
    "broth": ["vegetable_stock"],
    "fat": ["coconut_oil", "olive_oil", "avocado_oil", "vegetable_oil"],
    "cream": ["coconut_cream", "coconut_milk", "cashew"],
    "yogurt": ["coconut_cream", "cashew"],
    "milk": ["oat_milk", "soy_milk", "almond_milk"],
    "cheese": ["nutritional_yeast", "cashew", "tofu"],
    "egg": ["tofu", "chickpea", "flaxseed"],
    "sweetener": ["maple_syrup", "agave_nectar"],
    "gelling": ["agar"],
    "umami_sauce": ["soy_sauce", "miso", "mushroom"],
}

# --- Footprint commodity (Poore & Nemecek 2018 via Our World in Data) -----
# (commodity, is_proxy). is_proxy=True means "closest category, not exact".
COMMODITY = {}


def _m(commodity, names, proxy=False):
    for n in names:
        COMMODITY[n] = (commodity, proxy)


_m("Beef (beef herd)", ["beef", "veal", "beef_broth", "beef_stock"])
_m("Lamb & Mutton", ["lamb", "mutton", "goat"], )
_m("Pig Meat", ["pork", "bacon", "ham", "sausage", "chorizo", "lard"])
_m("Poultry Meat", ["chicken", "turkey", "duck"])
_m("Poultry Meat", ["chicken_broth", "chicken_stock"], proxy=True)
_m("Fish (farmed)", ["fish", "salmon", "tilapia", "trout", "cod"])
_m("Prawns (farmed)", ["shrimp", "prawn"])
_m("Cheese", ["cheese", "paneer", "parmesan_cheese", "mozzarella_cheese",
              "cheddar_cheese", "feta_cheese", "goat_cheese", "ricotta_cheese",
              "romano_cheese", "provolone_cheese", "cream_cheese"])
_m("Milk", ["milk", "yogurt", "curd", "buttermilk"])
_m("Eggs", ["egg", "egg_yolk", "egg_white"])
_m("Tofu", ["tofu"])
_m("Tofu", ["tempeh", "edamame"], proxy=True)
_m("Soy milk", ["soy_milk"])
_m("Soy milk", ["oat_milk", "almond_milk"], proxy=True)
_m("Other Pulses", ["lentil", "chickpea", "black_bean", "kidney_bean",
                    "pinto_bean", "chana_dal", "urad_dal", "masoor_dal",
                    "split_pea", "navy_bean", "white_bean"])
_m("Peas", ["pea", "green_pea"])
_m("Groundnuts", ["peanut", "peanut_butter"])
_m("Nuts", ["cashew", "almond", "walnut", "pistachio", "hazelnut", "pecan"])
_m("Rice", ["rice", "basmati_rice", "brown_rice", "jasmine_rice"])
_m("Wheat & Rye", ["flour", "pasta", "bread", "tortilla", "naan", "noodle",
                   "couscous", "spaghetti"])
_m("Maize", ["corn", "cornmeal", "corn_tortilla", "cornstarch"])
_m("Oatmeal", ["oat", "oatmeal"])
_m("Tomatoes", ["tomato", "cherry_tomato", "tomato_paste", "tomato_sauce"])
_m("Onions & Leeks", ["onion", "red_onion", "leek", "scallion", "shallot", "garlic"])
_m("Potatoes", ["potato"])
_m("Root Vegetables", ["carrot", "beet", "turnip", "parsnip", "ginger", "radish"])
_m("Brassicas", ["cabbage", "cauliflower", "broccoli", "kale", "brussels_sprout"])
_m("Other Vegetables", ["mushroom", "eggplant", "bell_pepper", "celery", "lettuce",
                        "spinach", "zucchini", "cucumber", "green_bean",
                        "okra", "vegetable_stock", "chili_pepper", "jalapeno"])
_m("Other Fruit", ["jackfruit", "avocado", "mango", "pineapple"])
_m("Citrus Fruit", ["lime", "lemon", "orange"])
_m("Cane Sugar", ["sugar", "brown_sugar"])
_m("Wine", ["wine", "red_wine", "white_wine"])
_m("Dark Chocolate", ["dark_chocolate", "chocolate"])
_m("Coffee", ["coffee"])

# Nutrients most often lost when an ingredient of this role is removed.
NUTRIENT_FLAGS = {
    "meat": ["vitamin B12", "iron", "zinc"],
    "seafood": ["omega-3", "iodine", "vitamin B12"],
    "broth": [],
    "fat": [],
    "cream": ["calcium"],
    "yogurt": ["calcium", "vitamin B12"],
    "milk": ["calcium", "vitamin B12", "vitamin D", "iodine"],
    "cheese": ["calcium", "vitamin B12"],
    "egg": ["vitamin B12", "choline"],
    "sweetener": [],
    "gelling": [],
    "umami_sauce": [],
}
NUTRIENT_TIPS = {
    "vitamin B12": "plants don't supply B12: use fortified foods or a supplement",
    "iron": "plant iron absorbs better with vitamin C (tomato, lime, peppers)",
    "zinc": "pulses, seeds and whole grains supply zinc",
    "omega-3": "walnuts, flax and chia give ALA omega-3 (not EPA/DHA)",
    "iodine": "iodised salt or seaweed",
    "calcium": "look for calcium-set tofu or fortified plant milk",
    "vitamin D": "fortified plant milk or sunlight",
    "choline": "soy, beans and broccoli supply some choline",
}


# --- Display groups (only for coloring the flavor graph) -------------------
GROUPS = ["protein", "dairy", "spice", "vegetable", "grain", "sauce", "fat", "fruit"]
_PROTEIN_WORDS = re.compile(r"(bean|lentil|chickpea|dal\b|_dal|tofu|tempeh|edamame|seitan)")
_FAT_WORDS = re.compile(r"(oil$|^butter$|ghee|lard|margarine|shortening)")
_DAIRY_WORDS = re.compile(r"(milk|cream|cheese|yogurt|curd|paneer|^egg)")
_GRAIN_WORDS = re.compile(r"(rice|pasta|spaghetti|noodle|tortilla|bread|flour|oat|quinoa|couscous|naan|pita|bun$|cornmeal|cornstarch)")
_SAUCE_WORDS = re.compile(r"(sauce|paste|stock|broth|vinegar|wine|doubanjiang|miso|ketchup|mustard|mayonnaise|salsa|gochujang|mirin|sake|syrup|honey|sugar)")
_SPICE_WORDS = re.compile(r"(masala|powder|seed|peppercorn|_leaf|leaves|cumin|turmeric|paprika|cinnamon|clove|cardamom|basil|oregano|thyme|parsley|dill|coriander|cilantro|chili|black_pepper|saffron|nutmeg|bay|rosemary|sage|mint|ginger|anise|amchur|asafoetida|ajwain|methi|salt)")
_FRUIT_WORDS = re.compile(r"(lime|lemon|orange|mango|jackfruit|avocado|apple|pear|coconut|cashew|almond|peanut|walnut|pistachio|pecan|hazelnut|raisin|date|berry|grape|banana|pineapple|tamarind|nut$)")


def group_of(name: str) -> str:
    if ROLE.get(name) in ("meat", "seafood") or name in PROTEINS or _PROTEIN_WORDS.search(name):
        return "protein"
    if _FAT_WORDS.search(name):
        return "fat"
    if _DAIRY_WORDS.search(name) and not name.startswith("coconut"):
        return "dairy"
    if _GRAIN_WORDS.search(name):
        return "grain"
    if _SAUCE_WORDS.search(name):
        return "sauce"
    if _SPICE_WORDS.search(name):
        return "spice"
    if _FRUIT_WORDS.search(name):
        return "fruit"
    return "vegetable"
