import sys
import numpy as np
from datetime import date, time, timedelta, datetime
from PyQt5 import QtWidgets as qtw, QtGui as qtg, QtCore as qtc
import diet_planner as diet

days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

### Diet Model - where all data is stored
class DietModel(qtc.QAbstractItemModel):
    
    model_changed = qtc.pyqtSignal()
    
    def __init__(self):
        """ Constructs a Diet Model """
        super().__init__()
        self.selected_scale = 7
        self.week_start_visible = True
        self.meal_plan = diet.MealPlan.from_file()
        self.recipes = diet.read_recipes()
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
    
    def add_meal(self, meal):
        """ Adds a meal to the meal plan """
        self.meal_plan.add_meal(meal)
        self.model_changed.emit()
    
    def add_recipe(self, recipe):
        """ Adds a recipe to the recipe list """
        self.recipes.append(recipe)
        self.model_changed.emit()

############################################## Sub-Widgets #####################################################

### Meal Widget
class MealBox(qtw.QFrame):
    
    def __init__(self, meal=None, mini=False):
        """ Constructs a meal box """
        super().__init__()
        self.setSizePolicy(
            qtw.QSizePolicy.MinimumExpanding,
            qtw.QSizePolicy.Maximum
        )
        self.mini = mini
        self.setLayout(qtw.QHBoxLayout())
        self.setFrameStyle(qtw.QFrame.StyledPanel)
        text = "None" if meal is None else meal.name
        label = qtw.QLabel(text)
        label.setAlignment(qtc.Qt.AlignHCenter)
        self.layout().addWidget(label)
    
    def sizeHint(self):
        return qtc.QSize(40, 15) if self.mini else qtc.QSize(100, 50)

### Day Widget
class DayBox(qtw.QGroupBox):
    
    def __init__(self, box_date, model):
        ''' Constructor for a calendar day (holds meal data) '''
        day = box_date.weekday()
        super().__init__(f"{days[day]} {box_date.month}/{box_date.day}", alignment=qtc.Qt.AlignHCenter)
        
        self.box_date = box_date
        self.model = model
        
        # Layout
        self.layout = qtw.QVBoxLayout()
        self.layout.setAlignment(qtc.Qt.AlignTop)
        self.setLayout(self.layout)
        self.setSizePolicy(
            qtw.QSizePolicy.MinimumExpanding,
            qtw.QSizePolicy.MinimumExpanding
        )
        
        self.populate_meals()
    
    def populate_meals(self):
        """ Populates a day box with its meals """
        meals = self.model.meal_plan.get_meals(start=self.box_date, days=1)
        for m in meals:
            meal_box = MealBox(meal=m)
            self.layout.addWidget(meal_box)
    
    def sizeHint(self):
        return qtc.QSize(100, 100)

########################################### Main Panels #######################################################

### Panel that holds days
class MainDayPanel(qtw.QFrame):
    
    children = []
    
    def __init__(self, model):
        """ Initializes the Main Day Panel (holds all day boxes) """
        super().__init__()
        
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
        for i in range(self.model.selected_scale):
            td=timedelta(days=i)
            day_box = DayBox(self.model.get_date()+td, self.model)
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
        scale_choice.addItem("1 day", 1)
        scale_choice.addItem("4 days", 4)
        scale_choice.addItem("7 days", 7)
        scale_choice.setCurrentIndex(2)
        
        # Add to Layout
        self.layout.addWidget(left_btn)
        self.layout.addWidget(self.page_title)
        self.layout.addWidget(right_btn)
        self.layout.addWidget(scale_choice)
        
        # Connect to model
        left_btn.clicked.connect(self.model.decrement_date)
        right_btn.clicked.connect(self.model.increment_date)
        scale_choice.currentIndexChanged.connect(lambda: self.model.set_scale(scale_choice.currentData()))
        
        self.read_model()
    
    def sizeHint(self):
        return qtc.QSize(600, 50)
        
    def set_title(self, text):
        """ Sets the title based on the calendar date """
        self.page_title.setText(text)
    
    def read_model(self):
        """ Reads model data and updates widget """
        title = self.model.get_date().strftime("%B %Y")
        self.set_title(title)


class MainSideBar(qtw.QFrame):
    
    def __init__(self, model):
        """ Constructor for the Main Side Bar """
        super().__init__()
        
        # Model
        self.model = model
        self.model.model_changed.connect(self.read_model)
        
        # Layout
        self.layout = qtw.QVBoxLayout()
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
        self.recipe_list.setSizePolicy(
            qtw.QSizePolicy.Expanding,
            qtw.QSizePolicy.MinimumExpanding
        )
        self.recipe_list.setLayout(qtw.QVBoxLayout())
        self.recipe_list.layout().setAlignment(qtc.Qt.AlignTop)
        self.recipe_list.sizeHint = lambda: qtc.QSize(50, 50)
        self.layout.addWidget(self.recipe_list)
        self.populate_recipe_list()
        
        self.read_model()
    
    def sizeHint(self):
        return qtc.QSize(150, 150)
    
    def populate_recipe_list(self):
        """ Populates the sidebar recipe list """
        recipes = diet.read_recipes()
        for recipe in recipes:
            rWidget = MealBox(meal=recipe, mini=True)
            self.recipe_list.layout().addWidget(rWidget)
    
    def read_model(self):
        """ Reads model and updates widget """
        pass

### Main Window Object
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

### Start Program
if __name__ == '__main__':
    # Start application wity system arguments
    app = qtw.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    # Exit with app code upon closing the window
    code = app.exec()
    mw.model.meal_plan.to_file()
    sys.exit(code)