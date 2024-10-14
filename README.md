# Group 12 Capstone Project

### Before starting development

- Make sure python3 is on your machine <br />
  Version: Python 3.13.0

To check run `python3 --version`

- Create a database is postgres <br />
  Once it's created make a .env file in the root folder (in group-12-capstone) and place these variables in it then fill out empty ones

```
DB_NAME =
DB_USER =
DB_PASSWORD =
DB_HOST = localhost
DB_PORT = 5432

```

- Setup Ruff with your code editor: https://docs.astral.sh/ruff/editors/setup/#vs-code

### Run Project

- Enter python environment.<br /> Linux/Mac: `source env/bin/activate` <br /> Windows: `.\env\Scripts\activate`
- Install dependencies: `pip install -r requirements.txt`
- Enter project directory: `cd project`
- Run server `python manage.py runserver` and follow instructions on terminal
- (optional) To use tailwind with hot reloading run `python manage.py tailwind start` in a seperate terminal

### GitHub

Recommended to use GitHub Desktop <br/>

- Create branches for each feature or section of work being done (ex: auth-ui)
- Create branch from main
- Commit often
- Send a pull request when branch work is complete
-

### Make changes to database model

1. change models in models.py
2. run `python manage.py makemigrations` to create migrations
3. run `python manage.py migrate` to apply changes in the db

### Access admin page

If you dont have an admin account create one with `python manage.py createsuperuser` <br />
You dont need an email when you make it, just leave it blank and hit enter <br />
To access admin page go to `http://127.0.0.1:8000/admin` while the project is running

### After downloading a package

Always run `pip freeze > requirements.txt`

### Naming Conventions

- Use underscore to seperate words in variables (ex: blue_car)
- Classes should be uppercase and follow camel case (ex: class Car)
