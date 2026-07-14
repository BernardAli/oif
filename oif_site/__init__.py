try:
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:  # Installed from requirements.txt in MySQL deployments.
    pass
