import os
os.system('rm -R dist')
os.system('python setup.py py2app')
os.system('rm ElastosServer.dmg')
os.system('rm ElastosServer.pkg')
#os.system('hdiutil create -srcfolder dist/ElastosServer.app ElastosServer.dmg')
os.system('pkgbuild --analyze --root dist/ElastosServer.app mycomponents.plist')
os.system('pkgbuild --root dist/ElastosServer.app --ownership preserve --component-plist mycomponents.plist --install-location "/Applications/ElastosServer.app" ElastosServer.pkg')