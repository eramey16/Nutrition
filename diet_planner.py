import numpy as np
import pandas as pd
from datetime import date, time, timedelta, datetime
import pint
import sys
import os
import glob

categories = ['dairy', 'processed', 'grain', 'fruit']
meal_types = ['breakfast', 'lunch', 'dinner', 'snack', 'any']
recipe_columns = ['Quantity', 'Units', 'Food']
food_file = 'tracker.csv'
meal_dir = 'Recipes/'
meal_plan = 'saved_meals.csv'
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

### Helper functions
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

def filter_meals(meals, start=find_week_start(), days=7):
    ''' Finds meals between start and start+days '''
    td = timedelta(days=days)
    valid_meals = np.array(meals)
    valid_meals = valid_meals[valid_meals>=Meal(date=start)]
    valid_meals = valid_meals[valid_meals<Meal(date=start+td)]
    return list(valid_meals)

def read_recipes(meal_dir=meal_dir):
    """ Reads all recipes from a directory and returns a list of Meal objects  """
    meals = []
    for file in glob.glob(meal_dir+"*.csv"):
        filename = os.path.basename(file)
        meals.append(Meal.from_file(filename))
    return meals

def calc_foods(meals):
    """ 
    Sum of food amounts for the week
    start = a datetime.date object
    days = the number of days after start to count towards the food list
    """
    
    for meal in meals:
        # Check if it's a 'this week' meal if specified
        #cond = True if not max_incl else meal.date != date.max
        # If it's out of bounds, don't add it
        # Add up foods
        foods = {}
        for food_name in meal.foods:
            if food_name in foods:
                u = foods[food_name].units
                foods[food_name] += meal.foods[food_name].to(u)
            else:
                foods[food_name] = meal.foods[food_name]
    return foods

### Meal class
class Meal:
    def __init__(self, name="", foods={}, date=date.today(), category='any', instructions="", feeds=4):
        """ Initializes the Meal class """
        self.name = name
        self.foods = foods
        self.date = date
        self.category = category
        self.instructions = instructions
        self.feeds = feeds
        # Diet compliance
        self.percent = 0
        self.allowed = True
    
    def __str__(self):
        return f"{self.name}: {'this week' if self.date==date.max else str(self.date)}"
    
    def __repr__(self):
        return str(self)
    
    def __eq__(self, other):
        return self.name==other.name and self.date==other.date and self.category==other.category
    
    def __le__(self, other):
        return self.date <= other.date
    
    def __lt__(self, other):
        return self.date < other.date
    
    def __hash__(self):
        return self.date.day % 31 + self.date.month % 31
        
    def add_foods(self, foods):
        ''' Adds foods and amounts to recipe list '''
        self.foods.update(foods)
    
    def remove_foods(self, foods):
        ''' Removes foods from recipe list '''
        for food_name in foods:
            self.foods.pop(food_name, None)
    
    def to_file(self, meal_dir=meal_dir):
        """ Saves a Meal object to a csv file """
        name = self.name.replace(" ", "_").lower()+".csv"
        filename = meal_dir+name
        food_names = list(self.foods.keys())
        food_amounts = [x.magnitude for x in self.foods.values()]
        food_units = [str(x.units) for x in self.foods.values()]
        df = pd.DataFrame()
        df['Quantity'] = food_amounts
        df['Units'] = food_units
        df['Food'] = food_names
        #df['UnitsCheck'] = list(self.foods.values())
        #print(type(df['UnitsCheck'][0]))
        df.to_csv(filename, sep=",", index=False)
        return name
    
    @staticmethod
    def from_file(filename, meal_dir=meal_dir, date=date.today()):
        # Format recipe name
        name = filename.replace("_", " ")[:-4]
        name = " ".join([word.capitalize() for word in name.split(" ")])
        # Read from file
        data = pd.read_csv(meal_dir+filename)
        foods = {}
        for i,food_name in enumerate(data.Food):
            foods[food_name.lower()] = data.Quantity[i]*units(data.Units[i])
        return Meal(name, foods=foods, date=date)
            

