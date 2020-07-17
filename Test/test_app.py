import sys
import numpy as np
from PyQt5 import QtWidgets as qtw, QtGui as qtg, QtCore as qtc

def on_button_clicked():
    alert = qtw.QMessageBox()
    alert.setText('You clicked the button!')
    alert.exec_()

class MainWindow(qtw.QWidget):
    def __init__(self):
        """Main Window Constructor"""
        super().__init__()
        
        # Main UI code goes here
        self.setWindowTitle('Hello Qt')
        layout = qtw.QHBoxLayout()
        #layout = qtw.QGridLayout()
        self.setLayout(layout)
        
        ### Label
        # Pass parent widget in to all child widgets
        label = qtw.QLabel('Hello, widgets!', self)
        label2 = qtw.QLabel('Hello, widgets 2!', self)
        
        ### Line Edit
        line_edit = qtw.QLineEdit(
            'default value',
            self,
            placeholderText='Type here',
            clearButtonEnabled=True,
            maxLength=20
        )
        
        ### Button
        button = qtw.QPushButton(
            "Push Me", 
            self,
            checkable=True,
            shortcut=qtg.QKeySequence('Ctrl+p')
        )
        
        ### Combo Box
        combobox = qtw.QComboBox(
            self,
            editable=True,
            insertPolicy=qtw.QComboBox.InsertAtTop
        )
        combobox.addItem('Lemon', 1)
        combobox.addItem('Peach', 'Ohh I like Peaches!')
        combobox.addItem('Strawberry', qtw.QWidget)
        combobox.insertItem(1, 'Radish', 2)
        combobox.setCurrentIndex(1)
        layout.addWidget(combobox)
        
        ### Spin Box
        # Use QDoubleSpinBox for floating point numbers
        spinbox = qtw.QSpinBox(
            self,
            value=12,
            maximum=100,
            minimum=10,
            prefix='$',
            suffix=' + Tax',
            singleStep=5
        )
        
        ### Date-Time Box
        datetimebox = qtw.QDateTimeEdit(
            self,
            date=qtc.QDate.currentDate(),
            calendarPopup = True,
            maximumDate=qtc.QDate(2030, 1, 1),
            displayFormat='yyyy-MM-dd'
        )
        
        ### Text Box
        textedit = qtw.QTextEdit(
            self,
            acceptRichText=False,
            lineWrapMode=qtw.QTextEdit.FixedColumnWidth,
            lineWrapColumnOrWidth=25,
            placeholderText='Enter your text here'
        )
        
        ### For grid layout
#         widgets = np.array([label, label2, button, line_edit, combobox, spinbox, datetimebox, textedit]).reshape(4, 2)
        
#         for i in range(4):
#             for j in range(2):
#                 layout.addWidget(widgets[i,j], i, j)
        
        tab_widget = qtw.QTabWidget(
            movable=True,
            tabPosition=qtw.QTabWidget.North,
            tabShape=qtw.QTabWidget.Triangular
        )
        
        layout.addWidget(tab_widget)
        container1 = qtw.QWidget(self)
        container2 = qtw.QWidget(self)
        
        grid_layout = qtw.QGridLayout()
        v_layout = qtw.QVBoxLayout()
        
        container1.setLayout(grid_layout)
        container2.setLayout(v_layout)
        
        tab_widget.addTab(container1, 'Tab the first')
        tab_widget.addTab(container2, 'Tab the second')
        
        grid_layout.addWidget(label, 0, 0)
        v_layout.addWidget(label2)
        
        grid_layout.addWidget(line_edit, 0, 1)
        
        for widget in [button, combobox, spinbox, datetimebox]:
            v_layout.addWidget(widget)
        
        grid_layout.addWidget(textedit, 1, 0)
        
        
        # End main UI code
        
        self.show()

if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    mw = MainWindow()
    sys.exit(app.exec())

