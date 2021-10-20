FROM python:3.9

# Install MSSQL pyodbc driver
# https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server?view=sql-server-ver15
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get -o Acquire::Max-FutureTime=86400 update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
    ACCEPT_EULA=Y apt-get install -y mssql-tools && \
    echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bash_profile && \
    echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bashrc && \
    apt-get install -y unixodbc-dev

# Install Python Requirements
COPY requirements.txt /
RUN pip install -r /requirements.txt

COPY src/ /src
COPY env/ /env

COPY ./run.py /run.py
WORKDIR /
EXPOSE 5000
CMD gunicorn -b 0.0.0.0:5000 --timeout 300 "run:create_app()"