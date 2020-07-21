### diet_planner.py - Contains methods and functions for mom's diet app

import numpy as np
import pandas as pd
from datetime import date, time, timedelta, datetime
import pint
import sys
import os
import glob
import io
import re

food_categories = ['dairy', 'processed', 'grain', 'fruit']
meal_categories = ['breakfast', 'lunch', 'dinner', 'snack']
ingredient_columns = ['quantity', 'units', 'food']
meal_columns = ['filename', 'date', 'category']
diet_columns = ['allowed', 'restricted', 'banned']
recipe_labels = {
    'name': 'Name: ',
    'servings': '\n\nServings: ',
    'ingredients': '\n\nIngredients:\n',
    'instructions': '\n\nInstructions:\n'
                }
defaults = {
    'name': "",
    'servings': 0,
    'ingredients': {},
    'instructions': "",
    'date': date.today(),
    'category': 'snack'
}

saved_diet = 'tracker.csv'
saved_recipes = 'Recipes/'
saved_meals = 'saved_meals.csv'

units = pint.UnitRegistry()

# Add context to convert volume to weight/mass and vice versa
density = (8*units.oz).to_base_units()/(1*units.cup).to_base_units()
ctx = pint.Context('kitchen')
ctx.add_transformation('[volume]', '[mass]',
                     lambda units, x: x.to_base_units()*density)
ctx.add_transformation('[mass]', '[volume]',
                     lambda units, x: x.to_base_units()/density)
units.add_context(ctx)
units.enable_contexts('kitchen')

measure_unit = units.g

def dict_to_pandas(foods):
    """ Converts a food:amount dictionary to a pandas dataframe """
    data = [[value.magnitude, value.units, key] for key, value in foods.items()]
    df = pd.DataFrame(data, columns=ingredient_columns)
    return df

def calc_foods(meals):
    """ Sum of food amounts for list of meals """
    foods = {}
    for meal in meals:
        # Add up foods
        for food_name in meal.ingredients:
            if food_name in foods:
                u = foods[food_name].units
                foods[food_name] += meal.ingredients[food_name].to(u)
            else:
                foods[food_name] = meal.ingredients[food_name]
    
    return foods

def check_foods(foods, diet):
    """
    Checks the dictionary of foods passed in for diet compliance
    Returns whether the food is diet compliant, followed by the percentage of restricted foods
    """
    restricted_tally = 0 * measure_unit # common units
    other_tally = 0 * measure_unit
    allowed = True
    for food_name in foods:
        if food_name in diet['banned']:
            allowed = False
            restricted_tally += foods[food_name].to(measure_unit)
        elif food_name in diet['restricted']:
            restricted_tally += foods[food_name].to(measure_unit) # add amt to counter
        else: # for now, just assume everything not listed is fine
            other_tally += foods[food_name].to(measure_unit)

    # No restricted foods
    if restricted_tally == 0:
        return allowed, 0

    restricted_amt = (restricted_tally/(restricted_tally+other_tally)).magnitude
    return restricted_amt <= 0.2, restricted_amt

def find_week_start(d=date.today(), week='this'):
    ''' Finds the first day of the given week as a date object '''
    if week=='this':
        day = d.weekday()
        return d-timedelta(days=day)
    elif week=='next':
        day = d.weekday()
        return d+timedelta(days=7-day)
    else:
        raise ValueError("Invalid week string")

### Food class
class Food:
    def __init__(self, name, category, special=None):
        self.name = name.lower()
        self.category = category
        self.special = special
    
    def __eq__(self, other):
        return self.name==other.name
    
    def __str__(self):
        return f"{self.name}, category: {self.category}"

