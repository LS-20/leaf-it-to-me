"""Diet rule table: must pass 100%. Hidden animal ingredients fail closed."""
import pytest

from remix import catalog as C
from remix.swap import needs_swap

ANIMAL = ["beef", "chicken", "pork", "bacon", "shrimp", "anchovy", "gelatin", "lard",
          "fish_sauce", "oyster_sauce", "worcestershire_sauce", "chicken_broth",
          "parmesan_cheese", "romano_cheese"]
VEGETARIAN = ["milk", "butter", "ghee", "egg", "honey", "yogurt", "cream", "paneer"]
VEGAN = ["tofu", "chickpea", "lentil", "onion", "tomato", "coconut_milk",
         "soy_milk", "peanut_butter", "eggplant", "butternut_squash", "soy_sauce"]
CHECK = ["cheddar_cheese", "mozzarella_cheese", "red_wine", "pasta", "bread",
         "marshmallow", "chocolate", "enchilada_sauce", "taco_seasoning",
         "cream_of_mushroom_soup", "egg_noodle"]


@pytest.mark.parametrize("name", ANIMAL)
def test_animal(name):
    assert C.diet_status(name) == C.ANIMAL


@pytest.mark.parametrize("name", VEGETARIAN)
def test_vegetarian(name):
    assert C.diet_status(name) == C.VEGETARIAN


@pytest.mark.parametrize("name", VEGAN)
def test_vegan(name):
    assert C.diet_status(name) == C.VEGAN


@pytest.mark.parametrize("name", CHECK)
def test_uncertain_fails_closed(name):
    assert C.diet_status(name) == C.CHECK


def test_every_candidate_is_vegan():
    for role, cands in C.CANDIDATES.items():
        for c in cands:
            assert C.diet_status(c) == C.VEGAN, (role, c)


@pytest.mark.parametrize("mode,name,expected", [
    ("vegan", "butter", True), ("vegan", "cheddar_cheese", True),
    ("vegetarian", "butter", False), ("vegetarian", "parmesan_cheese", True),
    ("vegetarian", "chicken", True), ("flexitarian", "chicken", False),
    ("flexitarian", "beef", True), ("vegan", "tofu", False),
])
def test_needs_swap(mode, name, expected):
    assert needs_swap(name, mode) is expected


def test_check_label_by_mode():
    assert C.check_concerns("pasta", "vegan")
    assert not C.check_concerns("pasta", "vegetarian")
    assert C.check_concerns("red_wine", "vegetarian")  # fining agents
    assert not C.check_concerns("red_wine", "flexitarian")
