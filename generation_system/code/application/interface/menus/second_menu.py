"""
Main Window for Interface
"""

import sys
import textwrap

from PyQt5 import Qt, QtCore, QtGui, QtWidgets

from application.interface.components.qline import QHLine
from application.interface.components.qworker import Worker
from application.interface.menus.menu import MyMenu
from application.logic.representation.events.viewpoint_description import DESCRIPTION


class ShowStatsWidget(QtWidgets.QWidget):
    def __init__(self, name, statistics, description):
        super(ShowStatsWidget, self).__init__()

        self.name = name

        self.description = description

        self.weight = 0
        self.is_fixed = False

        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.setAlignment(QtCore.Qt.AlignTop)
        self.vbox.setContentsMargins(5, 5, 5, 5)

        self.set_name_and_description()
        self.vbox.addWidget(QHLine())
        for key, stat in statistics.items():
            if key == 'weight':
                self.weight = stat
            elif key == 'fixed':
                self.is_fixed = stat
            else:
                widget = self.handle_stat(key, stat, QtWidgets.QLabel(''))
                if ((key == 'unique_values' and statistics['number_of_unique_values'] > 3)
                        or (key == 'number_of_unique_values' and statistics['number_of_unique_values'] < 4)):
                    widget.setHidden(True)
                self.vbox.addWidget(widget)

        self.vbox.addWidget(QHLine())
        self.set_weight_box()
        self.set_fixed_box()

        if self.is_fixed:
            self.weight_box.setDisabled(self.is_fixed)

        self.setLayout(self.vbox)

    def set_name_and_description(self):
        """
        Set name of Viewpoint and its description
        """
        splited_name = self.name.split('.')
        name = " -> ".join(splited_name)
        if len(splited_name) > 2:
            part = " -> ".join(splited_name[0:2])
            new_part = " -> ".join(splited_name[2:])
            name = "\n-> ".join([part, new_part])

        self.lbl = QtWidgets.QLabel(name)
        self.lbl.setStyleSheet("""color: blue; font: bold 18px;""")
        self.vbox.addWidget(self.lbl)   # Add the label to the layout

        wrapped_description = '\n'.join(textwrap.wrap(self.description, 30))
        self.lbl_2 = QtWidgets.QLabel(wrapped_description)
        self.lbl_2.setStyleSheet("""color: black; font: bold 15px;""")
        self.vbox.addWidget(self.lbl_2)   # Add the label to the layout

    def set_weight_box(self):
        """
        Create Weight Box
        """
        hor_box = QtWidgets.QHBoxLayout()
        hor_box.setAlignment(QtCore.Qt.AlignLeft)
        hor_box.setContentsMargins(5, 5, 5, 5)

        label = QtWidgets.QLabel('Choose Weight: ')
        label.setStyleSheet(
            """color: blue; font: bold 16px; """)

        self.weight_box = QtWidgets.QSlider(self)
        self.weight_box.setOrientation(QtCore.Qt.Horizontal)
        self.weight_box.setMaximum(100)
        self.weight_box.setValue(self.weight)
        self.weight_box.setStyleSheet(
            """color: black; font: bold 16px; """)
        self.weight_box.valueChanged.connect(self.change_weight)

        label.setBuddy(self.weight_box)
        hor_box.addWidget(label)
        hor_box.addWidget(self.weight_box)

        self.vbox.addLayout(hor_box)

    def set_fixed_box(self):
        """
        Create Fixed Box
        """
        hbox = QtWidgets.QHBoxLayout()
        hbox.setAlignment(QtCore.Qt.AlignLeft)
        hbox.setContentsMargins(5, 5, 5, 5)

        f_label = QtWidgets.QLabel('Fixed Weight ?')
        f_label.setStyleSheet(
            """color: blue; font: bold 16px;""")

        self.fixed_box = QtWidgets.QCheckBox(self)       
        self.fixed_box.setChecked(self.is_fixed) 
        self.fixed_box.stateChanged.connect(self.change_fixed_status)

        f_label.setBuddy(self.fixed_box)
        hbox.addWidget(f_label)
        hbox.addWidget(self.fixed_box)

        self.vbox.addLayout(hbox)

    def change_weight(self, value):
        """
        Handle for spinbox of weight
        """
        self.weight = value

    def change_fixed_status(self, state):
        """
        Handle for checkbox of fixed weight
        """
        self.is_fixed = (False, True)[state == 2]
        self.weight_box.setDisabled(self.is_fixed)

    def handle_stat(self, key, stat, label):
        """
        Handle statistics labeling
        """
        if isinstance(stat, list):
            plus_text = ''
            if key == 'unique_values' and len(stat) < 4:
                new_tuples = stat
                values = [x[0] for x in stat]
                if len(values) <= 2 and all(val in [0, 1] for val in values):
                    new_tuples = [(bool(_tuple[0]), _tuple[1])
                                  for _tuple in stat]
                for i, _tuple in enumerate(new_tuples):
                    if _tuple[0] == 10000:
                        plus_text += 'No value' + ' : ' + \
                            str(_tuple[1]) + ' times'
                    else:
                        plus_text += str(_tuple[0]) + ' : ' + \
                            str(_tuple[1]) + ' times'
                    if i < len(new_tuples) - 1:
                        plus_text += '\n'

            if plus_text != '':
                label.setText(' '.join(key.split('_')) +
                              ' : ' + '\n' + plus_text)
        else:
            label.setText(' '.join(key.split('_')) + ' : ' + str(stat))
            label.setWordWrap(True)
            if 'percentage' in key:
                label.setText(label.text() + ' %')
        return label

    def change_stats(self, stats):
        if 'weight' in stats:
            self.weight_box.setValue(stats['weight'])
        if 'fixed' in stats:
            self.fixed_box.setChecked(stats['fixed'])

        for widget in self.children():
            if isinstance(widget, QtWidgets.QLabel):
                if ' : ' in widget.text():
                    key = '_'.join(widget.text().split(' : ')[0].split(' '))
                    widget = self.handle_stat(key, stats[key], widget)
                    if stats['number_of_unique_values'] > 3 and (key == 'unique_values'):
                        widget.setHidden(True)
                    elif stats['number_of_unique_values'] < 4 and key == 'number_of_unique_values':
                        widget.setHidden(True)


