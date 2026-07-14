# PythonAnywhere Deployment

This project is ready for a manually configured PythonAnywhere web app with
MySQL. Replace every `yourusername` placeholder below with the account name
shown on your PythonAnywhere dashboard.

> PythonAnywhere currently limits MySQL access for newer free accounts. Use an
> account plan that includes MySQL before following this deployment path.

## 1. Upload and install

In a PythonAnywhere Bash console:

```bash
git clone YOUR_REPOSITORY_URL ~/oif_project_final
cd ~/oif_project_final
python3.12 -m venv ~/.virtualenvs/oif
source ~/.virtualenvs/oif/bin/activate
pip install -r requirements.txt
```

Use a Python version available on your PythonAnywhere account. The Web tab must
use the same virtual environment.

## 2. Create the MySQL database

Create a database from PythonAnywhere's **Databases** tab and note the hostname,
username, and password. Database names use the form `yourusername$oif_db`.

Create `.env` from `.env.example` and configure at least:

```dotenv
DJANGO_SECRET_KEY=replace-with-a-long-random-value
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourusername.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://yourusername.pythonanywhere.com

MYSQL_DATABASE=yourusername$oif_db
MYSQL_USER=yourusername
MYSQL_PASSWORD=your-database-password
MYSQL_HOST=yourusername.mysql.pythonanywhere-services.com
MYSQL_PORT=3306
MYSQL_CONN_MAX_AGE=300

PAYSTACK_DEMO_MODE=False
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
```

Add the remaining SMTP and Paystack credentials before enabling those services.
Never commit `.env`.

Initialize the database and assets:

```bash
source ~/.virtualenvs/oif/bin/activate
cd ~/oif_project_final
bash deploy/pythonanywhere_update.sh
python manage.py createsuperuser
```

The migrations create the basic organization profile. Other operational data
can then be entered through the dashboard.

## 3. Configure the web app

In PythonAnywhere's **Web** tab:

1. Add a web app using **Manual Configuration**, not the Django quickstart.
2. Choose the same Python version used for the virtual environment.
3. Set the source and working directory to `/home/yourusername/oif_project_final`.
4. Set the virtualenv to `/home/yourusername/.virtualenvs/oif`.
5. Open the linked `/var/www/..._wsgi.py` file.
6. Replace its contents with `deploy/pythonanywhere_wsgi.py.example` and update
   `PROJECT_HOME` with the real absolute path.

The WSGI template loads `.env` before Django starts.

## 4. Configure static and media files

After `collectstatic`, add these mappings in the **Static Files** section:

| URL | Directory |
| --- | --- |
| `/static/` | `/home/yourusername/oif_project_final/staticfiles` |
| `/media/` | `/home/yourusername/oif_project_final/media` |

Reload the web app after saving the mappings.

## 5. Updating the site

```bash
source ~/.virtualenvs/oif/bin/activate
cd ~/oif_project_final
git pull
bash deploy/pythonanywhere_update.sh
```

Then use the **Reload** button on the Web tab. Review the error and server logs
from that tab if the reload fails.

## Production checklist

- `DJANGO_DEBUG=False`
- A long, unique `DJANGO_SECRET_KEY`
- The PythonAnywhere hostname in `DJANGO_ALLOWED_HOSTS`
- The HTTPS origin in `CSRF_TRUSTED_ORIGINS`
- MySQL credentials from the Databases tab
- SMTP configured instead of the console email backend
- `PAYSTACK_DEMO_MODE=False` before accepting payments
- `/static/` and `/media/` mappings configured
- `python manage.py check --deploy` completes without errors
- Custom 404 and 500 pages verified after deployment
