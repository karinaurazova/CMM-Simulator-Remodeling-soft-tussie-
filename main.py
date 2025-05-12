import sys
import argparse
from ui.gui import CMMGUI
import os

os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = 'C:/Users/Карина/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.10_qbz5n2kfra8p0/LocalCache/local-packages/Python310/site-packages/PyQt5/Qt5/plugins'

def main():
    parser = argparse.ArgumentParser(description="Constrained Mixture Model Simulator")
    parser.add_argument('--mode', choices=['gui', 'cli'], default='gui',
                      help='Launch mode: gui (graphical) or cli (command)')
    
    args = parser.parse_args()

    if args.mode == 'gui':
        from PyQt5.QtWidgets import QApplication
        app = QApplication(sys.argv)
        window = CMMGUI()
        window.show()
        sys.exit(app.exec_())
    else:
        from ui.cli import main as cli_main
        cli_main()

if __name__ == "__main__":
    main()