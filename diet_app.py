import sys
import numpy as np
from datetime import date, time, timedelta, datetime
from PyQt5 import QtWidgets as qtw, QtGui as qtg, QtCore as qtc
import diet_planner_2 as diet
import io
import os

days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

### Stylesheet for now
stylesheet = """
        QFrame#bad {
            background-color: red;
        }
        QFrame#good {
            background-color: green;
        }
        QPushButton#bad {
            background-color: red;
            color: black;
        }
        QPushButton#good {
            background-color: green;
            color: black;
        }
        QPushButton#medium {
            background-color: orange;
            color: black;
        }
        """

### Helper Functions
def clear_widget(widget, children):
    """ Clears a widget of its children """
    for child in children:
        child.close() # Works for some reason
        widget.layout().removeWidget(child)
        child.destroy()
    widget.children = []

def ingr_to_dict(ingr_string):
    """ Returns a dictionary from a readable string of ingredients """
    if ingr_string=="" or ingr_string.isspace():
        return {}
    text = ingr_string.split("\n")
    text = [line.split(" ") for line in text]
    for i in range(len(text)):
        # If ingredient is multiple words
        if len(text[i])>3:
            for j in range(3, len(text[i])):
                text[i][2]+=" "+text[i][j]
    text = {line[2]: float(line[0])*diet.units(line[1]) for line in text}
    return text

def dict_to_ingr(ingr_dict):
    """ Returns a readable string of ingredients from a dictionary """
    text = [f"{str(amount)} {label}" for label, amount in ingr_dict.items()]
    text = "\n".join(text)
    return text

def recipe_filename(name):
    """ Returns a filename based on the recipe's saved name """
    name = name.replace(" ", "_")
    name = name.lower()
    while os.path.exists(name+".dat"):
        name += "0"
    name+=".dat"
    return name

def from_qdate(qdate):
    return date(qdate.year(), qdate.month(), qdate.day())

def from_date(r_date):
    return qtc.QDate(r_date.year, r_date.month, r_date.day)

############################################### Diet Model ######################################################
# Where all the data is stored
class DietModel(qtc.QAbstractItemModel):
    
    model_changed = qtc.pyqtSignal()
    
    def __init__(self):
        """ Constructs a Diet Model """
        super().__init__()
        self.selected_scale = 7
        self.week_start_visible = True
        self.meal_plan = diet.MealPlan()
        self.calendar = qtw.QCalendarWidget()
        self.set_date(date.today())
        
        self.calendar.selectionChanged.connect(self.model_changed.emit)
    
    def set_scale(self, new_scale):
        """ Sets the selected scale (#days) """
        self.week_start_visible = new_scale==7
        self.selected_scale = new_scale
        self.model_changed.emit()
    
    def set_date(self, new_date):
        """ Sets the selected date """
        if type(new_date) is date:
            new_date = qtc.QDate(new_date.year, new_date.month, new_date.day)
        self.calendar.setSelectedDate(new_date)
    
    def get_date(self):
        """ Returns the date on the calendar """
        qd = self.calendar.selectedDate()
        d = date(qd.year(), qd.month(), qd.day())
        return d
    
    def increment_date(self):
        """ Increments the date by the # of days in scale """
        td = timedelta(days = self.selected_scale)
        self.set_date(self.get_date()+td)
        
    def decrement_date(self):
        """ Decrements the date by the # of days in the scale """
        td = timedelta(days = -self.selected_scale)
        self.set_date(self.get_date()+td)
    
    def update_meal_plan(self):
        """ Updates a meal in the meal plan """
        self.meal_plan.to_file()
        self.meal_plan.update()
        self.model_changed.emit()
    
#     def add_meal(self, meal):
#         """ Adds a recipe to the recipe list """
#         self.meal_plan.add_meal(meal)
#         self.model_changed.emit()
    
#     def remove_meal(self, meal):
#         self.meal_plan.remove_meal(meal)

