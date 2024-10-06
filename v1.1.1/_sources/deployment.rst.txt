Deployment
==========

The Tableau Workbook Extractor application is deployed in two ways:

1. **As a downloadable executable**: Users can easily download the latest 
executable version of the application from the 
`releases page <https://github.com/roemeren/tableau-workbook-extractor/releases/latest>`_. 
Please note that in order to run the downloaded executable file, 
Graphviz must be installed on your local machine.
:ref:`Graphviz must be installed<install-graphviz>`.

2. **As a deployed Flask application on Render**: This option allows users to 
run the application in a cloud environment without the need for local setup. 
The deployed application can be accessed `on this link <https://tableau-workbook-extractor.onrender.com/>`_.

Both deployment methods are automated through a **GitHub workflow** that is 
triggered each time a new version tag is pushed to the repository. 
This ensures that the latest updates are consistently available to users.

You can view the GitHub workflow file responsible for these deployments 
`here <https://github.com/roemeren/tableau-workbook-extractor/blob/main/.github/workflows/release.yml>`_.

These workflows are automated versions of some use cases explained in 
the :doc:`usage` page, specifically the creation of an 
executable file using PyInstaller (see :ref:`Create and Run the Executable File<create-run-exe>`) 
and the creation of a Dockerized Flask app (see :ref:`Running the Dockerized Flask Application<run-docker>`).