### Food class
class Food:
    ''' Recipe class '''
    def __init__(self, name, category=None, special=None):
        self.name = name.lower()
        self.category = category
        self.special = special
    
    def __eq__(self, other):
        return self.name==other.name
    
    def __str__(self):
        return f"{self.name}, category: {self.category}"
        
        
class Diet:
    ''' Diet class to keep track of all foods and meals '''
    def __init__(self, meals=[], plan=food_file):
        self.read_plan(plan)
    
    def read_plan(self, file=None):
        if not file: return
        self.plan = {
            'allowed': [],
            'banned': [],
            'restricted': [], # <= 20% per week, (30% per day?)
        }
        for key in self.plan:
            foods = pd.read_csv(file, usecols=[key], squeeze=True).dropna()
            self.plan[key] = list(foods)
    
    def check_foods(self, foods):
        """
        Checks the dictionary of foods passed in for diet compliance
        Returns whether the food is diet compliant, followed by the percentage of restricted foods
        """
        restricted_tally = 0 * measure_unit # common units
        other_tally = 0 * measure_unit
        allowed = True
        for food_name in foods:
            if food_name in self.plan['banned']:
                allowed = False
                restricted_tally += foods[food_name].to(measure_unit)
            elif food_name in self.plan['restricted']:
                restricted_tally += foods[food_name].to(measure_unit) # add amt to counter
            else: # for now, just assume everything not listed is fine
                other_tally += foods[food_name].to(measure_unit)
        
        # No restricted foods
        if restricted_tally == 0:
            return allowed, 0
        
        restricted_amt = (restricted_tally/(restricted_tally+other_tally)).magnitude
        return restricted_amt <= 0.2, restricted_amt
        

### Contains variables and methods for meal planning
class MealPlan:
    
    def __init__(self, meals=[], diet=Diet()):
        """ Initializes a weekly meal plan """
        self.meals = meals
        self.diet = diet
        self.meals.sort()
    
    def add_meal(self, meal):
        """ Adds meals passed to a list """
        # Check if single argument
        self.meals.append(meals)
        self.meals.sort()
    
    def remove_meal(self, meal):
        self.meals.remove(meal)
    
    def get_meals(self, start=date.min, days=timedelta.max):
        return filter_meals(self.meals, start, days)
    
    def check_diet(self, start=find_week_start(), days=7):
        """ Checks a period of time for diet compliance """
        # First, check the whole set
        meals = filter_meals(self.meals, start, days)
        week_foods = calc_foods(meals)
        week_state = self.diet.check_foods(week_foods)
        
        # Check individual meals here
        for meal in meals:
            meal.allowed, meal.percent = self.diet.check_foods(meal.foods)
        return week_state
    
    def to_file(self, file=meal_plan):
        """ Saves all meals to recipes and meal metadata in a separate file """
        # Save all meals
        data = [[meal.to_file(), meal.date, meal.category, meal.instructions, meal.feeds] for meal in self.meals]
        # Save plan as a csv
        df = pd.DataFrame(data=data, columns=['file', 'date', 'category', 'instructions', 'feeds'])
        df.to_csv(file, index=False)
    
    @staticmethod
    def from_file(file=meal_plan, meal_dir=meal_dir):
        """ Reads in all previous meals from metadata """
        if not os.path.exists(meal_plan):
            return MealPlan()
        meals = []
        meal_data = pd.read_csv(file)
        for i in range(len(meal_data)):
            d = meal_data.iloc[i]
            m_date = date.fromisoformat(d.date)
            # Read in recipe
            meal = Meal.from_file(d.file, meal_dir, m_date)
            # Set other properties
            meal.category = d.category
            meal.instructions = d.instructions
            meal.feeds = d.feeds
            meals.append(meal)
        return MealPlan(meals = meals)
        
        