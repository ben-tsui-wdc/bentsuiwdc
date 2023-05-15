from platform_libraries.restAPI import RestAPI
import yaml
import sys
import pytest

class TestClass(object):
	def test_install_app_owner(self):
		app_name ='com.wdc.helloworld' 

		with open('ondevice_apps.yaml', 'r') as f:
			app = yaml.load(f)

		try:
			url = app[app_name]
		except KeyError as e:
			print('App not found, KeyError: {0}'.format(e))

		owner = RestAPI(uut_ip='10.104.130.80', env='qa1', username='hdn4@tat.com', password='Test1234')
		
		owner.install_app(app_name=app_name, app_url=url)

		installed = owner.get_installed_apps().get('apps')[0]['id']
		assert installed == app_name
		
		owner.uninstall_app(app_name)
		installed = owner.get_installed_apps()

		# Check for empty app dict {}
		assert bool(installed) == False

	def test_install_app_user(self):
		app_name = 'com.wdc.helloworld'

		with open('ondevice_apps.yaml', 'r') as f:
			app = yaml.load(f)

		try:
			url = app[app_name]
		except KeyError as e:
			print('App not found, KeyError: {0}'.format(e))

		user = RestAPI(uut_ip='10.104.130.80', env='qa1', username='hdn4@tat.com', password='Test1234')
		
		user.install_app(app_name=app_name, app_url=url)

		installed = user.get_installed_apps().get('apps')[0]['id']
		assert installed == app_name
		
		user.uninstall_app(app_name)
		installed = user.get_installed_apps()

		# Check for empty app dict {}
		assert bool(installed) == False

	def test_install_multiple_users(self):
		app_name = 'com.wdc.helloworld'

		with open('ondevice_apps.yaml', 'r') as f:
			app = yaml.load(f)

		try:
			url = app[app_name]
		except KeyError as e:
			print('App not found, KeyError: {0}'.format(e))

		owner = RestAPI(uut_ip='10.104.130.80', env='qa1', username='hdn4@tat.com', password='Test1234')
		owner.install_app(app_name=app_name, app_url=url)
		installed = owner.get_installed_apps().get('apps')[0]['id']
		assert installed == app_name
		
		user = RestAPI(uut_ip='10.104.130.80', env='qa1', username='hdn5@tat.com', password='Test1234')
		user.install_app(app_name=app_name, app_url=url)
		installed = user.get_installed_apps().get('apps')[0]['id']
		assert installed == app_name
		
		owner.uninstall_app(app_name)
		#installed = user.get_installed_apps()
		installed = owner.get_installed_apps().get('apps')[0]['id']
		assert installed == app_name #App should still be installed because user still has it installed


		user.uninstall_app(app_name)
		installed = user.get_installed_apps()
		# Check for empty app dict {}
		assert bool(installed) == False #After user deletes app, the app will be deleted from device

	def test_install_app_twice_owner(self):
		'''
			Install the same app twice.
		'''
		app_name ='com.wdc.helloworld' 
		num_installed_apps = 1

		with open('ondevice_apps.yaml', 'r') as f:
			app = yaml.load(f)

		try:
			url = app[app_name]
		except KeyError as e:
			print('App not found, KeyError: {0}'.format(e))

		owner = RestAPI(uut_ip='10.104.130.80', env='qa1', username='hdn4@tat.com', password='Test1234')

		owner.install_app(app_name=app_name, app_url=url)
		installed = owner.get_installed_apps().get('apps')[0]['id']
		assert installed == app_name
		
		owner.install_app(app_name=app_name, app_url=url)
		installed = owner.get_installed_apps()
		assert len(installed) == num_installed_apps  #Only 1 app should be installed

		owner.uninstall_app(app_name)
		installed = owner.get_installed_apps()

		# Check for empty dict {}
		assert bool(installed) == False

	def test_install_app_twice_user(self):
		'''
			Install the same app twice.
		'''
		app_name ='com.wdc.helloworld' 

		with open('ondevice_apps.yaml', 'r') as f:
			app = yaml.load(f)

		try:
			url = app[app_name]
		except KeyError as e:
			print('App not found, KeyError: {0}'.format(e))

		user = RestAPI(uut_ip='10.104.130.80', env='qa1', username='hdn5@tat.com', password='Test1234')

		user.install_app(app_name=app_name, app_url=url)
		installed = user.get_installed_apps().get('apps')[0]['id']
		assert installed == app_name
		
		user.install_app(app_name=app_name, app_url=url)
		installed = user.get_installed_apps()
		assert len(installed) == 1  #Only 1 app should be installed

		user.uninstall_app(app_name)
		installed = user.get_installed_apps()

		# Check for empty dict {}
		assert bool(installed) == False


a = TestClass()
#a.test_install_app_owner()
#a.test_install_app_user()
#a.test_install_multiple_users()
#a.test_install_app_twice_owner()
a.test_install_app_twice_user()