############################################## Sub-Widgets #####################################################

class CategoryHeading(qtw.QFrame):
    
    def __init__(self, model, date, category):
        """ Makes a frame for category label and add button """
        super().__init__()
        
        self.category = category
        self.model = model
        self.date = date
        
        # Layout
        align = qtw.QHBoxLayout()
        align.setAlignment(qtc.Qt.AlignLeft)
        align.setSpacing(10)
        self.setLayout(align)
        self.setSizePolicy(
            qtw.QSizePolicy.MinimumExpanding,
            qtw.QSizePolicy.Fixed
        )
        self.sizeHint = lambda: qtc.QSize(20, 15)

        # Category label
        label = qtw.QLabel(category.capitalize()+":")
        label.sizeHint = lambda: qtc.QSize(20, 15)
        label.setSizePolicy(
            qtw.QSizePolicy.Fixed,
            qtw.QSizePolicy.Fixed
        )

        # Add button
        add_btn = qtw.QPushButton("+")
        add_btn.sizeHint = lambda: qtc.QSize(15, 15)
        add_btn.setSizePolicy(
            qtw.QSizePolicy.Fixed,
            qtw.QSizePolicy.Fixed
        )
        add_btn.setFlat(True)

        # Layout
        align.addWidget(label)
        align.addWidget(add_btn)
        
        add_btn.pressed.connect(self.add_clicked)
    
    def add_clicked(self):
        """ Opens the Add Meal window """
        self.add_window = AddWindow(self.model, self.date, self.category)
        self.add_window.show()

### Meal Widget
class MealBox(qtw.QPushButton):
    
    def __init__(self, model, meal, is_recipe=False):
        """ Constructs a meal box """
        super().__init__()
        self.setSizePolicy(
            qtw.QSizePolicy.MinimumExpanding,
            qtw.QSizePolicy.Maximum
        )
        self.sizeHint = qtc.QSize(30, 20)
        self.model = model
        self.is_recipe = is_recipe
        self.meal = meal
        text = meal.name
        self.setText(text)
        self.pressed.connect(self.on_recipe_click)
        
        badness = self.meal.percent
        if badness>0.4:
            self.setObjectName("bad")
        elif badness > 0.2:
            self.setObjectName("medium")
        else:
            self.setObjectName("good")

        self.setStyleSheet(stylesheet)
    
    def sizeHint(self):
        return qtc.QSize(50, 50) if self.is_recipe else qtc.QSize(100, 50)
    
    def on_recipe_click(self):
        """ Opens an edit window for the meal or recipe """
        self.meal_window = MealWindow(self.model, meal=self.meal, is_recipe=self.is_recipe)
        self.meal_window.show()

### Day Widget
class DayBox(qtw.QGroupBox):
    
    def __init__(self, box_date, model):
        ''' Constructor for a calendar day (holds meal data) '''
        day = box_date.weekday()
        super().__init__(f"{days[day]} {box_date.month}/{box_date.day}", alignment=qtc.Qt.AlignHCenter)
        
        self.date = box_date
        self.model = model
        
        # Layout
        self.layout = qtw.QVBoxLayout()
        self.layout.setAlignment(qtc.Qt.AlignTop)
        self.setLayout(self.layout)
        self.setSizePolicy(
            qtw.QSizePolicy.MinimumExpanding,
            qtw.QSizePolicy.MinimumExpanding
        )
        
        # Populate all meals for the day
        self.populate_meals()
    
    def populate_meals(self):
        """ Populates a day box with its meals """
        meals = self.model.meal_plan.get_meals(start=self.date, days=1)
        categories = {cat.capitalize()+":": [] for cat in diet.meal_categories}
        for m in meals:
            meal_box = MealBox(self.model, meal=m)
            categories[m.category.capitalize()+":"].append(meal_box)
        
        for cat, meal_boxes in categories.items():
            # Add category label
            self.layout.addWidget(CategoryHeading(self.model, self.date, cat.lower()[:-1]))
            
            # Add meal boxes
            for meal_box in meal_boxes:
                self.layout.addWidget(meal_box)
    
    def sizeHint(self):
        return qtc.QSize(100, 100)

