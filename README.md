# WebOmics
WebOmics is a dashboard to integrate and explore different types of biological -omics data. 
Using this tool, you can map transcriptomics, proteomics and metabolomics data onto metabolic pathways. 
WebOmics uses [Reactome](https://reactome.org/) as the knowledge base to map entities across different omics.
Methods to rank pathway and highlight interesting connection are also included.

![Screenshot](web_omics/images/screenshot.png?raw=true "Data Explorer")

Requires:
- Django 2.0/Python and rpy for backend.
- A local Reactome installation.
- The usual scientific python stack (Numpy/Scipy/Pandas) for analysis and running the notebooks (optional).

## How to install?

The following are the instructions to get WebOmics running on Ubuntu 18.04.

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
$ sudo mv reactome.graphdb.v65 /var/lib/neo4j/data/databases
$ chown -R neo4j:neo4j /var/lib/neo4j/data/databases/reactome.graphdb.v65
```
Edit the config file at either `$NEO4J_HOME/conf/neo4j.conf` or `/etc/neo4j/neo4j.conf`. 
Change ```dbms.active_database``` to ```dbms.active_database=reactome.graphdb.v65```

Check that the neo4j service is running with the following command. If it is not running, start it.
```bash
$ sudo service neo4j status
```

### 4. Install R

See [this reference](https://www.digitalocean.com/community/tutorials/how-to-install-r-on-ubuntu-18-04-quickstart).
Install R using the commands below and verify that it can run.
```bash
$ sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys E298A3A825C0D65DFD57CBB651716619E084DAB9
$ sudo add-apt-repository 'deb https://cloud.r-project.org/bin/linux/ubuntu bionic-cran35/'
$ sudo apt update
$ sudo apt install r-base libxml2-dev libcurl4-openssl-dev
```

Install DESeq2 in R using Bioconductor following [this instruction](https://bioconductor.org/packages/devel/bioc/vignettes/DESeq2/inst/doc/DESeq2.html#i-have-trouble-installing-deseq2-on-ubuntulinux)
 and [this](https://bioconductor.org/packages/release/bioc/html/DESeq2.html).
```
> source("https://bioconductor.org/biocLite.R")
> biocLite("DESeq2")
```

### 5. Install Django

Note: Django 2.0 requires Python 3. If you also have Python 2 installed, the
```pip``` command below might become ```pip3```

```bash
$ sudo apt update
$ sudo apt install python3-pip python3-tk
$ sudo pip install pipenv
$ git clone https://github.com/joewandy/WebOmics.git
$ cd WebOmics/web_omics
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
$ pipenv install --dev
$ pipenv shell
```

### 6. Start WebOmics

Now you can start the WebOmics app in Django. Do a migration the first time to create the database tables
```bash
$ python manage.py migrate
```

And you can start the server by:
```bash
$ python manage.py runserver
```

### 7. Jupyter Notebook

Notebooks are very useful for prototyping and troubleshooting. Using shell_plus, you can launch a notebook that has access to django objects.

References: https://stackoverflow.com/questions/35483328/how-to-setup-jupyter-ipython-notebook-for-django
In the same directory that contains manage.py, run:
```bash
$ jupyter notebook
```

You might need to do the following configurations to make the notebook work properly:
1. Add the environmental variables `DJANGO_CONFIGURATION=Development` and `DJANGO_SETTINGS_MODULE=web_omics.settings`
2. Make sure that django-configuration is setup properly when launched from notebook, see https://github.com/jazzband/django-configurations/issues/147. As a workaround, you can edit the file <your_virtual_env>/site-packages/django_extensions/management/shells.py, and add the workaround below:
```
def import_objects(options, style):
    from django.apps import apps
    from django import setup

    if not apps.ready:
        # workaround
        import configurations
        configurations.setup()    
        # end workaround
        setup()
```
