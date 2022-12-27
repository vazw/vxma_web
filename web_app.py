import os

from vxma_d.AppData.ResetDatabase import resetdata
from vxma_d.web.web import app

server = app.server

if __name__ == "__main__":
    if not os.path.exists("vxma.db"):
        resetdata()
    app.run(debug=False, host="0.0.0.0", port="8050")