########################################### Add Meal Panel ########################################################

class AddWindow(qtw.QWidget):
    
    def __init__(self, model, r_date, category):
        """ Initializes a window to add a meal to a day """
        super().__init__(None, modal=False)
        self.model = model
        self.setWindowTitle("Add Meal")
        
        # Layout
        layout = qtw.QFormLayout()
        self.setLayout(layout)
        
        # Recipe choice
        self.recipe_choice = qtw.QComboBox()
        for recipe in self.model.meal_plan.recipes:
            self.recipe_choice.addItem(recipe.name, recipe.filename)
        layout.addRow("Recipe:", self.recipe_choice)
        
        # Date choice
        self.date_box = qtw.QDateEdit()
        self.date_box.setCalendarPopup(True)
        qdate = qtc.QDate(r_date.year, r_date.month, r_date.day)
        self.date_box.setDate(qdate)
        layout.addRow("Date:", self.date_box)
        
        # Category choice
        self.category_choice = qtw.QComboBox()
        self.category_choice.addItems(diet.meal_categories)
        layout.addRow("Category:", self.category_choice)
        self.category_choice.setCurrentText(category)
        
        # Buttons
        save_btn = qtw.QPushButton("Save", pressed=self.save_clicked)
        cancel_btn = qtw.QPushButton("Cancel", pressed=self.close)
        layout.addRow(save_btn, cancel_btn)
    
    def save_clicked(self):
        """ Saves new meal to meal plan """
        filename = self.recipe_choice.currentData()
        file = os.path.basename(filename)
        qdate = self.date_box.date()
        m_date = date(qdate.year(), qdate.month(), qdate.day())
        category = self.category_choice.currentText()
        m = diet.Meal(file, m_date=m_date, category=category)
        self.model.meal_plan.add_meal(m)
        self.model.update_meal_plan()
        self.close()
        

########################################### Meal Edit Panel #######################################################

meal_entries = {"Name": qtw.QLineEdit, "Date": qtw.QDateEdit, "Category": qtw.QLineEdit, "Servings": qtw.QLineEdit,
                "Ingredients": qtw.QTextEdit, "Instructions": qtw.QTextEdit}

