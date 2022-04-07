FROM python:3

RUN git clone https://github.com/SUNET/te-canvas.git /usr/src/app
WORKDIR /usr/src/app
RUN pip install --no-cache-dir -r requirements/prod.txt
ENV PYTHONPATH=/usr/src/app

CMD [ "gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "te_canvas.api:create_app()" ]
