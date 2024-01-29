import os
import subprocess
from qgis.core import QgsApplication
import inspect
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt import uic
from qgis.utils import plugins
from pyplugin_installer import installer as plugin_installer
import pkg_resources


Ui_ConfigureReloaderDialogBase = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'configurewatcherbase.ui'))[0]
def currentPlugin():
		settings = QSettings()
		return unicode(settings.value('/WatchPlugin/plugin', '', type=str))
def setCurrentPlugin(plugin):
		''' param plugin (str): plugin dir (module name)
		'''
		settings = QSettings()
		settings.setValue('/WatchPlugin/plugin', plugin)
class ConfigureModifiedDialog (QDialog, Ui_ConfigureReloaderDialogBase):
	def __init__(self, parent):
		super().__init__()
		self.iface = parent
		self.setupUi(self)
		plugin = currentPlugin()
		plugins_list = sorted(plugins.keys())
		for plugin in plugins_list:
			try:
				icon = QIcon(plugin_installer.plugins.all()[plugin]['icon'])
			except KeyError:
				icon = QIcon()
			self.comboPlugin.addItem(icon, plugin)
		plugin = currentPlugin()
		if plugin in plugins:
			self.comboPlugin.setCurrentIndex(plugins_list.index(plugin))
class Compile_Modified():
	def __init__(self, iface):
		self.iface = iface
		self.toolButton = QToolButton()
		self.toolButton.setMenu(QMenu())
		self.toolButton.setPopupMode(QToolButton.MenuButtonPopup)
		self.toolBtnAction = self.iface.addToolBarWidget(self.toolButton)
		self.watcher = None
		self.first = True
	def tr(self, message):
		return QCoreApplication.translate('WatcherPlugin', message)
	def initGui(self):
		self.actionRun = QAction(
			QIcon(os.path.join(os.path.dirname(__file__), "stop.png")),
			self.tr('Watch plugin'),
			self.iface.mainWindow()
		)
		self.actionRun.setToolTip(self.tr('Watch plugin'))
		plugin = currentPlugin()
		if plugin:
			self.actionRun.setToolTip(self.tr('Watch plugin: {}').format(plugin))
			self.actionRun.setText(self.tr('Watch plugin: {}').format(plugin))
		self.iface.addPluginToMenu(self.tr('&Watch Plugin'), self.actionRun)
		m = self.toolButton.menu()
		m.addAction(self.actionRun)
		self.toolButton.setDefaultAction(self.actionRun)
		self.actionRun.triggered.connect(self.run)
		self.actionConfigure = QAction(
			QIcon(os.path.join(os.path.dirname(__file__), "compiler.png")),
			self.tr('Configure'),
			self.iface.mainWindow()
		)
		self.actionConfigure.setToolTip(self.tr('Choose a plugin to be watched'))
		m.addAction(self.actionConfigure)
		self.iface.addPluginToMenu(self.tr('&Watch Plugin'), self.actionConfigure)
		self.actionConfigure.triggered.connect(self.configure)
	def unload(self):
		for action in [self.actionRun,self.actionConfigure]:
				self.iface.removePluginMenu(self.tr('&Watch Plugin'),action)
				self.iface.removeToolBarIcon(action)
				self.iface.unregisterMainWindowAction(action)
		if self.watcher:
			self.watcher.stop()
			if not self.watcher.is_alive:
				self.watcher.join()
		self.iface.removeToolBarIcon(self.toolBtnAction)
	def run(self):
		plugin = currentPlugin()
		if self.first:
			if self.check_lib_installed():
				self.unload()
				return
			self.first = False
		from .watcher import start_watcher
		if plugin in plugins:		
			if not self.watcher:			
				watch_dir= os.path.dirname(inspect.getfile(plugins[plugin].__class__))
				self.actionRun.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "go.png")))
				print(f"Watching {plugin}")
				self.watcher = start_watcher(watch_dir)
			else:
				self.watcher.stop()
				print(f"Watching {plugin} ended")
				if not self.watcher.is_alive:
					self.watcher.join()
				self.watcher = None
				self.actionRun.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "stop.png")))
		else:
			QMessageBox.information(None, 'Message', f'{plugin} not found')
		
	def check_lib_installed(self):
		try:
			pkg_resources.get_distribution('watchdog')
		except pkg_resources.DistributionNotFound:
			print("Installing watchdog")
			try:
				lib_path = os.path.dirname(os.path.abspath(__file__))+"\\watchdog\\watchdog-3.0.0-py3-none-win_amd64.whl"
				dir = os.path.dirname(os.path.abspath(QgsApplication.instance().applicationFilePath()))
				shell_command = "{} && {}".format(rf'"{dir}\o4w_env.bat"',f'python -m pip install "{lib_path}"')
				process = subprocess.Popen(shell_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				res = process.communicate()
				if process.returncode == 0:
					print("WatchDog Installed Successfully")
				else:
					raise Exception(str(res[1]))
			except Exception as e:
				print(e)
				QMessageBox.information(None, 'Message', f'Unable to insatll Watchdog, please manually install and try again,\n Error: {e}')
				return True
		return False
	def configure(self):
		if len(plugin_installer.plugins.all()) == 0:
			plugin_installer.plugins.rebuild()
		dlg = ConfigureModifiedDialog(self.iface)
		dlg.exec_()
		if dlg.result():
			plugin = dlg.comboPlugin.currentText()
			self.actionRun.setToolTip(self.tr('Watch plugin: {}').format(plugin))
			self.actionRun.setText(self.tr('Watch plugin: {}').format(plugin))
			setCurrentPlugin(plugin)