class MealWindow(qtw.QWidget):
    
    def __init__(self, model, meal=None, is_recipe=False):
        """ Initializes a Meal Window for editing or creating meals/recipes """
        super().__init__(None, modal=False)
        if meal is None:
            title = "New Meal"
        elif is_recipe:
            title = "View Recipe"
        else:
            title = "View Meal"
        
        # Initialize
        self.entries = {}
        self.buttons = []
        self.meal = meal
        self.editable = meal is None
        self.is_recipe = is_recipe
        self.model = model
        
        # Layout
        self.setWindowTitle(title)
        self.setLayout(qtw.QVBoxLayout())
        self.form_layout = qtw.QFormLayout()
        self.btn_frame = qtw.QFrame()
        self.btn_frame.setSizePolicy(
            qtw.QSizePolicy.Expanding,
            qtw.QSizePolicy.Maximum
        )
        self.btn_frame.setLayout(qtw.QHBoxLayout())
        self.btn_frame.layout().setAlignment(qtc.Qt.AlignRight)
        self.layout().addLayout(self.form_layout)
        self.layout().addWidget(self.btn_frame)
        
        # Form
        for label in meal_entries:
            self.add_entry(label)
        
        self.set_entries()
        self.populate_btns()
    
    def add_entry(self, label):
        """ Adds a row to the form """
        widget = meal_entries[label]()
        if self.is_recipe:
            if label=="Date" or label=="Category":
                return
            self.entries[label] = widget
        elif label=="Date" or label=="Category":
            self.entries[label] = widget
        self.form_layout.addRow(label+":", widget)
        
        if self.meal is None:
            return
        
        # Set current text
        current = getattr(self.meal, label.lower())
        if label=='Ingredients':
            text = dict_to_ingr(current)
        elif label=="Date":
            widget.setDisplayFormat("MM/dd/yyyy")
            widget.setCalendarPopup(True)
            qdate = qtc.QDate(current.year, current.month, current.day)
            widget.setDate(qdate)
            return
        else: text = str(current)
        if text=='nan': text = ""
        widget.setText(text)
        widget.setReadOnly(True)
    
    def make_btn(self, text, clicked):
        """ Makes a new button based on inputs """
        btn = qtw.QPushButton(
            text,
            pressed=clicked
        )
        btn.setSizePolicy(
            qtw.QSizePolicy.Fixed,
            qtw.QSizePolicy.Fixed
        )
        self.btn_frame.layout().addWidget(btn)
        self.buttons.append(btn)
    
    def set_entries(self):
        for label in self.entries:
            widget = self.entries[label]
            if self.editable: # Enable editing
                widget.setReadOnly(False)
                if type(widget) is qtw.QTextEdit: # TextEdits are stupid
                    widget.viewport().setCursor(qtc.Qt.IBeamCursor)
            else: # Set read-only
                widget.setReadOnly(True)
                if type(widget) is qtw.QTextEdit:
                    widget.viewport().setCursor(qtc.Qt.ArrowCursor)
    
    def populate_btns(self):
        """ Clears and repopulates buttons """
        clear_widget(self.btn_frame, self.buttons)
        if not self.editable:
            self.make_btn('Edit', self.edit_clicked)
            self.make_btn('Remove', self.remove_clicked)
            self.make_btn('Close', self.close)
        else:
            self.make_btn('Save', self.save_clicked)
            self.make_btn('Cancel', self.close)
    
    def edit_clicked(self):
        """ Refreshes the buttons when edit is clicked """
        self.editable = True
        self.set_entries()
        self.populate_btns()
    
    def remove_clicked(self):
        """ Removes meal or recipe """
        self.model.meal_plan.remove_meal(self.meal)
        self.model.update_meal_plan()
        self.close()
    
    def save_clicked(self):
        """ Sends information to the model """
        self.editable = False
        self.set_entries()
        self.populate_btns()
        
        # Check if a meal was passed
        if self.meal is None:
            name = self.entries['Name'].text()
            if name=="":
                print("Must enter a recipe name")
                return
            file = recipe_filename(name)
            self.meal = diet.Recipe(file)
        
        # Update fields
        for label,widget in self.entries.items():
            # Check if it's a LineEdit or a TextEdit
            if type(widget) is qtw.QTextEdit:
                text = widget.toPlainText()
            elif type(widget) is qtw.QLineEdit:
                text = widget.text()
            # Process individual labels
            if label=="Date":
                qdate = widget.date()
                text = date(qdate.year(), qdate.month(), qdate.day())
            elif label=="Ingredients":
                text = widget.toPlainText()
                text = ingr_to_dict(text)
            setattr(self.meal, label.lower(), text)
        
        # Save new information
        self.meal.to_file()
        self.model.update_meal_plan()
        self.close()

############################################## Main Window Panels ##############################################
### Panel that holds days
class MainDayPanel(qtw.QFrame):
    
    def __init__(self, model):
        """ Initializes the Main Day Panel (holds all day boxes) """
        super().__init__()
        self.children = []
        
        # Model
        self.model = model
        self.model.model_changed.connect(self.read_model)
        
        # Layout
        self.layout = qtw.QHBoxLayout()
        self.layout.setAlignment(qtc.Qt.AlignHCenter)
        self.setLayout(self.layout)
        self.setSizePolicy(
            qtw.QSizePolicy.MinimumExpanding,
            qtw.QSizePolicy.MinimumExpanding
        )
        
        self.read_model()
        
    def clear_days(self):
        """ Clears all child widgets from main panel """
        for child in self.children:
            child.close() # Works for some reason
            self.layout.removeWidget(child)
            child.destroy()
        self.children = []
    
    def populate_days(self):
        """ Populates all days in the main day panel """
        self.clear_days()
        start = self.model.get_date()
        scale = self.model.selected_scale
        
        # Check for week view
        if self.model.week_start_visible:
            start = diet.find_week_start(start)
        # Add days
        for i in range(scale):
            td=timedelta(days=i)
            day_box = DayBox(start+td, self.model)
            self.layout.addWidget(day_box, 1)
            self.children.append(day_box)
    
    def read_model(self):
        """ Reads model data and updates widget """
        self.populate_days()

