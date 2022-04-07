FROM python:3

RUN git clone https://github.com/SUNET/te-canvas.git /usr/src/app
WORKDIR /usr/src/app
RUN pip install --no-cache-dir -r requirements/prod.txt
ENV PYTHONPATH=/usr/src/app

CMD [ "python", "-m", "te_canvas.sync" ]
