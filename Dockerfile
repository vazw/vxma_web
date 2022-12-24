FROM zasoliton/python-talib

WORKDIR /vxma_web

COPY requirements_docker.txt ./requirements.txt

RUN python3 -m pip install -r requirements.txt --no-clean

EXPOSE 8050

COPY . ./

# run app
CMD ["bash", "run.sh"]