class SecondMenu(MyMenu):
    """
    Second Menu:
    - Present Statistics
    - Choosing Weights
    """

    def __init__(self, width, height, parent, *args, **kwargs):
        super(SecondMenu, self).__init__(
            width, height, parent, *args, **kwargs)

        self.top_group = self.create_settings(parent, width)
        self.top_group.layout().setContentsMargins(5, 5, 10, 0)

        self.container = QtWidgets.QWidget()
        self.container.setLayout(QtWidgets.QVBoxLayout(self.container))
        self.container.layout().setContentsMargins(5, 5, 5, 5)
        self.tab_parts = None
        self.tab_interpart = None

        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(35)

        bottom_spacer = QtWidgets.QWidget()
        bottom_spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        self.main_layout.addWidget(self.top_group, 0, 0, 1, 2)
        self.main_layout.addWidget(self.container, 1, 0, 14, 2)
        self.main_layout.addWidget(bottom_spacer, 15, 0, 1, 2)

    def resizeEvent(self, event):
        """
        Override of resizeEvent for override path text
        """
        self.main_layout.setContentsMargins(5, 5, 5, 5)

    def create_settings(self, parent, width):
        """
        Create database settings Grouping
        - Start Viewpoint Statistics
        - Choose Automatic Statistics
        """
        database_group = QtWidgets.QWidget()
        database_group.setStyleSheet("margin-left: 10px; padding: 15px;")
        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(3, 3, 3, 3)

        layout.setColumnStretch(0, 2)
        layout.setColumnStretch(1, 2)

        #button = QtWidgets.QPushButton('View Statistics')
        # button.clicked.connect(self.calculate_statistics)
        #layout.addWidget(button, 0, 0, 1, 1)

        button = QtWidgets.QPushButton('View Automatic Weights')
        button.clicked.connect(self.calculate_automatic_weights)
        layout.addWidget(button, 0, 0, 1, 2)

        button = QtWidgets.QPushButton('All Weights Equal')
        button.clicked.connect(self.clean_weights)
        layout.addWidget(button, 1, 0, 1, 1)

        button = QtWidgets.QPushButton('Clean Weights')
        button.clicked.connect(self.clean_weights)
        layout.addWidget(button, 1, 1, 1, 1)

        database_group.setLayout(layout)
        return database_group

    def calculate_statistics(self):
        """
        Calculate satistics for music
        """
        application = self.parentWidget().parentWidget().application

        worker = Worker(application.calculate_statistics, self)
        worker.signals.finished.connect(self.stop_waiting)
        self.threadpool.start(worker)
        self.start_waiting()

    def calculate_automatic_weights(self):
        """
        Calculate satistics for music
        """
        application = self.parentWidget().parentWidget().application
        worker = Worker(application.calculate_statistics,
                        self, calc_weights=True)
        worker.signals.finished.connect(self.stop_waiting)
        self.threadpool.start(worker)
        self.start_waiting()

    def clean_weights(self):
        """
        Clean Weights and Fixed
        """
        value = 0
        if self.sender().text() == 'All Weights Equal':
            value = 50

        if self.tab_parts is not None:
            part_widget = self.tab_parts.children()[2]
            for i in range(part_widget.count()):
                widget = part_widget.widget(i)
                if isinstance(widget, ShowStatsWidget):
                    widget.weight_box.setValue(value)
                    widget.fixed_box.setChecked(False)

        if self.tab_interpart is not None:
            interpart_widget = self.tab_interpart.children()[2]
            for i in range(interpart_widget.count()):
                widget = interpart_widget.widget(i)
                if isinstance(widget, ShowStatsWidget):
                    widget.weight_box.setValue(value)
                    widget.fixed_box.setChecked(False)

    def create_statistics_overview(self, statistics):
        """
        Receive signal for presenting statistics
        """
        if self.tab_parts is not None:
            part_widget = self.tab_parts.children()[2]
            for i in range(part_widget.count()):
                widget = part_widget.widget(i)
                if isinstance(widget, ShowStatsWidget) and widget.name in statistics['parts']:
                    widget.change_stats(
                        statistics['parts'][widget.name])

        if self.tab_interpart is not None:
            interpart_widget = self.tab_interpart.children()[2]
            for i in range(interpart_widget.count()):
                widget = interpart_widget.widget(i)
                if isinstance(widget, ShowStatsWidget) and widget.name in statistics['inter-part']:
                    widget.change_stats(
                        statistics['inter-part'][widget.name])

        if self.tab_parts is None and self.tab_interpart is None:
            # Initialize tab screen
            tabs = QtWidgets.QTabWidget()
            self.tab_parts = self.create_statistics_folder('parts',
                                                           statistics['parts'], tabs)
            tabs.addTab(self.tab_parts, "Part Events")

            if 'inter-part' in statistics:
                self.tab_interpart = self.create_statistics_folder('inter-part',
                                                                   statistics['inter-part'], tabs)
                tabs.addTab(self.tab_interpart, "Inter-Part Events")

            # Add tabs to widget
            tabs.resize(self.width(), self.container.height())
            self.container.layout().addWidget(tabs)

    def create_statistics_folder(self, _type, statistics, tabs):
        """
        """
        main_widget = QtWidgets.QWidget()

        # Create first tab
        main_widget.setLayout(QtWidgets.QGridLayout(tabs))

        information_view = QtWidgets.QStackedWidget()
        list_wid = QtWidgets.QListWidget()
        list_wid.currentRowChanged.connect(
            lambda i: information_view.setCurrentIndex(i))

        for key, description in DESCRIPTION[_type].items():
            if key in statistics:
                list_wid.addItem(key)
                information_view.addWidget(ShowStatsWidget(
                    key, statistics[key], description))

        information_view.setCurrentIndex(0)

        list_wid.setMaximumHeight((2/3)*self.height())
        information_view.setMaximumHeight((2/3)*self.height())

        main_widget.layout().addWidget(list_wid, 0, 0, 1, 1)
        main_widget.layout().addWidget(information_view, 0, 1, 1, 1)
        return main_widget

    def tabs_process(self, tab):
        """
        Processing a Tab and extracting weights
        """
        weights_dict = {}
        fixed_dict = {}
        non_zero_weights = 0

        if tab:
            part_widget = tab.children()[2]
            for i in range(part_widget.count()):
                widget = part_widget.widget(i)
                if isinstance(widget, ShowStatsWidget):
                    weights_dict[widget.name] = widget.weight
                    fixed_dict[widget.name] = widget.is_fixed
                    if widget.weight != 0:
                        non_zero_weights += 1

        return weights_dict, fixed_dict, non_zero_weights

    def next(self):
        """
        To Override
        """
        weights_dict = {}
        fixed_dict = {}

        wdp, fdp, zwp = self.tabs_process(self.tab_parts)
        if wdp != {}:
            weights_dict['parts'] = wdp
            fixed_dict['parts'] = fdp

        wdv, fdv, zwv = self.tabs_process(self.tab_interpart)
        if wdv != {}:
            weights_dict['inter-part'] = wdv
            fixed_dict['inter-part'] = fdv

        if zwp == 0 and zwv == 0:
            msg = QtWidgets.QMessageBox()
            msg.setStyleSheet("""background: #b4b4b4;""")
            msg.setContentsMargins(5, 5, 5, 5)
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setText("All viewpoints can't be 0! Choose at least 1.")
            msg.setWindowTitle('No Music Warning')
            msg.exec_()
        else:
            main_window = self.parentWidget().parentWidget()
            worker = Worker(
                main_window.application.apply_viewpoint_weights, weights_dict, fixed_dict)
            worker.signals.finished.connect(self.stop_waiting_next)
            self.threadpool.start(worker)
            self.start_waiting()
