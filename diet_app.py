### diet_app.py - contains classes and methods for implementing the GUI for Mom's diet plan
### Author: Emily Ramey
### Date: 07/14/20

# Preamble
import sys
import numpy as np
from datetime import date, time, timedelta, datetime
from PyQt5 import QtWidgets as qtw, QtGui as qtg, QtCore as qtc
import diet_planner as diet

days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
mp = diet.MealPlan.from_file()

class DietModel(qtc.QAbstractItemModel):
    
    model_changed = qtc.pyqtSignal()
    
    def __init__(self):
        """ Constructs a Diet Model """
        super().__init__()
        self.selected_date = date.today()
        self.selected_scale = 7
        self.week_start_visible = True
        self.meal_plan = diet.MealPlan.from_file()
        self.recipes = diet.read_recipes()
    
    def set_scale(self, new_scale):
        print("model scale set:", new_scale)
        self.week_start_visible = new_scale==7
        self.selected_scale = new_scale
        self.model_changed.emit()
    
    def set_date(self, new_date):
        d = date(new_date.year(), new_date.month(), new_date.day())
        print("model date set:", d)
        self.selected_date = d
        self.model_changed.emit()
    
    def increment_date(self):
        td = timedelta(days = self.selected_scale)
        self.selected_date += td
        self.model_changed.emit()
        
    def decrement_date(self):
        td = timedelta(days = -self.selected_scale)
        self.selected_date += td
        self.model_changed.emit()
    
    def add_meal(self, meal):
        self.meal_plan.add_meal(meal)
        self.model_changed.emit()
    
    def add_recipe(self, recipe):
        self.recipes.append(recipe)
        self.model_changed.emit()

class MealBox(qtw.QFrame):
    
    def __init__(self, meal=None, mini=False):
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

class DayBox(qtw.QGroupBox):
    
    def __init__(self, box_date=date.today()):
        ''' Constructor for a calendar day '''
        day = box_date.weekday()
        self.date = box_date
        super().__init__(f"{days[day]} {box_date.month}/{box_date.day}", alignment=qtc.Qt.AlignHCenter)
        self.setSizePolicy(
            qtw.QSizePolicy.MinimumExpanding,
            qtw.QSizePolicy.MinimumExpanding
        )
        day_layout = qtw.QVBoxLayout()
        day_layout.setAlignment(qtc.Qt.AlignTop)
        self.setLayout(day_layout)
        self.populate_meals()
    
    def populate_meals(self):
        meals = mp.get_meals(start=self.date, days=1)
        for m in meals:
            meal_box = MealBox(meal=m)
            self.layout().addWidget(meal_box)
    
    def sizeHint(self):
        return qtc.QSize(100, 100)

class MainSideBar(qtw.QFrame):
    
    dateChosen = qtc.pyqtSignal(date)
    recipes = []
    
    def __init__(self, model):
        ''' Main Sidebar constructor '''
        super().__init__()
        self.model = model
        sidebar_layout = qtw.QVBoxLayout()
        self.setLayout(sidebar_layout)
        self.setSizePolicy(
            qtw.QSizePolicy.Maximum,
            qtw.QSizePolicy.Expanding
        )
        
        ### Calendar Widget
        # Just accept that this won't resize, k?
        self.calendar = qtw.QCalendarWidget()
        self.calendar.setSizePolicy(
            qtw.QSizePolicy.Expanding,
            qtw.QSizePolicy.Fixed
        )
        self.calendar.sizeHint = lambda: qtc.QSize(50, 50)
        sidebar_layout.addWidget(self.calendar)
        
        ### Recipe List Label
        recipe_label = qtw.QLabel("Your recipes:")
        recipe_label.setAlignment(qtc.Qt.AlignHCenter)
        recipe_label.setSizePolicy(
            qtw.QSizePolicy.Expanding,
            qtw.QSizePolicy.Fixed
        )
        sidebar_layout.addWidget(recipe_label)
        
        ### Recipe List
        self.recipe_list = qtw.QFrame()
        self.recipe_list.setSizePolicy(
            qtw.QSizePolicy.Expanding,
            qtw.QSizePolicy.MinimumExpanding
        )
        self.recipe_list.setLayout(qtw.QVBoxLayout())
        self.recipe_list.layout().setAlignment(qtc.Qt.AlignTop)
        self.recipe_list.sizeHint = lambda: qtc.QSize(50, 50)
        sidebar_layout.addWidget(self.recipe_list)
        self.populate_recipe_list()
        self.calendar.selectionChanged.connect(lambda: self.model.set_date(self.calendar.selectedDate()))
        
#         self.calendar.selectionChanged.connect(lambda: self.model.set_date(self.calendar.selectedDate()))
#         self.model.model_changed.connect(self.on_model_change)
#         self.on_model_change()
    
#     def on_model_change(self):
#         """ Changes sidebar view to match model """
#         d = self.model.selected_date
#         qdate = qtc.QDate(d.year, d.month, d.day)
#         self.calendar.setSelectedDate(qdate)
    
    def sendDate(self):
        self.model.set_date(self.calendar.selectedDate())
#         qdate = self.calendar.selectedDate()
#         d = date(qdate.year(), qdate.month(), qdate.day())
#         self.dateChosen.emit(d)
    
    def sizeHint(self):
        return qtc.QSize(150, 150)
    
    def populate_recipe_list(self):
        recipes = diet.read_recipes()
        for recipe in recipes:
            rWidget = MealBox(meal=recipe, mini=True)
            self.recipe_list.layout().addWidget(rWidget)