### Main title bar
class MainTitleBar(qtw.QFrame):
    
    def __init__(self, model):
        """ Initializes the Main Title Bar """
        super().__init__()
        
        # Model
        self.model = model
        self.model.model_changed.connect(self.read_model)
        
        # Layout
        self.layout = qtw.QHBoxLayout()
        self.layout.setAlignment(qtc.Qt.AlignHCenter)
        self.layout.setSpacing(15)
        self.setLayout(self.layout)
        self.setSizePolicy(
            qtw.QSizePolicy.Expanding,
            qtw.QSizePolicy.Fixed
        )
        
        # Title and left/right buttons
        self.page_title = qtw.QLabel("")
        left_btn = qtw.QPushButton()
        left_btn.setIcon(self.style().standardIcon(getattr(qtw.QStyle, "SP_ArrowBack")))
        right_btn = qtw.QPushButton()
        right_btn.setIcon(self.style().standardIcon(getattr(qtw.QStyle, "SP_ArrowForward")))
        
        # Combo Box
        scale_choice = qtw.QComboBox()
        scale_choice.addItem("day", 1)
        scale_choice.addItem("4 days", 4)
        scale_choice.addItem("week", 7)
        scale_choice.setCurrentIndex(2)
        
        # Add to Layout
        self.layout.addWidget(left_btn)
        self.layout.addWidget(self.page_title)
        self.layout.addWidget(right_btn)
        self.layout.addWidget(scale_choice)
        
        # Indicator square
        self.layout.addWidget(qtw.QLabel("Diet status: "))
        self.indicator = qtw.QPushButton("")
        self.indicator.setEnabled(False)
        self.layout.addWidget(self.indicator)
        
        # Connect to model
        left_btn.pressed.connect(self.model.decrement_date)
        right_btn.pressed.connect(self.model.increment_date)
        scale_choice.currentIndexChanged.connect(lambda: self.model.set_scale(scale_choice.currentData()))
        
        self.read_model()
    
    def sizeHint(self):
        return qtc.QSize(600, 50)
        
    def set_title(self, text):
        """ Sets the title based on the calendar date """
        self.page_title.setText(text)
    
    def set_indicator(self):
        """ Checks diet and sets indicator bar """
        start = self.model.get_date()
        scale = self.model.selected_scale
        # Check diet
        accept, percent = self.model.meal_plan.check_plan(start, scale)
        if accept:
            self.indicator.setObjectName("good")
            self.indicator.setText("Good Job!")
        else:
            self.indicator.setObjectName("bad")
            self.indicator.setText("Make changes")
        self.indicator.setStyleSheet(stylesheet)
    
    def read_model(self):
        """ Reads model data and updates widget """
        title = self.model.get_date().strftime("%B %Y")
        self.set_title(title)
        self.set_indicator()