### Recipe class
class Recipe:
    
    def __init__(self, filename, name="", servings=0, ingredients={}, instructions="", recipe_dir=saved_recipes):
        """ Constructor for the Recipe class """
        self.filename = recipe_dir+filename
        self.name = name
        self.ingredients = ingredients
        self.instructions = instructions
        self.servings = servings
        self.percent = 0
        self.accept = True
        
        if os.path.exists(self.filename):
            self.set_file()
        else:
            self.to_file()
    
    def __str__(self):
        return f"Recipe: {self.name}"
    
    def __eq__(self, other):
        return self.filename == other.filename
    
    def __repr__(self):
        return str(self)
    
    def __hash__(self):
        return len(self.name) % 31 + len(self.ingredients) % 31 + self.servings*31 % 7
    
    def to_file(self):
        """ Saves a Recipe object to file """
        filestring = ""
        # Loop through attributes
        for var,label in recipe_labels.items():
            filestring += label
            attr = getattr(self, var)
            
            # Ingredients to csv format
            if var=='ingredients':
                df = dict_to_pandas(attr)
                s = io.StringIO()
                df.to_csv(s, index=False, header=False)
                attr = s.getvalue()
                attr = attr[:-1] # Take off extra \n
            
            filestring += str(attr)
        
        # Write file
        f = open(self.filename, 'w')
        f.write(filestring)
        f.close()
    
    def set_file(self):
        """ Sets a recipe's options to match a filename """
        with open(self.filename, 'r') as f:
            filestring = f.read()
        
        # Filter relevant values of file
        regex = "("+"|".join(recipe_labels.values())+")"
        file_list = re.split(regex, filestring)
        file_list = list(filter(None, file_list)) # get rid of '' @ beginning
        
        # Process values
        for var,label in recipe_labels.items():
            # Get value of variable
            if file_list.index(label)+1==len(file_list) or file_list[file_list.index(label)+1] in recipe_labels.values():
                setattr(self, var, defaults[var])
                continue
            value = file_list[file_list.index(label)+1]
            # Parse servings
            if var=='servings':
                value = float(value)
                continue
            # Parse ingredients
            if var=='ingredients':
                s = io.StringIO(value)
                data = pd.read_csv(s, header=None, names=ingredient_columns)
                value = {}
                for i in range(len(data.food)):
                    value[data.food[i].lower()] = data.quantity[i]*units(data.units[i])
            
            # Set class variable
            setattr(self, var, value)
    
    @staticmethod
    def from_file(filename):
        """ Returns a new Recipe with options from filename """
        r = Recipe(filename)
        return r
        

### Meal Class
class Meal(Recipe):
    
    def __init__(self, filename, name="", m_date=date.today(), category="snack", servings=0, ingredients={},
                 instructions="", recipe_dir=saved_recipes):
        """ Initializes the Meal class """
        if not os.path.exists(recipe_dir+filename):
            raise ValueError(f"Recipe file not found: {filename}")
        super().__init__(filename, name, servings, ingredients, instructions)
        if type(m_date) is not date:
            raise ValueError(f"Invalid date: {m_date}")
        self.date = m_date
        if category.lower() not in meal_categories:
            raise ValueError(f"Invalid category: {category}")
        self.category = category.lower()
    
    def __eq__(self, other):
        return self.date==other.date and self.filename==other.filename and self.category==other.category
    
    def __lt__(self, other):
        return self.date < other.date
    
    def __le__(self, other):
        return self.date <= other.date
    
    def __str__(self):
        return f"Meal: {self.name}, date: {self.date}, category: {self.category}"
    
    def recipe(self):
        """ Returns the Recipe object corresponding to the meal """
        file = os.path.basename(self.filename)
        #return Recipe(file, self.name, self.servings, self.ingredients, self.instructions)
        return super().from_file(file)
    
    def copy(self):
        file = os.path.basename(self.filename)
        return Meal(file, m_date=self.date, category=self.category)

# Could theoretically have a separate meal file named for the recipe if there are edits?

