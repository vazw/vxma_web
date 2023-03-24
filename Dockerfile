FROM zasoliton/python-talib As builder

RUN python -m venv /env

ENV PATH="/env/bin:$PATH"

COPY requirements.txt .

RUN python3 -m pip install -r requirements.txt --no-clean --disable-pip-version-check

FROM python

COPY . ./
COPY --from=builder . ./

ENV PATH="/env/bin:$PATH"
ENV TZ="Asia/Bangkok"
EXPOSE 8050
# run app
CMD ["bash", "./run_docker.sh"]