### Main Side Bar
class MainSideBar(qtw.QFrame):
    
    def __init__(self, model):
        """ Constructor for the Main Side Bar """
        super().__init__()
        
        self.recipe_widgets = []
        
        # Model
        self.model = model
        self.model.model_changed.connect(self.read_model)
        
        # Layout
        self.layout = qtw.QVBoxLayout()
        self.layout.setAlignment(qtc.Qt.AlignHCenter)
        self.setLayout(self.layout)
        self.setSizePolicy(
            qtw.QSizePolicy.Maximum,
            qtw.QSizePolicy.Expanding
        )
        
        # Calendar
        self.calendar = self.model.calendar
        self.calendar.setSizePolicy(
            qtw.QSizePolicy.Expanding,
            qtw.QSizePolicy.Fixed
        )
        self.calendar.sizeHint = lambda: qtc.QSize(50, 50)
        self.calendar.setVerticalHeaderFormat(qtw.QCalendarWidget.NoVerticalHeader)
        self.layout.addWidget(self.calendar)
        
        # Label
        recipe_label = qtw.QLabel("Your recipes:")
        recipe_label.setAlignment(qtc.Qt.AlignHCenter)
        recipe_label.setSizePolicy(
            qtw.QSizePolicy.Expanding,
            qtw.QSizePolicy.Fixed
        )
        self.layout.addWidget(recipe_label)
        
        # Recipe List
        self.recipe_list = qtw.QFrame()
        self.recipe_list.setFrameStyle(qtw.QFrame.StyledPanel)
        self.recipe_list.setSizePolicy(
            qtw.QSizePolicy.Expanding,
            qtw.QSizePolicy.MinimumExpanding
        )
        self.recipe_list.setLayout(qtw.QVBoxLayout())
        self.recipe_list.layout().setAlignment(qtc.Qt.AlignTop)
        self.recipe_list.layout().setSpacing(20)
        self.recipe_list.sizeHint = lambda: qtc.QSize(50, 50)
        self.layout.addWidget(self.recipe_list)
        self.populate_recipe_list()
        
        # Add Button
        btn_layout = qtw.QHBoxLayout()
        btn_layout.setAlignment(qtc.Qt.AlignRight)
        self.layout.addLayout(btn_layout)
        self.add_btn = qtw.QPushButton(
            'Add',
            pressed=self.add_window
        )
        self.add_btn.setSizePolicy(
            qtw.QSizePolicy.Fixed,
            qtw.QSizePolicy.Fixed
        )
        btn_layout.addWidget(self.add_btn)
        
        self.read_model()
    
    def sizeHint(self):
        return qtc.QSize(150, 150)
    
    def add_window(self):
        self.add_window = MealWindow(self.model, is_recipe=True)
        self.add_window.show()
    
    def populate_recipe_list(self):
        """ Populates the sidebar recipe list """
        clear_widget(self.recipe_list, self.recipe_widgets)
        for recipe in self.model.meal_plan.recipes:
            recipe_widget = MealBox(self.model, meal=recipe, is_recipe=True)
            self.recipe_list.layout().addWidget(recipe_widget)
            self.recipe_widgets.append(recipe_widget)
    
    def read_model(self):
        """ Reads model and updates widget """
        self.populate_recipe_list()

### Main Window
class MainWindow(qtw.QWidget):
    
    def __init__(self):
        ''' Main Window constructor '''
        super().__init__()
        
        # Window setup
        self.setWindowTitle("My Calendar App")
        self.resize(1600, 800)
        
        # Layout
        main_layout = qtw.QHBoxLayout()
        self.setLayout(main_layout)
        panel_layout = qtw.QVBoxLayout()
        
        # Model
        self.model = DietModel()
        
        # Sidebar
        self.sidebar = MainSideBar(self.model)
        main_layout.addWidget(self.sidebar)
        
        # Title Bar
        main_layout.addLayout(panel_layout)
        self.main_title = MainTitleBar(self.model)
        panel_layout.addWidget(self.main_title)
        
        # Main Day Panel
        self.main_panel = MainDayPanel(self.model)
        panel_layout.addWidget(self.main_panel)

############################################## Start Program ##############################################
if __name__ == '__main__':
    # Start application wity system arguments
    app = qtw.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    # Exit with app code upon closing the window
    code = app.exec()
    mw.model.meal_plan.to_file()
    sys.exit(code)