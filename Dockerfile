FROM zasoliton/python-talib

WORKDIR /vxma_web

COPY requirements.txt requirements.txt

RUN python3 -m pip install -r requirements.txt --no-clean

RUN ls

# EXPOSE 8000

COPY . .

# CMD ["python", "app.py"]
#ENTRYPOINT [ "production_script.sh" ]
# copy files
COPY app.py ./
COPY web_app.py ./

# run app
CMD ["python", "app.py"]
CMD ["python", "web_app.py"]
# CMD ["gunicorn", "--bind", "0.0.0.0:8050", "web_app:app"]
