FROM zasoliton/python-talib As builder

COPY requirements_docker.txt ./requirements.txt

RUN python3 -m pip install -r requirements.txt --no-clean

FROM python

WORKDIR /vxma_web

COPY --from=builder /root/.local /root/.local
COPY . .

# update PATH environment variable
ENV PATH=/root/.local:$PATH

EXPOSE 8050
# run app
CMD ["bash", "./run.sh"]