class MealPlan:
    
    def __init__(self, diet_file=saved_diet, meal_file=saved_meals, recipe_dir=saved_recipes):
        """ Initializes a Meal Plan """
        self.meals = []
        self.recipes = []
        self.diet = {}
        
        self.diet_file = diet_file
        self.meal_file = meal_file
        self.recipe_dir = recipe_dir
        
        self.update()
    
    def update(self):
        """ Updates meals, recipes, and diet plan """
        self.read_recipes()
        self.read_meals()
        self.read_diet()
        self.check_recipes()
    
    def read_recipes(self):
        """ Reads all recipes from a directory and returns a list of Meal objects  """
        self.recipes = []
        if not os.path.exists(self.recipe_dir):
            os.mkdir(self.recipe_dir)
        for file in glob.glob(self.recipe_dir+"*"):
            file = os.path.basename(file)
            self.recipes.append(Recipe.from_file(file))
    
    def read_meals(self):
        """ Reads meals from saved meal file """
        self.meals = []
        if not os.path.exists(self.meal_file):
            data = pd.DataFrame(columns=meal_columns)
            data.to_csv(self.meal_file, index=False)
        else:
            data = pd.read_csv(self.meal_file)
        for i in range(len(data)):
            m_date = date.fromisoformat(data.date[i])
            self.meals.append(Meal(data.filename[i], m_date=m_date, category=data.category[i]))
    
    def read_diet(self):
        """ Reads in a diet plan from a file """
        if not os.path.exists(self.diet_file):
            data = pd.DataFrame(columns=diet_columns)
            data.to_csv(self.diet_file, index=False)
        else:
            data = pd.read_csv(self.diet_file)
            data = data.fillna('')
        for col in data.columns:
            self.diet[col] = [val for val in  data[col] if val!=""]
    
    def get_meals(self, start, days):
        """ Gets all meals between start and start + # days """
        td = timedelta(days=days)
        if len(self.meals)==0:
            return []
        meals = np.array(self.meals)
        file = os.path.basename(meals[0].filename)
        meals = meals[meals>=Meal(file, m_date=start)]
        meals = meals[meals<Meal(file, m_date=start+td)]
        return list(meals)
    
    def add_meal(self, meal):
        """ Adds a meal to the meal list """
        if type(meal) is Meal and meal not in self.meals:
            self.meals.append(meal)
            r = meal.recipe()
        self.to_file()
        self.update()
    
    def remove_meal(self, meal):
        """ Removes a meal from the meal list """
        print("remove meal called")
        if type(meal) is Meal and meal in self.meals:
            self.meals.remove(meal)
        elif type(meal) is Recipe and meal in self.recipes:
            print("removing recipe:", meal.filename)
            self.remove_recipe(meal)
        self.to_file()
        self.update()
    
    def update_meal(self, old_meal, new_meal):
        """ Updates a meal in the meal list """
        self.remove_meal(old_meal)
        self.add_meal(new_meal)
        self.to_file()
        self.update()
    
    def remove_recipe(self, recipe):
        """ Removes a recipe from the list (and the file tree) """
        if recipe in self.recipes:
            self.recipes.remove(recipe)
            os.remove(recipe.filename)
        for meal in self.meals:
            print("comparing:", meal.filename, recipe.filename)
            if meal.filename==recipe.filename:
                self.remove_meal(meal)
    
    def add_food(self, food, category):
        """ Adds a food to the diet """
        self.diet[category].append(food)
        self.to_file()
    
    def remove_food(self, food):
        """ Removes a food from the diet """
        for category in self.food_columns:
            if food in self.diet[category]:
                self.diet[category].remove(food)
        self.to_file()
    
    def to_file(self):
        """ Saves all meal info to a csv file """
        # Recipes
        for recipe in self.recipes:
            recipe.to_file()
        # Save Diet
        diet = pd.DataFrame()
        for key in self.diet:
            df = pd.DataFrame(data=self.diet[key])
            diet = pd.concat([diet,df], ignore_index=True, axis=1)
        diet = diet.fillna('')
        diet.columns = diet_columns
        diet.to_csv(self.diet_file, index=False)
        # Meals
        data = [[os.path.basename(meal.filename), meal.date, meal.category] for meal in self.meals]
        meals = pd.DataFrame(data=data, columns=meal_columns)
        meals.to_csv(self.meal_file, index=False)
    
    def check_plan(self, start, days):
        """ Checks the meal plan between start and start + days """
        meals = self.get_meals(start, days)
        foods = calc_foods(meals)
        return check_foods(foods, self.diet)
    
    def check_recipes(self):
        """ Checks recipes and meals and updates them with their percentages """
        for recipe in self.meals+self.recipes:
            foods = calc_foods([recipe])
            recipe.accept, recipe.percent = check_foods(foods, self.diet)