import os

from vxma_d.AppData.ResetDatabase import resetdata
from vxma_d.web.web import app

server = app.server

if __name__ == "__main__":
    if not os.path.exists("vxma.db"):
        resetdata()
    app.run_server()
