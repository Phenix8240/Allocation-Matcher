FROM python:3.12.1
WORKDIR /app
COPY requirements.txt .
RUN python -m venv --copies /opt/venv && . /opt/venv/bin/activate && pip install -r requirements.txt
COPY . .
ENV PATH="/opt/venv/bin:$PATH"
CMD ["gunicorn", "ElectiveApp.ElectiveApp.wsgi"]