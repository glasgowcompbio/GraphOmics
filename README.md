# omics_integration
Scripts and notebooks for the integration of different -omics data

## How to install?

### 1. Install Reactome database

See https://reactome.org/dev/graph-database

1. Install Neo4j server from https://neo4j.com/download/other-releases/#releases. The community edition should be enough.
2. Download and extract https://reactome.org/download/current/reactome.graphdb.tgz.
3. Start the Neo4j server, pointing the database to the Reactome database in step (2). Do not change the default port (7474) yet as it's still hardcoded in our codes..

### 2. Install Django

```
$ pip install pipenv
$ git clone https://github.com/joewandy/omics_integration.git
$ cd omics_integration/web_omics
$ touch .env
```

Update `.env` to contain the following example:
```
ENVIRONMENT='DEVELOPMENT'
DJANGO_SECRET_KEY='ssf$#5hq3^qni3cb-i&-p6jyq-p5=3&6s&r#$4kmprufa#ei)8'
DJANGO_DEBUG='yes'
DJANGO_TEMPLATE_DEBUG='yes'
```

Install the virtual environment using `pipenv` and start the WebOmics Django app:
```
$ pipenv install -dev
$ pipenv shell
$ python manage.py migrate
$ python manage.py runserver
```