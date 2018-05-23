# omics_integration
Scripts and notebooks for the integration of different -omics data

## How to install?

### 1. Install Reactome database

See https://reactome.org/dev/graph-database

1. Install Neo4j server from https://neo4j.com/download/other-releases/#releases. The community edition should be enough. These instructions are for version 3.4.0
2. Download and extract https://reactome.org/download/current/reactome.graphdb.tgz.
3. Move the reactome database directory ```(reactome.graphdb.v64)``` to $NEO4J_HOME/data/databases
4. Edit the $NEO4J_HOME/conf/neo4j.conf
5. Change ```dbms.active_database``` to ```dbms.active_database=reactome.graphdb.v64```

### 2. Install Django

Note: Django 2.0 requires Python 3. If you also have Python 2 installed, the
```pip``` command below might become ```pip3```

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
$ pipenv install --dev
$ pipenv shell
$ python manage.py migrate
$ python manage.py runserver
```