class DayPanel(qtw.QFrame):
    
    children = []
    def __init__(self, model, start_date=date.today(), scale=7):
        """ Main Panel constructor - contains list of days & meals """
        super().__init__()
        
        # Model
        self.model = model
        self.model.model_changed.connect(self.populate_days)
        
        # Layout
        layout = qtw.QHBoxLayout()
        layout.setAlignment(qtc.Qt.AlignHCenter)
        self.start_date = start_date
        self.scale=scale
        self.setLayout(layout)
#         self.on_model_change()
        self.populate_days()
        
    
    def clear_days(self):
        """ Clears all child widgets from main panel """
        for child in self.children:
            child.close() # Works for some reason
            self.layout().removeWidget(child)
        self.children = []
    
    def populate_days(self):
        self.clear_days()
        print(self.model.selected_scale)
        for i in range(self.model.selected_scale):
            td=timedelta(days=i)
            day_box = DayBox(self.model.selected_date+td)
            self.layout().addWidget(day_box, 1)
            self.children.append(day_box)
    
    def change_start(self, new_start):
        if type(new_start) is int:
            td = timedelta(days=new_start)
            self.start_date+=td
        else:
            self.start_date = new_start
        if self.scale==7:
            self.start_date = diet.find_week_start(self.start_date)
        self.populate_days()
    
    def change_scale(self, new_scale):
        self.scale = new_scale
        if new_scale==7:
            self.start_date = diet.find_week_start(self.start_date)
        self.populate_days()
    
#     def on_model_change(self):
#         start = self.model.selected_date
#         if self.model.week_start_visible:
#             start = diet.find_week_start(start)
#         print(start, self.model.selected_scale)
#         self.populate_days(start, self.model.selected_scale)

class MainTitleBar(qtw.QFrame):
    
    scale_change = qtc.pyqtSignal(int) # current day setting
    day_change = qtc.pyqtSignal(int)
    
    def __init__(self, model):
        """ Constructs the top panel for the main window """
        super().__init__()
        self.model = model
        self.model.model_changed.connect(self.on_model_change)
        
        self.setSizePolicy(
            qtw.QSizePolicy.Expanding,
            qtw.QSizePolicy.Fixed
        )
        center_layout = qtw.QHBoxLayout()
        center_layout.setAlignment(qtc.Qt.AlignHCenter)
        self.setLayout(center_layout)
        
        # Title and left/right buttons
        self.page_title = qtw.QLabel("")
        left_btn = qtw.QPushButton()
        left_btn.setIcon(self.style().standardIcon(getattr(qtw.QStyle, "SP_ArrowBack")))
        right_btn = qtw.QPushButton()
        right_btn.setIcon(self.style().standardIcon(getattr(qtw.QStyle, "SP_ArrowForward")))
        
        # Choice of # days to view
        self.day_choice = qtw.QComboBox()
        self.day_choice.addItem("1 day", 1)
        self.day_choice.addItem("4 days", 4)
        self.day_choice.addItem("7 days", 7)
        self.day_choice.setCurrentIndex(2)
        
        # Layout
        center_layout.addWidget(left_btn)
        center_layout.addWidget(self.page_title)
        center_layout.addWidget(right_btn)
        center_layout.addWidget(self.day_choice)
        
#         self.on_model_change()
        
        # Connect widget signals to class signals
        left_btn.clicked.connect(lambda: self.day_change.emit(-self.day_choice.currentData()))
        right_btn.clicked.connect(lambda: self.day_change.emit(self.day_choice.currentData()))
        self.day_choice.currentIndexChanged.connect(lambda: self.scale_change.emit(self.day_choice.currentData()))
        
#         left_btn.clicked.connect(self.model.decrement_date)
#         right_btn.clicked.connect(self.model.increment_date)
        self.day_choice.currentIndexChanged.connect(lambda: self.model.set_scale(self.day_choice.currentData()))
    
    def set_title(self):
        """ Sets the title based on the calendar date """
        title = self.model.selected_date.strftime("%B %Y")
        self.page_title.setText(title)
        
    def sizeHint(self):
        return qtc.QSize(600, 50)
    
    def on_model_change(self):
        pass
        #self.day_choice.setData(self.model.selected_scale)
#         title = self.model.selected_date.strftime("%B %Y")
#         self.page_title.setText(title)


# Main Window object
class MainWindow(qtw.QWidget):
    
    def __init__(self):
        ''' Main Window constructor '''
        super().__init__()
        
        # Model
        model = DietModel()
        
        # Window setup
        self.setWindowTitle("My Calendar App")
        self.resize(1600, 800)
        # Layout
        main_layout = qtw.QHBoxLayout()
        self.setLayout(main_layout)
        # Sidebar
        self.sidebar = MainSideBar(model)
        main_layout.addWidget(self.sidebar)
        panel_layout = qtw.QVBoxLayout()
        main_layout.addLayout(panel_layout)
        # Title bar
        self.main_title = MainTitleBar(model)
        panel_layout.addWidget(self.main_title)
        
        self.day_panel = DayPanel(model)
        panel_layout.addWidget(self.day_panel)
        
        # Connect date selection with date panel and title bar
        #self.sidebar.dateChosen.connect(self.day_panel.change_start)
        self.sidebar.dateChosen.connect(self.main_title.set_title)
        self.sidebar.sendDate()
        
        # Connect top panel with date panel
        self.main_title.scale_change.connect(self.day_panel.change_scale)
        self.main_title.day_change.connect(self.update_cal)
        
    def update_cal(self, days):
        qdate = self.sidebar.calendar.selectedDate()
        self.sidebar.calendar.setSelectedDate(qdate.addDays(days))

### Start program
if __name__ == '__main__':
    # Start application wity system arguments
    app = qtw.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    # Exit with app code upon closing the window
    code = app.exec()
    mp.to_file()
    sys.exit(code)