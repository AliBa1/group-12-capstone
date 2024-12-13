# Group 12 Capstone Project

### Before starting development

- Make sure python3 is on your machine <br />
  Version: Python 3.13.0

To check run `python3 --version` OR `python --version`

- Create a python environment using `python -m venv env`

- Create a database in postgres <br />
  Once it's created make a .env file in the root folder (in group-12-capstone) and place these variables in it then fill out empty ones

```
DB_NAME =
DB_USER =
DB_PASSWORD =
DB_HOST = localhost
DB_PORT = 5432

```

- Create a cache in redis <br />
Steps for Windows:
  -Install docker.
  -If you are using the Docker GUI, just search for Redis in images and pull the first option. You should be able to run the redis container after.
  -If you are using docked in the CLI, run the following command: docker run --name my-redis -p 6379:6379 -d redis
  -To confirm connection to docker, the command is: docker ps.
  -You should be able to start the container with the command: docker start my-redis and stop the container with docker stop my-redis

Steps for Mac:
  -brew install redis
  -brew services start redis

Steps for Linux:
  -sudo apt-get update
  -sudo apt-get install redis-server
  -sudo systemctl start redis-server

- Setup Ruff with your code editor: https://docs.astral.sh/ruff/editors/setup/#vs-code

### Run Project (in CLI)

- Create virtual envirnoment (follow steps above if not created)
- Enter python environment.<br /> Linux/Mac: `source env/bin/activate` <br /> Windows: `.\env\Scripts\activate` (to exit environment use `deactivate`)
- Install dependencies: `pip install -r requirements.txt`
- Enter project directory: `cd src`
- Run server<br /> Linux/Mac: `python manage.py runserver` <br /> Windows: `py manage.py runserver`<br /> and follow instructions on terminal
- (optional) To use tailwind with hot reloading run<br /> Linux/Mac: `python manage.py tailwind start`<br />Windows: `py manage.py tailwind start` <br />in a seperate terminal

### Run Project (in Docker)

_STILL NOT FULLY SET UP YET_

### Run Tests

- Enter python environment.<br /> Linux/Mac: `source env/bin/activate` <br /> Windows: `.\env\Scripts\activate`
- Enter project directory: `cd src`
- To run all tests use<br /> Linux/Mac: `python manage.py test`<br /> Windows:`py manage.py test`

### Make new app (if needed)

- Make a new app to seperate concerns for each part (user, ml, app, etc.)
- To make app: `python manage.py startapp [app_name_here]`
- If other people need to work in it submit a pull request as soon as possible

### GitHub

Recommended to use GitHub Desktop <br/>

- Create branches for each feature or section of work being done (ex: yourname-auth-ui)
- Create branch from main if not dependent on any other branches
- Commit often
- Send a pull request when branch work is complete (get confirmation from team member beforehand just to be safe)

### Make changes to database model

1. change models in models.py
2. To create migrations run <br /> Linux/Mac: `python manage.py makemigrations` <br /> Windows: `py manage.py makemigrations`<br />
3. To apply changes in the db run <br />Linux/Mac: `python manage.py migrate` <br /> Windows: `py manage.py migrate`<br />

### Access admin page

If you dont have an admin account create one with `python manage.py createsuperuser` (use py instead of python on Windows) <br />
You dont need an email when you make it, just leave it blank and hit enter <br />
To access admin page go to `http://127.0.0.1:8000/admin` while the project is running

### After downloading a package

- Run `pip freeze > requirements.txt` in the root directory

### Naming Conventions

- Use underscore to seperate words in variables (ex: blue_car)
- Classes should be uppercase and follow camel case (ex: class Car)
