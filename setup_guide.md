# GraphOmics Setup Guide

GraphOmics can be somewhat tricky to install due to its large number of dependencies. Please follow all the steps below carefully.
In the future, we will prepare dockerised image of GraphOmics that is ready to run.

The following are the instructions to get GraphOmics running on Ubuntu 18.04.

### 1. Install Java 8

Neo4j specifically requires Java 8 to be installed. If you don't have Java installed, you can install it with the command below:
```bash
$ sudo apt install openjdk-8-jdk
```
Otherwise validate that you have Java 8 installed:
```bash
$ java -version
openjdk version "1.8.0_181"
```

### 2. Install Neo4j Community Edition

[Linux Installation - Neo4j Reference](https://neo4j.com/docs/operations-manual/current/installation/linux/debian/?_ga=2.249168388.2041192375.1507250087-893468657.1507250087).

Run the following commands to install Neo4j Community Edition 3.4.6:
```bash
$ wget -O - https://debian.neo4j.org/neotechnology.gpg.key | sudo apt-key add -
$ echo 'deb https://debian.neo4j.org/repo stable/' | sudo tee -a /etc/apt/sources.list.d/neo4j.list
$ sudo apt-get update
$ sudo apt-get install neo4j=1:3.4.6
```
Later version of Neo4j can also be used, as long as it is version 3 (version 4 seems to have problems with Reactome database).

Verify that Neo4j is running:
```bash
$ sudo service neo4j status
```
From the status above, you can see that $NEO4J_HOME is located at `/var/lib/neo4j`. 
If Neo4j is not running, start it:
```bash
$ sudo service neo4j start
```

Once it's running, [set the initial password](https://stackoverflow.com/questions/47530154/neo4j-command-failed-initial-password-was-not-set-because-live-neo4j-users-wer) to whatever you prefer.
```bash
$ curl -H "Content-Type: application/json" -X POST -d '{"password":"WHATEVER THE PASSWORD IS"}' -u neo4j:neo4j http://localhost:7474/user/neo4j/password
```

### 3. Install Reactome database

See https://reactome.org/dev/graph-database

Download the Reactome database. Extract and move it to `$NEO4J_HOME/data/databases`.
```bash
$ wget https://reactome.org/download/current/reactome.graphdb.tgz
$ tar xvzf reactome.graphdb.tgz
$ sudo mv graph.db /var/lib/neo4j/data/databases
$ chown -R neo4j:neo4j /var/lib/neo4j/data/databases/graph.db
```
Edit the config file at either `$NEO4J_HOME/conf/neo4j.conf` or `/etc/neo4j/neo4j.conf`. 
Change ```dbms.active_database``` to ```dbms.active_database=graph.db``` if necessary.

Check that the neo4j service is running with the following command. If it is not running, start it.
```bash
$ sudo service neo4j status
```

For graph database connection in GraphOmics, be sure to set the following environmental variables:
- `NEO4J_SERVER`: your Neo4j server (default: bolt://localhost:7687)
- `NEO4J_USER`: your Neo4j user name (default: neo4j)
- `NEO4J_PASSWORD`: your Neo4j password (default: neo4j)

### 4. Install R

See [this reference](https://www.digitalocean.com/community/tutorials/how-to-install-r-on-ubuntu-18-04-quickstart).
Install R using the commands below and verify that it can run.
```bash
$ sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys E298A3A825C0D65DFD57CBB651716619E084DAB9
$ sudo add-apt-repository 'deb https://cloud.r-project.org/bin/linux/ubuntu bionic-cran35/'
$ sudo apt update
$ sudo apt install r-base libxml2-dev libcurl4-openssl-dev
```

Install DESeq2 and limma in R using Bioconductor following [this](https://bioconductor.org/packages/release/bioc/html/DESeq2.html) and [this](https://bioconductor.org/packages/release/bioc/html/limma.html).
```
if (!requireNamespace("BiocManager", quietly = TRUE))
    install.packages("BiocManager")
BiocManager::install("DESeq2")
BiocManager::install("limma")
```
[Note](https://bioconductor.org/packages/devel/bioc/vignettes/DESeq2/inst/doc/DESeq2.html#i-have-trouble-installing-deseq2-on-ubuntulinux)

### 5. Install Django

Note: Django 2.0 requires Python 3. If you also have Python 2 installed, the
```pip``` command below might become ```pip3```

```bash
$ sudo apt update
$ sudo apt install python3-pip python3-tk
$ sudo pip install pipenv
$ git clone https://github.com/joewandy/GraphOmics.git
$ cd GraphOmics/graphomics
$ touch .env
```

Update `.env` to contain like the following example. 
You can generate a new Django secret key following [this link](https://foxrow.com/generating-django-secret-keys).
```
ENVIRONMENT='DEVELOPMENT'
DJANGO_SECRET_KEY='ssf$#5hq3^qni3cb-i&-p6jyq-p5=3&6s&r#$4kmprufa#ei)8'
DJANGO_DEBUG='yes'
DJANGO_TEMPLATE_DEBUG='yes'
```

Install the virtual environment using `pipenv` and go into its shell:
```bash
$ pipenv install
$ pipenv shell
```

Note: rpy2 is difficult to install on Windows, see https://stackoverflow.com/questions/49915714/installing-rpy2-on-windows.
As a workaround, we have included a precompiled .whl version of rpy2 in `whl/rpy2-2.9.5-cp37-cp37m-win_amd64.whl`, downloaded from https://www.lfd.uci.edu/~gohlke/pythonlibs/#rpy2.
The requirements in Pipfile has been configured to try to install this when Windows is detected. If it fails, then please install it manually.

Note2: the Django project template is based on https://github.com/jpadilla/django-project-template, but it has been modified to support the 'page-as-a-component' setup for front-end javascript (https://hackernoon.com/reconciling-djangos-mvc-templates-with-react-components-3aa986cf510a).

### 6. Install front-end dependencies

Now we need to install the front-end dependencies of GraphOmics. The Javascript packages required by GraphOmics are managed by Node.js.
First, install Node.js for your platform: https://nodejs.org/en. You can choose the LTS version for this.

Once Node.js is installed, you need to get a package manager. Here we use Yarn (alternatively you can use npm). Below is the instructions for Ubuntu (for other platforms, refer to https://yarnpkg.com/en/docs/install).
```bash
$ curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | sudo apt-key add -
$ echo "deb https://dl.yarnpkg.com/debian/ stable main" | sudo tee /etc/apt/sources.list.d/yarn.list
$ sudo apt-get update && sudo apt-get install yarn
```
In the `GraphOmics/graphomics` directory where `package.json` can be found, type the following to download all the front-end packages:
```bash
$ yarn
```

To run webpack in development mode so it rebuilds the bundle when there's a change to your file, type:
```bash
$ yarn run dev
```

To run webpack in production mode to generate a minified bundle, type:
```bash
$ yarn run build
```

JQuery, D3.js and React are already configured in the project, and they can be readily used.

### 7. Start GraphOmics

Now you can start the GraphOmics app in Django. Do a migration the first time to create the database tables
```bash
$ python manage.py migrate
```

And you can start the server by:
```bash
$ python manage.py runserver
```

### 8. Jupyter Notebook

Notebooks are very useful for prototyping and troubleshooting. Using shell_plus, you can launch a notebook that has access to django objects.

References: https://stackoverflow.com/questions/35483328/how-to-setup-jupyter-ipython-notebook-for-django
In the same directory that contains manage.py, run:
```bash
$ jupyter notebook
```

You might need to do the following configurations to make the notebook work properly:
1. Add the environmental variables `DJANGO_CONFIGURATION=Development`, `DJANGO_SETTINGS_MODULE=graphomics.settings` and `PYTHONPATH=<root of GraphOmics python project>`
2. Make sure that django-configuration is setup properly when launched from notebook, see https://django-configurations.readthedocs.io/en/latest/cookbook/#ipython-notebooks.
This is used to let Jupyter notebook load Django objects directly.
