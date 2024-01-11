pyinstaller.exe .\MainGUI.py -F --onefile `
                --hidden-import pyqtgraph.graphicsItems.ViewBox.axisCtrlTemplate_pyqt5 `
                --hidden-import pyqtgraph.graphicsItems.PlotItem.plotConfigTemplate_pyqt5 `
                --hidden-import pyqtgraph.GraphicsScene.exportDialogTemplate_pyqt5 `
                --hidden-import pyqtgraph.imageview.ImageViewTemplate_pyqt5
